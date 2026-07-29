import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.permissions import require_any_role, require_staff
from app.models.invoice import InvoiceStatus
from app.models.user import User
from app.schemas.invoice import (
    InvoiceCancelRequest,
    InvoiceCreate,
    InvoiceIssueRequest,
    InvoiceRead,
    InvoiceUpdate,
)
from app.services import invoices as invoice_service

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("", response_model=list[InvoiceRead])
def list_invoices(
    status: InvoiceStatus | None = None,
    customer_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_role),
) -> list[InvoiceRead]:
    invoices = invoice_service.list_invoices(db, status=status, customer_id=customer_id)
    return [InvoiceRead.from_orm_with_overdue(inv) for inv in invoices]


@router.post("", response_model=InvoiceRead, status_code=201)
def create_invoice(
    payload: InvoiceCreate, db: Session = Depends(get_db), user: User = Depends(require_staff)
) -> InvoiceRead:
    invoice = invoice_service.create_draft_invoice(
        db,
        customer_id=payload.customer_id,
        due_date=payload.due_date,
        line_items=[li.model_dump() for li in payload.line_items],
        actor_id=user.id,
    )
    return InvoiceRead.from_orm_with_overdue(invoice)


@router.get("/{invoice_id}", response_model=InvoiceRead)
def get_invoice(
    invoice_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(require_any_role)
) -> InvoiceRead:
    invoice = invoice_service.get_invoice(db, invoice_id)
    return InvoiceRead.from_orm_with_overdue(invoice)


@router.patch("/{invoice_id}", response_model=InvoiceRead)
def update_invoice(
    invoice_id: uuid.UUID,
    payload: InvoiceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
) -> InvoiceRead:
    invoice = invoice_service.update_invoice(
        db,
        invoice_id,
        actor_id=user.id,
        due_date=payload.due_date,
        line_items=[li.model_dump() for li in payload.line_items] if payload.line_items is not None else None,
    )
    return InvoiceRead.from_orm_with_overdue(invoice)


@router.post("/{invoice_id}/issue", response_model=InvoiceRead)
def issue_invoice(
    invoice_id: uuid.UUID,
    payload: InvoiceIssueRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
) -> InvoiceRead:
    invoice = invoice_service.issue_invoice(db, invoice_id, actor_id=user.id)
    return InvoiceRead.from_orm_with_overdue(invoice)


@router.post("/{invoice_id}/cancel", response_model=InvoiceRead)
def cancel_invoice(
    invoice_id: uuid.UUID,
    payload: InvoiceCancelRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
) -> InvoiceRead:
    invoice = invoice_service.cancel_invoice(db, invoice_id, reason=payload.reason, actor_id=user.id)
    return InvoiceRead.from_orm_with_overdue(invoice)
