"""create payments table

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-29
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from alembic import op
from app.config import settings

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

payment_method = pg.ENUM("cash", "bank_transfer", "upi", "cheque", name="payment_method")


def upgrade() -> None:
    op.create_table(
        "payments",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("invoice_id", pg.UUID(as_uuid=True), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("method", payment_method, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("recorded_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_payment_amount_positive"),
    )
    # Payments are immutable once created (no UPDATE/DELETE route or service
    # method exists) — grant only SELECT/INSERT to the runtime role as
    # defense-in-depth, mirroring the audit_log enforcement pattern.
    op.execute(f'GRANT SELECT, INSERT ON payments TO "{settings.APP_DB_ROLE}";')


def downgrade() -> None:
    op.drop_table("payments")
    payment_method.drop(op.get_bind(), checkfirst=True)
