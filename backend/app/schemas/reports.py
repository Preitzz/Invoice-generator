from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.customer import CustomerRead
from app.schemas.invoice import InvoiceRead
from app.schemas.payment import PaymentRead


class AgingBucket(BaseModel):
    range_label: str
    invoices: list[InvoiceRead]
    total: Decimal


class AgingReport(BaseModel):
    buckets: list[AgingBucket]


class CollectionsReport(BaseModel):
    period_start: date
    period_end: date
    payments: list[PaymentRead]
    total: Decimal


class CustomerStatement(BaseModel):
    customer: CustomerRead
    invoices: list[InvoiceRead]
    payments: list[PaymentRead]
