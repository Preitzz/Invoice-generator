import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ReminderInstanceStatus(str, enum.Enum):
    scheduled = "scheduled"
    sending = "sending"
    sent = "sent"
    cancelled = "cancelled"
    failed = "failed"


class ReminderInstance(Base):
    __tablename__ = "reminder_instances"
    __table_args__ = (
        UniqueConstraint("invoice_id", "rule_id", name="uq_reminder_instance_invoice_rule"),
        Index("ix_reminder_instances_status_scheduled_for", "status", "scheduled_for"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reminder_rules.id"), nullable=False
    )
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[ReminderInstanceStatus] = mapped_column(
        Enum(ReminderInstanceStatus, name="reminder_instance_status"),
        nullable=False,
        default=ReminderInstanceStatus.scheduled,
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    invoice = relationship("Invoice", back_populates="reminder_instances")
    rule = relationship("ReminderRule")
