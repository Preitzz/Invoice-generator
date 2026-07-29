import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.permissions import require_any_role, require_staff
from app.models.user import User
from app.schemas.payment import PaymentCreate, PaymentCreateResponse, PaymentRead
from app.services import payments as payment_service

router = APIRouter(prefix="/invoices/{invoice_id}/payments", tags=["payments"])


@router.post("", response_model=PaymentCreateResponse, status_code=201)
def record_payment(
    invoice_id: uuid.UUID,
    payload: PaymentCreate,
    confirm_duplicate: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
) -> PaymentCreateResponse:
    payment, duplicate_of = payment_service.record_payment(
        db,
        invoice_id,
        amount=payload.amount,
        payment_date=payload.payment_date,
        method=payload.method,
        notes=payload.notes,
        recorded_by=user.id,
        confirm_duplicate=confirm_duplicate or payload.confirm_duplicate,
    )
    return PaymentCreateResponse(
        payment=PaymentRead.model_validate(payment),
        duplicate_warning=duplicate_of is not None,
        duplicate_of=duplicate_of.id if duplicate_of else None,
    )


@router.get("", response_model=list[PaymentRead])
def list_payments(
    invoice_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(require_any_role)
) -> list[PaymentRead]:
    return [PaymentRead.model_validate(p) for p in payment_service.list_payments(db, invoice_id)]
