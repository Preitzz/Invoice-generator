"""create tax_rates table

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-29
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from alembic import op
from app.config import settings

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tax_rates",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("rate_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint(
            "rate_percent >= 0 AND rate_percent <= 100", name="ck_tax_rate_percent_range"
        ),
    )
    op.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON tax_rates TO "{settings.APP_DB_ROLE}";')


def downgrade() -> None:
    op.drop_table("tax_rates")
