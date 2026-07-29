"""Periodic reminder dispatch + per-instance send task.

`dispatch_due_reminders` doubles as the scheduler-recovery pass: every tick
it re-scans all due `scheduled` instances (not just ones missed since the
last tick), so a worker restart after downtime naturally catches up within
the bounded 24h window without any separate "on startup" code path.
"""

import logging
import uuid
from datetime import timedelta

from sqlalchemy import select

from app.core.timezone import now_utc
from app.db.session import SessionLocal
from app.models.invoice import Invoice, InvoiceStatus
from app.models.reminder_instance import ReminderInstance, ReminderInstanceStatus
from app.services import reminders as reminder_service
from app.services.audit import record_audit
from app.tasks.celery_app import celery_app
from app.tasks.email import EmailDeliveryError, send_admin_alert, send_reminder_email

logger = logging.getLogger("app.tasks.reminder_dispatch")


@celery_app.task(name="app.tasks.reminder_dispatch.dispatch_due_reminders")
def dispatch_due_reminders() -> dict:
    session = SessionLocal()
    claimed = 0
    skipped_catchup = 0
    try:
        if reminder_service.is_kill_switch_enabled(session):
            return {"kill_switch": True, "claimed": 0, "skipped_catchup": 0}

        now = now_utc()
        catchup_floor = now - reminder_service.CATCHUP_WINDOW

        candidate_ids = list(
            session.execute(
                select(ReminderInstance.id, ReminderInstance.scheduled_for)
                .where(
                    ReminderInstance.status == ReminderInstanceStatus.scheduled,
                    ReminderInstance.scheduled_for <= now,
                )
                .order_by(ReminderInstance.scheduled_for)
            ).all()
        )

        for instance_id, scheduled_for in candidate_ids:
            if scheduled_for < catchup_floor:
                _skip_catchup(session, instance_id)
                skipped_catchup += 1
                continue

            claimed_instance = reminder_service.claim_reminder_instance(session, instance_id)
            if claimed_instance is None:
                continue
            claimed += 1
            send_single_reminder.delay(str(claimed_instance.id))

        return {"claimed": claimed, "skipped_catchup": skipped_catchup}
    finally:
        session.close()


def _skip_catchup(session, instance_id: uuid.UUID) -> None:
    instance = session.get(ReminderInstance, instance_id)
    if instance is None or instance.status != ReminderInstanceStatus.scheduled:
        return
    record_audit(
        session,
        entity_type="reminder_instance",
        entity_id=instance.id,
        action="reminder_skipped_catchup_window",
        actor_id=None,
        before=None,
        after={"scheduled_for": instance.scheduled_for.isoformat()},
    )
    session.commit()


@celery_app.task(
    bind=True,
    name="app.tasks.reminder_dispatch.send_single_reminder",
    autoretry_for=(EmailDeliveryError,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=3,
)
def send_single_reminder(self, instance_id: str) -> str:
    session = SessionLocal()
    try:
        instance = session.execute(
            select(ReminderInstance).where(ReminderInstance.id == uuid.UUID(instance_id)).with_for_update()
        ).scalar_one_or_none()
        if instance is None:
            return "not_found"

        invoice = session.execute(
            select(Invoice).where(Invoice.id == instance.invoice_id).with_for_update()
        ).scalar_one()

        if invoice.status in (InvoiceStatus.paid, InvoiceStatus.cancelled):
            reason = "invoice paid" if invoice.status == InvoiceStatus.paid else "invoice cancelled"
            instance.status = ReminderInstanceStatus.cancelled
            instance.cancelled_at = now_utc()
            instance.cancellation_reason = reason
            session.flush()
            record_audit(
                session,
                entity_type="reminder_instance",
                entity_id=instance.id,
                action="reminder_cancelled",
                actor_id=None,
                before=None,
                after={"reason": reason},
            )
            session.commit()
            return "cancelled_race"

        try:
            send_reminder_email(instance, invoice)
        except EmailDeliveryError:
            session.rollback()
            if self.request.retries >= self.max_retries:
                session2 = SessionLocal()
                try:
                    failed_instance = session2.get(ReminderInstance, instance.id)
                    failed_instance.status = ReminderInstanceStatus.failed
                    session2.flush()
                    record_audit(
                        session2,
                        entity_type="reminder_instance",
                        entity_id=failed_instance.id,
                        action="reminder_failed_permanent",
                        actor_id=None,
                        before=None,
                        after={"attempt_count": failed_instance.attempt_count},
                    )
                    session2.commit()
                    send_admin_alert(failed_instance)
                finally:
                    session2.close()
            raise

        instance.status = ReminderInstanceStatus.sent
        instance.sent_at = now_utc()
        session.flush()
        record_audit(
            session,
            entity_type="reminder_instance",
            entity_id=instance.id,
            action="reminder_sent",
            actor_id=None,
            before=None,
            after={"sent_at": instance.sent_at.isoformat()},
        )
        session.commit()
        return "sent"
    finally:
        session.close()
