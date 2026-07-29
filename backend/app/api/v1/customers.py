import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_any_role, require_staff
from app.models.user import User
from app.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate
from app.services import customers as customer_service

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=list[CustomerRead])
def list_customers(db: Session = Depends(get_db), _: User = Depends(require_any_role)) -> list[CustomerRead]:
    return [CustomerRead.model_validate(c) for c in customer_service.list_customers(db)]


@router.post("", response_model=CustomerRead, status_code=201)
def create_customer(
    payload: CustomerCreate, db: Session = Depends(get_db), user: User = Depends(require_staff)
) -> CustomerRead:
    customer = customer_service.create_customer(
        db,
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        billing_address=payload.billing_address,
        actor_id=user.id,
    )
    return CustomerRead.model_validate(customer)


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(
    customer_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(require_any_role)
) -> CustomerRead:
    return CustomerRead.model_validate(customer_service.get_customer(db, customer_id))


@router.patch("/{customer_id}", response_model=CustomerRead)
def update_customer(
    customer_id: uuid.UUID,
    payload: CustomerUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
) -> CustomerRead:
    customer = customer_service.update_customer(
        db,
        customer_id,
        actor_id=user.id,
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        billing_address=payload.billing_address,
    )
    return CustomerRead.model_validate(customer)


@router.delete("/{customer_id}", response_model=CustomerRead)
def delete_customer(
    customer_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(require_staff)
) -> CustomerRead:
    customer = customer_service.delete_customer(db, customer_id, actor_id=user.id)
    return CustomerRead.model_validate(customer)
