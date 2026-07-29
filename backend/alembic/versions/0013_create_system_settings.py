"""create system_settings key-value table for the reminder kill-switch

Revision ID: 0013
Revises: 0011
Create Date: 2026-07-29

Note: 0012 is intentionally skipped — the implementation plan (Section 3) reserves
it for a dedicated admin-user migration that is deliberately NOT implemented
(password seeding lives in seed/seed_dev.py, never in a migration).
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from alembic import op
from app.config import settings

revision = "0013"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", pg.JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON system_settings TO "{settings.APP_DB_ROLE}";')

    system_settings_table = sa.table(
        "system_settings",
        sa.column("key", sa.String),
        sa.column("value", pg.JSONB),
    )
    op.bulk_insert(
        system_settings_table,
        [{"key": "reminder_kill_switch", "value": {"enabled": settings.REMINDER_KILL_SWITCH_DEFAULT}}],
    )


def downgrade() -> None:
    op.drop_table("system_settings")
