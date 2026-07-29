"""seed one active default tax rate

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-29
"""

import datetime

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

tax_rates_table = sa.table(
    "tax_rates",
    sa.column("id", pg.UUID(as_uuid=True)),
    sa.column("name", sa.String),
    sa.column("rate_percent", sa.Numeric),
    sa.column("effective_from", sa.Date),
    sa.column("effective_to", sa.Date),
    sa.column("is_active", sa.Boolean),
)


def upgrade() -> None:
    op.bulk_insert(
        tax_rates_table,
        [
            {
                "name": "Standard Flat Rate",
                "rate_percent": 18.00,
                "effective_from": datetime.date.today(),
                "effective_to": None,
                "is_active": True,
            }
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM tax_rates WHERE name = 'Standard Flat Rate';")
