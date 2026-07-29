"""create reminder_rules table + seed fixed 5 rows

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-29
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from alembic import op
from app.config import settings

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

REMINDER_RULES = [
    ("before_due_3d", -3, "reminder_before_due"),
    ("on_due", 0, "reminder_on_due"),
    ("overdue_7d", 7, "reminder_overdue"),
    ("overdue_14d", 14, "reminder_overdue"),
    ("overdue_30d", 30, "reminder_overdue"),
]

reminder_rules_table = sa.table(
    "reminder_rules",
    sa.column("id", pg.UUID(as_uuid=True)),
    sa.column("code", sa.String),
    sa.column("offset_days", sa.Integer),
    sa.column("template_id", sa.String),
)


def upgrade() -> None:
    op.create_table(
        "reminder_rules",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("offset_days", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.String(100), nullable=False),
    )
    op.bulk_insert(
        reminder_rules_table,
        [
            {"code": code, "offset_days": offset_days, "template_id": template_id}
            for code, offset_days, template_id in REMINDER_RULES
        ],
    )
    # Not user-editable via API in v1 — runtime role gets SELECT only.
    op.execute(f'GRANT SELECT ON reminder_rules TO "{settings.APP_DB_ROLE}";')


def downgrade() -> None:
    op.drop_table("reminder_rules")
