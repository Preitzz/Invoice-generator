import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.reminder_instance import ReminderInstanceStatus


class ReminderRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    offset_days: int


class ReminderInstanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rule_code: str
    scheduled_for: datetime
    status: ReminderInstanceStatus
    sent_at: datetime | None
    cancelled_at: datetime | None
    cancellation_reason: str | None
    attempt_count: int

    @classmethod
    def from_instance(cls, instance) -> "ReminderInstanceRead":
        return cls(
            id=instance.id,
            rule_code=instance.rule.code,
            scheduled_for=instance.scheduled_for,
            status=instance.status,
            sent_at=instance.sent_at,
            cancelled_at=instance.cancelled_at,
            cancellation_reason=instance.cancellation_reason,
            attempt_count=instance.attempt_count,
        )


class ReminderRescheduleRequest(BaseModel):
    new_scheduled_for: datetime


class ReminderCancelRequest(BaseModel):
    reason: str
