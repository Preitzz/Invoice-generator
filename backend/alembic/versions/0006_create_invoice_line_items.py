"""create invoice_line_items table

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-29
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from alembic import op
from app.config import settings

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "invoice_line_items",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "invoice_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("tax_rate_snapshot", sa.Numeric(5, 2), nullable=True),
        sa.Column("line_subtotal", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("line_tax", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.CheckConstraint("quantity > 0", name="ck_line_item_quantity_positive"),
        sa.CheckConstraint("unit_price >= 0", name="ck_line_item_unit_price_nonneg"),
    )
    op.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON invoice_line_items TO "{settings.APP_DB_ROLE}";')


def downgrade() -> None:
    op.drop_table("invoice_line_items")
