import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.timezone import ist_end_of_day, now_utc
from app.models.customer import Customer
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment

OPEN_STATUSES = (InvoiceStatus.draft, InvoiceStatus.issued, InvoiceStatus.partially_paid)

AGING_BUCKETS = [
    ("0-30", 0, 30),
    ("31-60", 31, 60),
    ("61-90", 61, 90),
    ("90+", 91, None),
]


def aging_report(session: Session) -> list[dict]:
    outstanding = list(
        session.execute(select(Invoice).where(Invoice.status.in_(OPEN_STATUSES))).scalars()
    )
    now = now_utc()
    buckets: dict[str, dict] = {label: {"invoices": [], "total": Decimal("0.00")} for label, _, _ in AGING_BUCKETS}

    for inv in outstanding:
        due_moment = ist_end_of_day(inv.due_date)
        if now <= due_moment:
            continue  # not overdue — excluded from aging buckets
        days_overdue = (now.date() - inv.due_date).days
        for label, lo, hi in AGING_BUCKETS:
            if days_overdue >= lo and (hi is None or days_overdue <= hi):
                buckets[label]["invoices"].append(inv)
                buckets[label]["total"] += Decimal(str(inv.total_amount)) - Decimal(str(inv.amount_paid))
                break

    return [
        {"range_label": label, "invoices": buckets[label]["invoices"], "total": buckets[label]["total"]}
        for label, _, _ in AGING_BUCKETS
    ]


def collections_report(session: Session, *, start: date, end: date) -> dict:
    payments = list(
        session.execute(
            select(Payment)
            .where(Payment.payment_date >= start, Payment.payment_date <= end)
            .order_by(Payment.payment_date)
        ).scalars()
    )
    total = sum((Decimal(str(p.amount)) for p in payments), Decimal("0.00"))
    return {"period_start": start, "period_end": end, "payments": payments, "total": total}


def customer_statement(session: Session, customer_id: uuid.UUID) -> dict:
    customer = session.get(Customer, customer_id)
    if customer is None:
        raise NotFoundError("Customer not found")

    invoices = list(
        session.execute(
            select(Invoice).where(Invoice.customer_id == customer_id).order_by(Invoice.created_at)
        ).scalars()
    )
    invoice_ids = [inv.id for inv in invoices]
    payments = (
        list(
            session.execute(
                select(Payment).where(Payment.invoice_id.in_(invoice_ids)).order_by(Payment.payment_date)
            ).scalars()
        )
        if invoice_ids
        else []
    )
    return {"customer": customer, "invoices": invoices, "payments": payments}
