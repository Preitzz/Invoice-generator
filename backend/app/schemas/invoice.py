import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.invoice import InvoiceStatus


class LineItemCreate(BaseModel):
    description: str
    quantity: Decimal
    unit_price: Decimal


class LineItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    description: str
    quantity: Decimal
    unit_price: Decimal
    tax_rate_snapshot: Decimal | None
    line_subtotal: Decimal
    line_tax: Decimal
    line_total: Decimal


class InvoiceCreate(BaseModel):
    customer_id: uuid.UUID
    due_date: date
    line_items: list[LineItemCreate]


class InvoiceUpdate(BaseModel):
    due_date: date | None = None
    line_items: list[LineItemCreate] | None = None


class InvoiceIssueRequest(BaseModel):
    note: str | None = None


class InvoiceCancelRequest(BaseModel):
    reason: str


class InvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invoice_number: str | None
    customer_id: uuid.UUID
    status: InvoiceStatus
    issue_date: date | None
    due_date: date
    currency: str
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    amount_paid: Decimal
    customer_name_snapshot: str | None
    customer_email_snapshot: str | None
    customer_address_snapshot: str | None
    cancelled_at: datetime | None
    cancellation_reason: str | None
    created_at: datetime
    updated_at: datetime
    is_overdue: bool = False
    line_items: list[LineItemRead] = []

    @classmethod
    def from_orm_with_overdue(cls, invoice) -> "InvoiceRead":
        from app.services.invoices import is_overdue

        obj = cls.model_validate(invoice)
        obj.is_overdue = is_overdue(invoice)
        obj.line_items = [LineItemRead.model_validate(li) for li in invoice.line_items]
        return obj
