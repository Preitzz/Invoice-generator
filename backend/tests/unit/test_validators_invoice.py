from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.core.exceptions import (
    CancelWithPaymentsError,
    EditBelowPaymentsError,
    InvalidStateTransitionError,
    InvoiceNotEditableError,
)
from app.models.invoice import InvoiceStatus
from app.services import invoices as invoice_service
from tests.factories import make_line_item


def _make_draft(db_session, customer, admin_user, due_date=None):
    return invoice_service.create_draft_invoice(
        db_session,
        customer_id=customer.id,
        due_date=due_date or (date.today() + timedelta(days=10)),
        line_items=[make_line_item(unit_price="100.00", quantity="2")],
        actor_id=admin_user.id,
    )


def test_create_draft_has_no_invoice_number(db_session, customer, admin_user):
    invoice = _make_draft(db_session, customer, admin_user)
    assert invoice.status == InvoiceStatus.draft
    assert invoice.invoice_number is None


def test_issue_assigns_sequential_number_and_snapshots_tax(db_session, customer, admin_user, active_tax_rate):
    invoice = _make_draft(db_session, customer, admin_user)
    issued = invoice_service.issue_invoice(db_session, invoice.id, actor_id=admin_user.id)
    assert issued.invoice_number is not None
    assert issued.invoice_number.startswith("INV-")
    assert issued.status == InvoiceStatus.issued
    assert issued.tax_amount > 0
    assert issued.total_amount == issued.subtotal + issued.tax_amount
    assert issued.line_items[0].tax_rate_snapshot == active_tax_rate.rate_percent


def test_issue_numbers_are_sequential_and_never_reused_for_abandoned_drafts(
    db_session, customer, admin_user, active_tax_rate
):
    abandoned = _make_draft(db_session, customer, admin_user)  # never issued
    first = _make_draft(db_session, customer, admin_user)
    second = _make_draft(db_session, customer, admin_user)

    issued_first = invoice_service.issue_invoice(db_session, first.id, actor_id=admin_user.id)
    issued_second = invoice_service.issue_invoice(db_session, second.id, actor_id=admin_user.id)

    n1 = int(issued_first.invoice_number.split("-")[1])
    n2 = int(issued_second.invoice_number.split("-")[1])
    assert n2 == n1 + 1


def test_only_draft_can_be_issued(db_session, customer, admin_user, active_tax_rate):
    invoice = _make_draft(db_session, customer, admin_user)
    invoice_service.issue_invoice(db_session, invoice.id, actor_id=admin_user.id)
    with pytest.raises(InvalidStateTransitionError):
        invoice_service.issue_invoice(db_session, invoice.id, actor_id=admin_user.id)


def test_edit_blocked_once_fully_paid(db_session, customer, admin_user, active_tax_rate):
    invoice = _make_draft(db_session, customer, admin_user)
    issued = invoice_service.issue_invoice(db_session, invoice.id, actor_id=admin_user.id)
    issued.status = InvoiceStatus.paid
    db_session.flush()
    db_session.commit()

    with pytest.raises(InvoiceNotEditableError):
        invoice_service.update_invoice(
            db_session, issued.id, actor_id=admin_user.id, due_date=date.today() + timedelta(days=30)
        )


def test_edit_blocked_below_amount_paid(db_session, customer, admin_user, active_tax_rate):
    invoice = _make_draft(db_session, customer, admin_user)
    issued = invoice_service.issue_invoice(db_session, invoice.id, actor_id=admin_user.id)
    issued.amount_paid = issued.total_amount
    db_session.flush()
    db_session.commit()

    with pytest.raises(EditBelowPaymentsError):
        invoice_service.update_invoice(
            db_session,
            issued.id,
            actor_id=admin_user.id,
            line_items=[make_line_item(unit_price="1.00", quantity="1")],
        )


def test_edit_allowed_before_full_payment(db_session, customer, admin_user, active_tax_rate):
    invoice = _make_draft(db_session, customer, admin_user)
    issued = invoice_service.issue_invoice(db_session, invoice.id, actor_id=admin_user.id)
    updated = invoice_service.update_invoice(
        db_session, issued.id, actor_id=admin_user.id, due_date=date.today() + timedelta(days=45)
    )
    assert updated.due_date == date.today() + timedelta(days=45)


def test_cancel_blocked_once_payment_exists(db_session, customer, admin_user, active_tax_rate):
    invoice = _make_draft(db_session, customer, admin_user)
    issued = invoice_service.issue_invoice(db_session, invoice.id, actor_id=admin_user.id)
    issued.amount_paid = Decimal("1.00")
    db_session.flush()
    db_session.commit()

    with pytest.raises(CancelWithPaymentsError):
        invoice_service.cancel_invoice(db_session, issued.id, reason="test", actor_id=admin_user.id)


def test_cancel_allowed_with_no_payments(db_session, customer, admin_user, active_tax_rate):
    invoice = _make_draft(db_session, customer, admin_user)
    issued = invoice_service.issue_invoice(db_session, invoice.id, actor_id=admin_user.id)
    cancelled = invoice_service.cancel_invoice(db_session, issued.id, reason="test", actor_id=admin_user.id)
    assert cancelled.status == InvoiceStatus.cancelled
    assert cancelled.cancellation_reason == "test"
    assert cancelled.cancelled_at is not None


def test_is_overdue_false_before_end_of_due_date_ist(db_session, customer, admin_user, active_tax_rate):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    invoice = _make_draft(db_session, customer, admin_user, due_date=date.today() + timedelta(days=1))
    issued = invoice_service.issue_invoice(db_session, invoice.id, actor_id=admin_user.id)
    now = datetime.now(ZoneInfo("UTC"))
    assert invoice_service.is_overdue(issued, now=now) is False


def test_is_overdue_true_after_end_of_due_date_ist(db_session, customer, admin_user, active_tax_rate):
    from app.core.timezone import ist_end_of_day

    invoice = _make_draft(db_session, customer, admin_user, due_date=date.today() - timedelta(days=1))
    issued = invoice_service.issue_invoice(db_session, invoice.id, actor_id=admin_user.id)
    past_due_moment = ist_end_of_day(invoice.due_date) + timedelta(seconds=1)
    assert invoice_service.is_overdue(issued, now=past_due_moment) is True


def test_overdue_never_applies_to_paid_or_cancelled(db_session, customer, admin_user, active_tax_rate):
    invoice = _make_draft(db_session, customer, admin_user, due_date=date.today() - timedelta(days=5))
    issued = invoice_service.issue_invoice(db_session, invoice.id, actor_id=admin_user.id)
    issued.status = InvoiceStatus.paid
    db_session.flush()
    assert invoice_service.is_overdue(issued) is False

    issued.status = InvoiceStatus.cancelled
    db_session.flush()
    assert invoice_service.is_overdue(issued) is False


def test_totals_never_use_float_and_round_half_up(db_session, customer, admin_user, active_tax_rate):
    invoice = invoice_service.create_draft_invoice(
        db_session,
        customer_id=customer.id,
        due_date=date.today() + timedelta(days=10),
        line_items=[make_line_item(unit_price="10.005", quantity="1")],
        actor_id=admin_user.id,
    )
    assert isinstance(invoice.subtotal, Decimal)
    # 10.005 * 1 rounds half-up to 10.01
    assert invoice.subtotal == Decimal("10.01")
