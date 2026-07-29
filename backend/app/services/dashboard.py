from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.timezone import now_utc
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment
from app.services.invoices import is_overdue

OPEN_STATUSES = (InvoiceStatus.draft, InvoiceStatus.issued, InvoiceStatus.partially_paid)


def get_dashboard_summary(session: Session, *, upcoming_days: int = 14, recent_payments_limit: int = 10) -> dict:
    open_invoices = list(
        session.execute(select(Invoice).where(Invoice.status.in_(OPEN_STATUSES))).scalars()
    )

    total_outstanding = Decimal("0.00")
    overdue_count = 0
    now = now_utc()
    for inv in open_invoices:
        total_outstanding += Decimal(str(inv.total_amount)) - Decimal(str(inv.amount_paid))
        if is_overdue(inv, now=now):
            overdue_count += 1

    from datetime import date, timedelta

    upcoming_cutoff = date.today() + timedelta(days=upcoming_days)
    upcoming_due = [
        inv
        for inv in open_invoices
        if inv.due_date >= date.today() and inv.due_date <= upcoming_cutoff
    ]
    upcoming_due.sort(key=lambda i: i.due_date)

    recent_payments = list(
        session.execute(
            select(Payment).order_by(Payment.created_at.desc()).limit(recent_payments_limit)
        ).scalars()
    )

    return {
        "total_outstanding": total_outstanding,
        "overdue_count": overdue_count,
        "upcoming_due": upcoming_due,
        "recent_payments": recent_payments,
    }
