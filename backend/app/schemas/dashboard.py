from decimal import Decimal

from pydantic import BaseModel

from app.schemas.invoice import InvoiceRead
from app.schemas.payment import PaymentRead


class DashboardSummary(BaseModel):
    total_outstanding: Decimal
    overdue_count: int
    upcoming_due: list[InvoiceRead]
    recent_payments: list[PaymentRead]
