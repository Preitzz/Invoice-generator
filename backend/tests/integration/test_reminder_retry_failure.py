from datetime import date, timedelta

from app.core.timezone import now_utc
from app.models.audit_log import AuditLogEntry
from app.models.reminder_instance import ReminderInstance, ReminderInstanceStatus
from app.services import invoices as invoice_service
from app.tasks import email as email_tasks
from app.tasks import reminder_dispatch
from app.tasks.celery_app import celery_app
from tests.factories import make_line_item


def _issued_invoice_with_due_instance(db_session, customer, admin_user, active_tax_rate):
    draft = invoice_service.create_draft_invoice(
        db_session,
        customer_id=customer.id,
        due_date=date.today() + timedelta(days=10),
        line_items=[make_line_item()],
        actor_id=admin_user.id,
    )
    invoice = invoice_service.issue_invoice(db_session, draft.id, actor_id=admin_user.id)
    instance = db_session.query(ReminderInstance).filter(ReminderInstance.invoice_id == invoice.id).first()
    instance.scheduled_for = now_utc() - timedelta(minutes=5)
    instance.status = ReminderInstanceStatus.sending
    instance.attempt_count = 1
    db_session.flush()
    db_session.commit()
    return invoice, instance


class _NoCloseSessionProxy:
    def __init__(self, session):
        self._session = session

    def close(self):
        pass

    def __getattr__(self, name):
        return getattr(self._session, name)


def _drive_task_with_manual_retries(task, instance_id: str, max_attempts: int = 6):
    """Celery's eager `.apply()` does not loop retries automatically (that's
    normally the worker's job) — this harness reproduces exactly what a real
    worker does: re-invoke the task with an incremented `retries` count each
    time a Retry is raised, until it either succeeds or genuinely fails."""
    from celery.exceptions import Retry

    attempt = 0
    while attempt < max_attempts:
        result = task.apply(args=[instance_id], kwargs={}, retries=attempt, throw=False)
        outcome = result.result
        if isinstance(outcome, Retry):
            attempt += 1
            continue
        return outcome
    raise AssertionError("exceeded max_attempts without resolving")


def test_transient_failure_recovers_on_retry(db_session, customer, admin_user, active_tax_rate, monkeypatch):
    invoice, instance = _issued_invoice_with_due_instance(db_session, customer, admin_user, active_tax_rate)

    fake_provider = email_tasks.FakeEmailProvider()
    fake_provider.force_fail_count = 1  # first attempt fails, retry succeeds
    email_tasks.set_provider(fake_provider)

    monkeypatch.setattr(reminder_dispatch, "SessionLocal", lambda: _NoCloseSessionProxy(db_session))

    celery_app.conf.task_always_eager = True
    try:
        outcome = _drive_task_with_manual_retries(reminder_dispatch.send_single_reminder, str(instance.id))
    finally:
        celery_app.conf.task_always_eager = False

    assert outcome == "sent"
    db_session.refresh(instance)
    assert instance.status == ReminderInstanceStatus.sent
    assert instance.attempt_count >= 1
    assert len(fake_provider.sent) == 1


def test_all_retries_exhausted_marks_failed_and_alerts_admin(
    db_session, customer, admin_user, active_tax_rate, monkeypatch
):
    invoice, instance = _issued_invoice_with_due_instance(db_session, customer, admin_user, active_tax_rate)

    fake_provider = email_tasks.FakeEmailProvider()
    fake_provider.force_fail_count = 999  # always fails
    email_tasks.set_provider(fake_provider)

    monkeypatch.setattr(reminder_dispatch, "SessionLocal", lambda: _NoCloseSessionProxy(db_session))

    celery_app.conf.task_always_eager = True
    try:
        outcome = _drive_task_with_manual_retries(reminder_dispatch.send_single_reminder, str(instance.id))
    finally:
        celery_app.conf.task_always_eager = False

    assert isinstance(outcome, email_tasks.EmailDeliveryError)

    db_session.refresh(instance)
    assert instance.status == ReminderInstanceStatus.failed

    failure_audit = (
        db_session.query(AuditLogEntry)
        .filter(
            AuditLogEntry.entity_id == instance.id,
            AuditLogEntry.action == "reminder_failed_permanent",
        )
        .first()
    )
    assert failure_audit is not None

    admin_alert = [s for s in fake_provider.sent if s["to"] == "admin-alerts@example.com"]
    assert len(admin_alert) == 1
