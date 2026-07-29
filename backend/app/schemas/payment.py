import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.payment import PaymentMethod


class PaymentCreate(BaseModel):
    amount: Decimal
    payment_date: date
    method: PaymentMethod
    notes: str | None = None
    confirm_duplicate: bool = False


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invoice_id: uuid.UUID
    amount: Decimal
    payment_date: date
    method: PaymentMethod
    notes: str | None
    recorded_by: uuid.UUID
    created_at: datetime


class PaymentCreateResponse(BaseModel):
    payment: PaymentRead
    duplicate_warning: bool = False
    duplicate_of: uuid.UUID | None = None
