from datetime import date, timedelta

from app.core.timezone import now_utc
from app.models.reminder_instance import ReminderInstance, ReminderInstanceStatus
from app.services import invoices as invoice_service
from app.tasks import reminder_dispatch
from tests.factories import make_line_item


class _NoCloseSessionProxy:
    """Wraps the test's fixture-managed db_session so dispatch code can call
    .close() without ending the outer test transaction — teardown of the
    SAVEPOINT-wrapped session is still owned entirely by the db_session
    fixture."""

    def __init__(self, session):
        self._session = session

    def close(self):
        pass

    def __getattr__(self, name):
        return getattr(self._session, name)


def _issued_invoice(db_session, customer, admin_user, active_tax_rate):
    draft = invoice_service.create_draft_invoice(
        db_session,
        customer_id=customer.id,
        due_date=date.today() + timedelta(days=10),
        line_items=[make_line_item()],
        actor_id=admin_user.id,
    )
    return invoice_service.issue_invoice(db_session, draft.id, actor_id=admin_user.id)


def test_scheduler_recovers_within_catchup_window(db_session, customer, admin_user, active_tax_rate, monkeypatch):
    invoice = _issued_invoice(db_session, customer, admin_user, active_tax_rate)
    instance = (
        db_session.query(ReminderInstance).filter(ReminderInstance.invoice_id == invoice.id).first()
    )
    instance.scheduled_for = now_utc() - timedelta(hours=6)
    db_session.flush()
    db_session.commit()

    monkeypatch.setattr(reminder_dispatch, "SessionLocal", lambda: _NoCloseSessionProxy(db_session))
    monkeypatch.setattr(
        reminder_dispatch.send_single_reminder, "delay", lambda instance_id: None
    )

    result = reminder_dispatch.dispatch_due_reminders()
    db_session.refresh(instance)
    assert result["claimed"] >= 1
    assert instance.status == ReminderInstanceStatus.sending


def test_scheduler_skips_instance_outside_catchup_window(db_session, customer, admin_user, active_tax_rate, monkeypatch):
    from app.models.audit_log import AuditLogEntry

    invoice = _issued_invoice(db_session, customer, admin_user, active_tax_rate)
    instance = (
        db_session.query(ReminderInstance).filter(ReminderInstance.invoice_id == invoice.id).first()
    )
    instance.scheduled_for = now_utc() - timedelta(hours=40)
    db_session.flush()
    db_session.commit()

    monkeypatch.setattr(reminder_dispatch, "SessionLocal", lambda: _NoCloseSessionProxy(db_session))
    monkeypatch.setattr(
        reminder_dispatch.send_single_reminder, "delay", lambda instance_id: None
    )

    result = reminder_dispatch.dispatch_due_reminders()
    db_session.refresh(instance)

    assert result["skipped_catchup"] >= 1
    assert instance.status == ReminderInstanceStatus.scheduled  # left untouched

    skip_audit = (
        db_session.query(AuditLogEntry)
        .filter(
            AuditLogEntry.entity_id == instance.id,
            AuditLogEntry.action == "reminder_skipped_catchup_window",
        )
        .first()
    )
    assert skip_audit is not None
