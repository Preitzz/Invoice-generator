import uuid
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.permissions import require_any_role
from app.models.user import User
from app.schemas.customer import CustomerRead
from app.schemas.invoice import InvoiceRead
from app.schemas.payment import PaymentRead
from app.schemas.reports import AgingBucket, AgingReport, CollectionsReport, CustomerStatement
from app.services import reports as report_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/aging", response_model=AgingReport)
def aging(db: Session = Depends(get_db), _: User = Depends(require_any_role)) -> AgingReport:
    buckets = report_service.aging_report(db)
    return AgingReport(
        buckets=[
            AgingBucket(
                range_label=b["range_label"],
                invoices=[InvoiceRead.from_orm_with_overdue(inv) for inv in b["invoices"]],
                total=b["total"],
            )
            for b in buckets
        ]
    )


@router.get("/collections", response_model=CollectionsReport)
def collections(
    start: date, end: date, db: Session = Depends(get_db), _: User = Depends(require_any_role)
) -> CollectionsReport:
    report = report_service.collections_report(db, start=start, end=end)
    return CollectionsReport(
        period_start=report["period_start"],
        period_end=report["period_end"],
        payments=[PaymentRead.model_validate(p) for p in report["payments"]],
        total=report["total"],
    )


@router.get("/customer/{customer_id}", response_model=CustomerStatement)
def customer_statement(
    customer_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(require_any_role)
) -> CustomerStatement:
    report = report_service.customer_statement(db, customer_id)
    return CustomerStatement(
        customer=CustomerRead.model_validate(report["customer"]),
        invoices=[InvoiceRead.from_orm_with_overdue(inv) for inv in report["invoices"]],
        payments=[PaymentRead.model_validate(p) for p in report["payments"]],
    )
