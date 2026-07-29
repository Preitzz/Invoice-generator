import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.exceptions import (
    CancelWithPaymentsError,
    EditBelowPaymentsError,
    InvoiceNotEditableError,
    NotFoundError,
)
from app.core.rounding import round_half_up
from app.core.timezone import ist_end_of_day, now_utc
from app.models.invoice import Invoice, InvoiceStatus
from app.models.invoice_line_item import InvoiceLineItem
from app.services.audit import record_audit
from app.services.reminders import cancel_remaining_reminders, recalculate_scheduled_reminders, schedule_reminders_for_invoice
from app.services.tax_rates import get_active_tax_rate

EDITABLE_STATUSES = (InvoiceStatus.draft, InvoiceStatus.issued, InvoiceStatus.partially_paid)
CANCELLABLE_STATUSES = (InvoiceStatus.draft, InvoiceStatus.issued, InvoiceStatus.partially_paid)


# ---------------------------------------------------------------------------
# Status derivation
# ---------------------------------------------------------------------------


def is_overdue(invoice: Invoice, now: "datetime | None" = None) -> bool:  # noqa: F821
    if invoice.status in (InvoiceStatus.paid, InvoiceStatus.cancelled):
        return False
    now = now or now_utc()
    return ist_end_of_day(invoice.due_date) < now


def derive_status(invoice: Invoice) -> InvoiceStatus:
    """Overdue is a derived, computed flag — never a stored status. This
    returns the *stored* status; use is_overdue() separately for the
    Overdue flag surfaced by reads/reports."""
    return invoice.status


# ---------------------------------------------------------------------------
# Totals computation (single source of truth — reports never recompute)
# ---------------------------------------------------------------------------


def _compute_totals(
    line_items: list[dict], tax_rate_percent: Decimal | None
) -> tuple[Decimal, Decimal, Decimal, list[dict]]:
    computed_lines = []
    subtotal = Decimal("0.00")
    for li in line_items:
        quantity = Decimal(str(li["quantity"]))
        unit_price = Decimal(str(li["unit_price"]))
        line_subtotal = round_half_up(quantity * unit_price)
        subtotal += line_subtotal
        computed_lines.append({**li, "line_subtotal": line_subtotal})
    subtotal = round_half_up(subtotal)

    rate = tax_rate_percent if tax_rate_percent is not None else Decimal("0")
    tax_amount = Decimal("0.00")
    for cl in computed_lines:
        line_tax = round_half_up(cl["line_subtotal"] * rate / Decimal("100"))
        cl["line_tax"] = line_tax
        cl["line_total"] = round_half_up(cl["line_subtotal"] + line_tax)
        tax_amount += line_tax
    tax_amount = round_half_up(tax_amount)
    total_amount = round_half_up(subtotal + tax_amount)
    return subtotal, tax_amount, total_amount, computed_lines


# ---------------------------------------------------------------------------
# Validators (Section 6 of the plan)
# ---------------------------------------------------------------------------


def assert_not_paid_for_edit(invoice: Invoice) -> None:
    if invoice.status == InvoiceStatus.paid:
        raise InvoiceNotEditableError("Invoice is fully paid and cannot be edited")
    if invoice.status == InvoiceStatus.cancelled:
        raise InvoiceNotEditableError("Cancelled invoices cannot be edited")


def assert_total_not_below_paid(new_total: Decimal, amount_paid: Decimal) -> None:
    if new_total < amount_paid:
        raise EditBelowPaymentsError(
            f"New total {new_total} would be below amount already paid {amount_paid}"
        )


def assert_no_payments_for_cancel(invoice: Invoice) -> None:
    if Decimal(str(invoice.amount_paid)) > 0:
        raise CancelWithPaymentsError("Cannot cancel an invoice with recorded payments")


# ---------------------------------------------------------------------------
# CRUD / lifecycle
# ---------------------------------------------------------------------------


def get_invoice(session: Session, invoice_id: uuid.UUID) -> Invoice:
    invoice = session.get(Invoice, invoice_id)
    if invoice is None:
        raise NotFoundError("Invoice not found")
    return invoice


def list_invoices(
    session: Session, *, status: InvoiceStatus | None = None, customer_id: uuid.UUID | None = None
) -> list[Invoice]:
    stmt = select(Invoice)
    if status is not None:
        stmt = stmt.where(Invoice.status == status)
    if customer_id is not None:
        stmt = stmt.where(Invoice.customer_id == customer_id)
    stmt = stmt.order_by(Invoice.created_at.desc())
    return list(session.execute(stmt).scalars())


def create_draft_invoice(
    session: Session,
    *,
    customer_id: uuid.UUID,
    due_date: date,
    line_items: list[dict],
    actor_id: uuid.UUID,
) -> Invoice:
    subtotal, tax_amount, total_amount, computed_lines = _compute_totals(line_items, tax_rate_percent=None)
    # Draft invoices carry unrounded/pre-tax working totals from line items
    # alone (no tax snapshot yet — that happens at Issue).
    invoice = Invoice(
        customer_id=customer_id,
        status=InvoiceStatus.draft,
        due_date=due_date,
        subtotal=subtotal,
        tax_amount=Decimal("0.00"),
        total_amount=subtotal,
        amount_paid=Decimal("0.00"),
    )
    session.add(invoice)
    session.flush()

    for cl in computed_lines:
        session.add(
            InvoiceLineItem(
                invoice_id=invoice.id,
                description=cl["description"],
                quantity=Decimal(str(cl["quantity"])),
                unit_price=Decimal(str(cl["unit_price"])),
                tax_rate_snapshot=None,
                line_subtotal=cl["line_subtotal"],
                line_tax=Decimal("0.00"),
                line_total=cl["line_subtotal"],
            )
        )
    session.flush()

    record_audit(
        session,
        entity_type="invoice",
        entity_id=invoice.id,
        action="invoice_created",
        actor_id=actor_id,
        before=None,
        after=_invoice_snapshot(invoice),
    )
    session.commit()
    session.refresh(invoice)
    return invoice


def update_invoice(
    session: Session,
    invoice_id: uuid.UUID,
    *,
    actor_id: uuid.UUID,
    due_date: date | None = None,
    line_items: list[dict] | None = None,
) -> Invoice:
    invoice = get_invoice(session, invoice_id)
    assert_not_paid_for_edit(invoice)
    before = _invoice_snapshot(invoice)
    due_date_changed = due_date is not None and due_date != invoice.due_date

    tax_rate_percent = None
    if invoice.status != InvoiceStatus.draft:
        # Already-issued invoices keep their snapshotted tax rate immutable.
        existing_line = invoice.line_items[0] if invoice.line_items else None
        tax_rate_percent = (
            Decimal(str(existing_line.tax_rate_snapshot))
            if existing_line and existing_line.tax_rate_snapshot is not None
            else None
        )

    if line_items is not None:
        subtotal, tax_amount, total_amount, computed_lines = _compute_totals(line_items, tax_rate_percent)
        assert_total_not_below_paid(total_amount, Decimal(str(invoice.amount_paid)))

        for li in list(invoice.line_items):
            session.delete(li)
        session.flush()

        for cl in computed_lines:
            session.add(
                InvoiceLineItem(
                    invoice_id=invoice.id,
                    description=cl["description"],
                    quantity=Decimal(str(cl["quantity"])),
                    unit_price=Decimal(str(cl["unit_price"])),
                    tax_rate_snapshot=tax_rate_percent,
                    line_subtotal=cl["line_subtotal"],
                    line_tax=cl.get("line_tax", Decimal("0.00")),
                    line_total=cl.get("line_total", cl["line_subtotal"]),
                )
            )
        invoice.subtotal = subtotal
        invoice.tax_amount = tax_amount
        invoice.total_amount = total_amount

    if due_date is not None:
        invoice.due_date = due_date

    session.flush()

    if due_date_changed:
        recalculate_scheduled_reminders(session, invoice, due_date)

    record_audit(
        session,
        entity_type="invoice",
        entity_id=invoice.id,
        action="invoice_updated",
        actor_id=actor_id,
        before=before,
        after=_invoice_snapshot(invoice),
    )
    session.commit()
    session.refresh(invoice)
    return invoice


def assign_invoice_number(session: Session) -> str:
    """Sequential invoice numbering assigned only at Issue time, via a DB
    sequence never touched by draft creation."""
    next_val = session.execute(text("SELECT nextval('invoice_number_seq')")).scalar_one()
    return f"INV-{next_val:04d}"


def snapshot_tax_and_totals(invoice: Invoice, tax_rate_percent: Decimal) -> None:
    """Snapshots the effective tax rate onto the invoice and each line item
    at issuance time, recomputing totals with tax now applied."""
    subtotal = Decimal("0.00")
    tax_amount = Decimal("0.00")
    for li in invoice.line_items:
        line_subtotal = round_half_up(Decimal(str(li.quantity)) * Decimal(str(li.unit_price)))
        line_tax = round_half_up(line_subtotal * tax_rate_percent / Decimal("100"))
        li.line_subtotal = line_subtotal
        li.line_tax = line_tax
        li.line_total = round_half_up(line_subtotal + line_tax)
        li.tax_rate_snapshot = tax_rate_percent
        subtotal += line_subtotal
        tax_amount += line_tax

    invoice.subtotal = round_half_up(subtotal)
    invoice.tax_amount = round_half_up(tax_amount)
    invoice.total_amount = round_half_up(invoice.subtotal + invoice.tax_amount)


def issue_invoice(session: Session, invoice_id: uuid.UUID, *, actor_id: uuid.UUID) -> Invoice:
    from app.core.exceptions import InvalidStateTransitionError

    invoice = get_invoice(session, invoice_id)
    if invoice.status != InvoiceStatus.draft:
        raise InvalidStateTransitionError("Only Draft invoices can be issued")

    before = _invoice_snapshot(invoice)

    customer = invoice.customer if hasattr(invoice, "customer") else None
    if customer is None:
        from app.models.customer import Customer

        customer = session.get(Customer, invoice.customer_id)

    tax_rate = get_active_tax_rate(session)

    invoice.invoice_number = assign_invoice_number(session)
    invoice.issue_date = date.today()
    invoice.customer_name_snapshot = customer.name
    invoice.customer_email_snapshot = customer.email
    invoice.customer_address_snapshot = customer.billing_address
    snapshot_tax_and_totals(invoice, Decimal(str(tax_rate.rate_percent)))
    invoice.status = InvoiceStatus.issued

    session.flush()

    schedule_reminders_for_invoice(session, invoice)

    record_audit(
        session,
        entity_type="invoice",
        entity_id=invoice.id,
        action="invoice_issued",
        actor_id=actor_id,
        before=before,
        after=_invoice_snapshot(invoice),
    )
    session.commit()
    session.refresh(invoice)
    return invoice


def cancel_invoice(session: Session, invoice_id: uuid.UUID, *, reason: str, actor_id: uuid.UUID) -> Invoice:
    invoice = get_invoice(session, invoice_id)
    if invoice.status not in CANCELLABLE_STATUSES:
        from app.core.exceptions import InvalidStateTransitionError

        raise InvalidStateTransitionError(f"Cannot cancel an invoice in status {invoice.status}")
    assert_no_payments_for_cancel(invoice)

    before = _invoice_snapshot(invoice)
    invoice.status = InvoiceStatus.cancelled
    invoice.cancelled_at = now_utc()
    invoice.cancellation_reason = reason
    session.flush()

    cancel_remaining_reminders(session, invoice, reason="invoice cancelled", actor_id=actor_id)

    record_audit(
        session,
        entity_type="invoice",
        entity_id=invoice.id,
        action="invoice_cancelled",
        actor_id=actor_id,
        before=before,
        after=_invoice_snapshot(invoice),
    )
    session.commit()
    session.refresh(invoice)
    return invoice


def _invoice_snapshot(invoice: Invoice) -> dict:
    return {
        "id": str(invoice.id),
        "invoice_number": invoice.invoice_number,
        "customer_id": str(invoice.customer_id),
        "status": invoice.status.value if hasattr(invoice.status, "value") else invoice.status,
        "issue_date": invoice.issue_date.isoformat() if invoice.issue_date else None,
        "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
        "subtotal": str(invoice.subtotal),
        "tax_amount": str(invoice.tax_amount),
        "total_amount": str(invoice.total_amount),
        "amount_paid": str(invoice.amount_paid),
        "cancelled_at": invoice.cancelled_at.isoformat() if invoice.cancelled_at else None,
        "cancellation_reason": invoice.cancellation_reason,
    }
