import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class TaxRateCreate(BaseModel):
    name: str
    rate_percent: Decimal
    effective_from: date


class TaxRateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    rate_percent: Decimal
    effective_from: date
    effective_to: date | None
    is_active: bool
