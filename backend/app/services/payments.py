import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import DuplicatePaymentWarning, OverpaymentError
from app.core.rounding import round_half_up
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment, PaymentMethod
from app.services.audit import record_audit
from app.services.invoices import cancel_remaining_reminders, get_invoice

DUPLICATE_WINDOW_MINUTES = 60


def assert_no_overpayment(invoice: Invoice, new_payment_amount: Decimal) -> None:
    amount_paid = Decimal(str(invoice.amount_paid))
    total_amount = Decimal(str(invoice.total_amount))
    if amount_paid + new_payment_amount > total_amount:
        raise OverpaymentError(
            f"Payment of {new_payment_amount} would bring amount_paid to "
            f"{amount_paid + new_payment_amount}, exceeding total_amount {total_amount}"
        )


def detect_duplicate_payment(
    session: Session, invoice: Invoice, amount: Decimal, *, window_minutes: int = DUPLICATE_WINDOW_MINUTES
) -> Payment | None:
    """Heuristic: same amount recorded on the same invoice within a short
    time window."""
    cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
    return session.execute(
        select(Payment)
        .where(
            Payment.invoice_id == invoice.id,
            Payment.amount == amount,
            Payment.created_at >= cutoff,
        )
        .order_by(Payment.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def recompute_invoice_status_after_payment(session: Session, invoice: Invoice, *, actor_id: uuid.UUID) -> None:
    amount_paid = Decimal(str(invoice.amount_paid))
    total_amount = Decimal(str(invoice.total_amount))

    if amount_paid == total_amount and total_amount > 0:
        invoice.status = InvoiceStatus.paid
        session.flush()
        cancel_remaining_reminders(session, invoice, reason="invoice paid", actor_id=actor_id)
    elif 0 < amount_paid < total_amount:
        invoice.status = InvoiceStatus.partially_paid
        session.flush()


def record_payment(
    session: Session,
    invoice_id: uuid.UUID,
    *,
    amount: Decimal,
    payment_date: date,
    method: PaymentMethod,
    notes: str | None,
    recorded_by: uuid.UUID,
    confirm_duplicate: bool = False,
) -> tuple[Payment, Payment | None]:
    """Returns (payment, duplicate_of). Raises DuplicatePaymentWarning if a
    likely-duplicate is found and confirm_duplicate is False (caller/API
    surfaces this as a 409 requiring explicit confirmation before retry)."""
    invoice = get_invoice(session, invoice_id)

    duplicate_of = detect_duplicate_payment(session, invoice, amount)
    if duplicate_of is not None and not confirm_duplicate:
        raise DuplicatePaymentWarning(
            f"A payment of {amount} was already recorded on this invoice within the last "
            f"{DUPLICATE_WINDOW_MINUTES} minutes; confirm to proceed anyway."
        )

    assert_no_overpayment(invoice, amount)

    payment = Payment(
        invoice_id=invoice.id,
        amount=amount,
        payment_date=payment_date,
        method=method,
        notes=notes,
        recorded_by=recorded_by,
    )
    session.add(payment)

    invoice.amount_paid = round_half_up(Decimal(str(invoice.amount_paid)) + amount)
    session.flush()

    recompute_invoice_status_after_payment(session, invoice, actor_id=recorded_by)

    record_audit(
        session,
        entity_type="payment",
        entity_id=payment.id,
        action="payment_recorded",
        actor_id=recorded_by,
        before=None,
        after=_payment_snapshot(payment),
    )
    session.commit()
    session.refresh(payment)
    return payment, (duplicate_of if confirm_duplicate else None)


def list_payments(session: Session, invoice_id: uuid.UUID) -> list[Payment]:
    return list(
        session.execute(
            select(Payment).where(Payment.invoice_id == invoice_id).order_by(Payment.created_at.desc())
        ).scalars()
    )


def _payment_snapshot(payment: Payment) -> dict:
    return {
        "id": str(payment.id),
        "invoice_id": str(payment.invoice_id),
        "amount": str(payment.amount),
        "payment_date": payment.payment_date.isoformat(),
        "method": payment.method.value if hasattr(payment.method, "value") else payment.method,
        "notes": payment.notes,
        "recorded_by": str(payment.recorded_by),
    }
