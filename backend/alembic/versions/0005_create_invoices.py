"""create invoices table

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-29
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from alembic import op
from app.config import settings

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

invoice_status = pg.ENUM(
    "draft", "issued", "partially_paid", "paid", "cancelled", name="invoice_status"
)


def upgrade() -> None:
    op.create_table(
        "invoices",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("invoice_number", sa.String(20), nullable=True, unique=True),
        sa.Column("customer_id", pg.UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("status", invoice_status, nullable=False, server_default="draft"),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("amount_paid", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("customer_name_snapshot", sa.String(255), nullable=True),
        sa.Column("customer_email_snapshot", sa.String(255), nullable=True),
        sa.Column("customer_address_snapshot", sa.Text(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount_paid >= 0", name="ck_invoice_amount_paid_nonneg"),
        sa.CheckConstraint("amount_paid <= total_amount", name="ck_invoice_amount_paid_le_total"),
        sa.CheckConstraint("currency = 'INR'", name="ck_invoice_currency_inr"),
    )
    op.create_index("ix_invoices_customer_id", "invoices", ["customer_id"])
    op.create_index("ix_invoices_status", "invoices", ["status"])
    op.create_index("ix_invoices_due_date", "invoices", ["due_date"])

    # Sequence backing sequential invoice numbering, incremented only at Issue.
    op.execute("CREATE SEQUENCE IF NOT EXISTS invoice_number_seq START WITH 1;")
    op.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON invoices TO "{settings.APP_DB_ROLE}";')
    op.execute(f'GRANT USAGE, SELECT, UPDATE ON SEQUENCE invoice_number_seq TO "{settings.APP_DB_ROLE}";')


def downgrade() -> None:
    op.execute("DROP SEQUENCE IF EXISTS invoice_number_seq;")
    op.drop_index("ix_invoices_due_date", table_name="invoices")
    op.drop_index("ix_invoices_status", table_name="invoices")
    op.drop_index("ix_invoices_customer_id", table_name="invoices")
    op.drop_table("invoices")
    invoice_status.drop(op.get_bind(), checkfirst=True)
