from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.permissions import require_admin, require_any_role
from app.models.user import User
from app.schemas.tax_rate import TaxRateCreate, TaxRateRead
from app.services import tax_rates as tax_rate_service

router = APIRouter(prefix="/tax-rates", tags=["tax-rates"])


@router.get("", response_model=list[TaxRateRead])
def list_tax_rates(db: Session = Depends(get_db), _: User = Depends(require_any_role)) -> list[TaxRateRead]:
    return [TaxRateRead.model_validate(r) for r in tax_rate_service.list_tax_rates(db)]


@router.post("", response_model=TaxRateRead, status_code=201)
def create_tax_rate(
    payload: TaxRateCreate, db: Session = Depends(get_db), user: User = Depends(require_admin)
) -> TaxRateRead:
    rate = tax_rate_service.create_tax_rate(
        db,
        name=payload.name,
        rate_percent=payload.rate_percent,
        effective_from=payload.effective_from,
        actor_id=user.id,
    )
    return TaxRateRead.model_validate(rate)
