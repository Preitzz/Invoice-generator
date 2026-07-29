"""create reminder_instances table

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-29
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from alembic import op
from app.config import settings

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

reminder_instance_status = pg.ENUM(
    "scheduled", "sending", "sent", "cancelled", "failed", name="reminder_instance_status"
)


def upgrade() -> None:
    op.create_table(
        "reminder_instances",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("invoice_id", pg.UUID(as_uuid=True), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("rule_id", pg.UUID(as_uuid=True), sa.ForeignKey("reminder_rules.id"), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", reminder_instance_status, nullable=False, server_default="scheduled"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("invoice_id", "rule_id", name="uq_reminder_instance_invoice_rule"),
    )
    op.create_index(
        "ix_reminder_instances_status_scheduled_for",
        "reminder_instances",
        ["status", "scheduled_for"],
    )
    op.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON reminder_instances TO "{settings.APP_DB_ROLE}";')


def downgrade() -> None:
    op.drop_index("ix_reminder_instances_status_scheduled_for", table_name="reminder_instances")
    op.drop_table("reminder_instances")
    reminder_instance_status.drop(op.get_bind(), checkfirst=True)
