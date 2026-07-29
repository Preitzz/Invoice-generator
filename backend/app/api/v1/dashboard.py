from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.permissions import require_any_role
from app.models.user import User
from app.schemas.dashboard import DashboardSummary
from app.schemas.invoice import InvoiceRead
from app.schemas.payment import PaymentRead
from app.services.dashboard import get_dashboard_summary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db), _: User = Depends(require_any_role)) -> DashboardSummary:
    summary = get_dashboard_summary(db)
    return DashboardSummary(
        total_outstanding=summary["total_outstanding"],
        overdue_count=summary["overdue_count"],
        upcoming_due=[InvoiceRead.from_orm_with_overdue(inv) for inv in summary["upcoming_due"]],
        recent_payments=[PaymentRead.model_validate(p) for p in summary["recent_payments"]],
    )
