import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_line_item_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_line_item_unit_price_nonneg"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    tax_rate_snapshot: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    line_subtotal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    line_tax: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    line_total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    invoice = relationship("Invoice", back_populates="line_items")
