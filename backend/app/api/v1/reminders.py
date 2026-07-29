import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.exceptions import NotFoundError
from app.core.permissions import require_admin, require_any_role
from app.models.reminder_instance import ReminderInstance
from app.models.user import User
from app.schemas.reminder import ReminderCancelRequest, ReminderInstanceRead, ReminderRescheduleRequest
from app.services import reminders as reminder_service

router = APIRouter(prefix="/invoices/{invoice_id}/reminders", tags=["reminders"])


def _get_instance(db: Session, invoice_id: uuid.UUID, reminder_id: uuid.UUID) -> ReminderInstance:
    instance = db.execute(
        select(ReminderInstance).where(
            ReminderInstance.id == reminder_id, ReminderInstance.invoice_id == invoice_id
        )
    ).scalar_one_or_none()
    if instance is None:
        raise NotFoundError("Reminder instance not found")
    return instance


@router.get("", response_model=list[ReminderInstanceRead])
def list_reminders(
    invoice_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(require_any_role)
) -> list[ReminderInstanceRead]:
    instances = db.execute(
        select(ReminderInstance)
        .where(ReminderInstance.invoice_id == invoice_id)
        .order_by(ReminderInstance.scheduled_for)
    ).scalars()
    return [ReminderInstanceRead.from_instance(ri) for ri in instances]


@router.post("/{reminder_id}/cancel", response_model=ReminderInstanceRead)
def cancel_reminder(
    invoice_id: uuid.UUID,
    reminder_id: uuid.UUID,
    payload: ReminderCancelRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> ReminderInstanceRead:
    instance = _get_instance(db, invoice_id, reminder_id)
    instance = reminder_service.cancel_single_reminder(
        db, instance, reason=payload.reason or "manual override", actor_id=user.id
    )
    return ReminderInstanceRead.from_instance(instance)


@router.post("/{reminder_id}/reschedule", response_model=ReminderInstanceRead)
def reschedule_reminder(
    invoice_id: uuid.UUID,
    reminder_id: uuid.UUID,
    payload: ReminderRescheduleRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> ReminderInstanceRead:
    instance = _get_instance(db, invoice_id, reminder_id)
    instance = reminder_service.reschedule_single_reminder(
        db, instance, new_scheduled_for=payload.new_scheduled_for, actor_id=user.id
    )
    return ReminderInstanceRead.from_instance(instance)
