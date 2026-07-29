"""Phase 7 gate: raw SQL DELETE against invoices / payments, issued as the
application's runtime DB role, must be rejected by Postgres itself — not
merely by absence of an app-level delete code path. Matches the enforcement
pattern used for audit_log immutability (see
test_audit_log_immutability.py) but for the 7-year retention guard on
invoices/payments (openspec specs/audit-logging/spec.md).

invoice_line_items is intentionally NOT covered here (see
0014_revoke_delete_invoices_payments.py's docstring): the spec's retention
requirement names only invoices, payments, and audit log entries, and
line items are legitimately deleted-and-recreated in place by
app.services.invoices.update_invoice when a draft invoice is edited.
"""

from datetime import date

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import ProgrammingError

from app.models.invoice import Invoice, InvoiceStatus
from app.models.invoice_line_item import InvoiceLineItem
from app.models.payment import Payment, PaymentMethod


def _make_invoice_with_line_item(db_session, customer):
    invoice = Invoice(
        customer_id=customer.id,
        status=InvoiceStatus.draft,
        due_date=date.today(),
        subtotal=100,
        tax_amount=0,
        total_amount=100,
        amount_paid=0,
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)

    line_item = InvoiceLineItem(
        invoice_id=invoice.id,
        description="Widget",
        quantity=1,
        unit_price=100,
        line_subtotal=100,
        line_tax=0,
        line_total=100,
    )
    db_session.add(line_item)
    db_session.commit()
    db_session.refresh(line_item)
    return invoice, line_item


def test_app_role_cannot_delete_invoice(db_session, customer):
    invoice, _ = _make_invoice_with_line_item(db_session, customer)

    with pytest.raises(ProgrammingError) as excinfo:
        db_session.execute(sa.text("DELETE FROM invoices WHERE id = :id"), {"id": invoice.id})
        db_session.commit()
    assert "permission denied" in str(excinfo.value).lower()
    db_session.rollback()


def test_app_role_can_still_delete_invoice_line_item(db_session, customer):
    """Defense against over-revocation: invoice_line_items DELETE is
    deliberately left grantable (not spec-required for retention) because
    app.services.invoices.update_invoice legitimately deletes and recreates
    a draft invoice's line items in place when they're edited."""
    _, line_item = _make_invoice_with_line_item(db_session, customer)

    db_session.execute(sa.text("DELETE FROM invoice_line_items WHERE id = :id"), {"id": line_item.id})
    db_session.commit()

    remaining = db_session.execute(
        sa.text("SELECT COUNT(*) FROM invoice_line_items WHERE id = :id"), {"id": line_item.id}
    ).scalar_one()
    assert remaining == 0


def test_app_role_cannot_delete_payment(db_session, customer, admin_user):
    invoice, _ = _make_invoice_with_line_item(db_session, customer)

    payment = Payment(
        invoice_id=invoice.id,
        amount=100,
        payment_date=date.today(),
        method=PaymentMethod.cash,
        recorded_by=admin_user.id,
    )
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)

    with pytest.raises(ProgrammingError) as excinfo:
        db_session.execute(sa.text("DELETE FROM payments WHERE id = :id"), {"id": payment.id})
        db_session.commit()
    assert "permission denied" in str(excinfo.value).lower()
    db_session.rollback()


def test_app_role_can_still_update_invoice(db_session, customer):
    """Defense against over-revocation: editing pre-full-payment invoices is
    a legitimate, spec-required operation and must remain possible."""
    invoice, _ = _make_invoice_with_line_item(db_session, customer)

    db_session.execute(
        sa.text("UPDATE invoices SET subtotal = 200 WHERE id = :id"), {"id": invoice.id}
    )
    db_session.commit()

    updated = db_session.execute(
        sa.text("SELECT subtotal FROM invoices WHERE id = :id"), {"id": invoice.id}
    ).scalar_one()
    assert float(updated) == 200
