"""Reminder scheduling math and lifecycle management.

Kept independent of app/tasks/reminder_dispatch.py (which owns the Celery
periodic-task orchestration) — this module owns everything that can be
unit-tested without a running worker: schedule computation, recalculation on
due-date edit, cancellation on paid/cancelled, the atomic claim helper, and
the kill-switch read/write.
"""

import uuid
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.timezone import ist_end_of_day, now_utc
from app.models.reminder_instance import ReminderInstance, ReminderInstanceStatus
from app.models.reminder_rule import ReminderRule
from app.models.system_settings import SystemSetting
from app.services.audit import record_audit

KILL_SWITCH_KEY = "reminder_kill_switch"
CATCHUP_WINDOW = timedelta(hours=24)


def compute_schedule(session: Session, due_date: date) -> list[tuple[ReminderRule, datetime]]:
    """Returns [(rule, scheduled_for_utc), ...] for all 5 fixed reminder
    rules, anchored to `due_date`'s 23:59:59 IST moment (the same instant
    used for the Overdue derivation), offset by each rule's offset_days.
    """
    anchor = ist_end_of_day(due_date)
    rules = session.execute(select(ReminderRule).order_by(ReminderRule.offset_days)).scalars().all()
    return [(rule, anchor + timedelta(days=rule.offset_days)) for rule in rules]


def schedule_reminders_for_invoice(session: Session, invoice) -> list[ReminderInstance]:
    """Called at Issue time. Creates all 5 ReminderInstance rows in
    'scheduled' status."""
    schedule = compute_schedule(session, invoice.due_date)
    instances = []
    for rule, scheduled_for in schedule:
        instance = ReminderInstance(
            invoice_id=invoice.id,
            rule_id=rule.id,
            scheduled_for=scheduled_for,
            status=ReminderInstanceStatus.scheduled,
        )
        session.add(instance)
        instances.append(instance)
    session.flush()
    return instances


def recalculate_scheduled_reminders(session: Session, invoice, new_due_date: date) -> None:
    """Recomputes all not-yet-sent (`scheduled`) reminder instances when an
    invoice's due date is edited. Already-`sent` instances are left
    untouched as historical record."""
    schedule = {rule.id: scheduled_for for rule, scheduled_for in compute_schedule(session, new_due_date)}

    instances = session.execute(
        select(ReminderInstance).where(
            ReminderInstance.invoice_id == invoice.id,
            ReminderInstance.status == ReminderInstanceStatus.scheduled,
        )
    ).scalars()

    for instance in instances:
        if instance.rule_id in schedule:
            instance.scheduled_for = schedule[instance.rule_id]
    session.flush()


def cancel_remaining_reminders(session: Session, invoice, *, reason: str, actor_id: uuid.UUID | None) -> None:
    """Cancels all remaining `scheduled` reminder instances for an invoice,
    recording each as an audited event. `actor_id=None` means system."""
    instances = session.execute(
        select(ReminderInstance).where(
            ReminderInstance.invoice_id == invoice.id,
            ReminderInstance.status == ReminderInstanceStatus.scheduled,
        )
    ).scalars()

    now = now_utc()
    for instance in instances:
        before = _instance_snapshot(instance)
        instance.status = ReminderInstanceStatus.cancelled
        instance.cancelled_at = now
        instance.cancellation_reason = reason
        session.flush()
        record_audit(
            session,
            entity_type="reminder_instance",
            entity_id=instance.id,
            action="reminder_cancelled",
            actor_id=actor_id,
            before=before,
            after=_instance_snapshot(instance),
        )


def cancel_single_reminder(
    session: Session, instance: ReminderInstance, *, reason: str, actor_id: uuid.UUID
) -> ReminderInstance:
    """Admin manually cancels one individual scheduled reminder instance."""
    before = _instance_snapshot(instance)
    instance.status = ReminderInstanceStatus.cancelled
    instance.cancelled_at = now_utc()
    instance.cancellation_reason = reason
    session.flush()
    record_audit(
        session,
        entity_type="reminder_instance",
        entity_id=instance.id,
        action="reminder_cancelled",
        actor_id=actor_id,
        before=before,
        after=_instance_snapshot(instance),
    )
    session.commit()
    session.refresh(instance)
    return instance


def reschedule_single_reminder(
    session: Session, instance: ReminderInstance, *, new_scheduled_for: datetime, actor_id: uuid.UUID
) -> ReminderInstance:
    before = _instance_snapshot(instance)
    instance.scheduled_for = new_scheduled_for
    session.flush()
    record_audit(
        session,
        entity_type="reminder_instance",
        entity_id=instance.id,
        action="reminder_rescheduled",
        actor_id=actor_id,
        before=before,
        after=_instance_snapshot(instance),
    )
    session.commit()
    session.refresh(instance)
    return instance


def claim_reminder_instance(session: Session, instance_id: uuid.UUID) -> ReminderInstance | None:
    """Atomic claim: UPDATE ... WHERE status='scheduled' RETURNING *,
    combined with SELECT ... FOR UPDATE SKIP LOCKED semantics so concurrent
    workers skip already-locked rows instantly instead of blocking.
    Returns the claimed (now 'sending') instance, or None if it was already
    claimed/handled by another worker.
    """
    locked = session.execute(
        select(ReminderInstance)
        .where(ReminderInstance.id == instance_id, ReminderInstance.status == ReminderInstanceStatus.scheduled)
        .with_for_update(skip_locked=True)
    ).scalar_one_or_none()

    if locked is None:
        return None

    locked.status = ReminderInstanceStatus.sending
    locked.attempt_count = locked.attempt_count + 1
    session.flush()
    session.commit()
    session.refresh(locked)
    return locked


def is_kill_switch_enabled(session: Session) -> bool:
    setting = session.get(SystemSetting, KILL_SWITCH_KEY)
    if setting is None:
        return False
    return bool(setting.value.get("enabled", False))


def set_kill_switch(session: Session, *, enabled: bool, actor_id: uuid.UUID) -> SystemSetting:
    setting = session.get(SystemSetting, KILL_SWITCH_KEY)
    before = {"enabled": setting.value.get("enabled")} if setting else None
    if setting is None:
        setting = SystemSetting(key=KILL_SWITCH_KEY, value={"enabled": enabled})
        session.add(setting)
    else:
        setting.value = {"enabled": enabled}
    session.flush()
    record_audit(
        session,
        entity_type="system_setting",
        entity_id=uuid.uuid5(uuid.NAMESPACE_DNS, KILL_SWITCH_KEY),
        action="kill_switch_toggled",
        actor_id=actor_id,
        before=before,
        after={"enabled": enabled},
    )
    session.commit()
    session.refresh(setting)
    return setting


def raise_admin_alert(session: Session, instance: ReminderInstance) -> None:
    """Alert an Admin for manual follow-up after a reminder's retries are
    exhausted. v1 implements this as an audited event; a real notification
    channel (email/in-app) can be layered on the same audit trail later."""
    record_audit(
        session,
        entity_type="reminder_instance",
        entity_id=instance.id,
        action="admin_alert_reminder_failed",
        actor_id=None,
        before=None,
        after=_instance_snapshot(instance),
    )
    session.commit()


def _instance_snapshot(instance: ReminderInstance) -> dict:
    return {
        "id": str(instance.id),
        "invoice_id": str(instance.invoice_id),
        "rule_id": str(instance.rule_id),
        "scheduled_for": instance.scheduled_for.isoformat() if instance.scheduled_for else None,
        "status": instance.status.value if hasattr(instance.status, "value") else instance.status,
        "sent_at": instance.sent_at.isoformat() if instance.sent_at else None,
        "cancelled_at": instance.cancelled_at.isoformat() if instance.cancelled_at else None,
        "cancellation_reason": instance.cancellation_reason,
        "attempt_count": instance.attempt_count,
    }
