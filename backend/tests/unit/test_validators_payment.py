from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.core.exceptions import DuplicatePaymentWarning, OverpaymentError
from app.models.invoice import InvoiceStatus
from app.models.payment import PaymentMethod
from app.services import invoices as invoice_service
from app.services import payments as payment_service
from tests.factories import make_line_item


def _issued_invoice(db_session, customer, admin_user, active_tax_rate, unit_price="100.00"):
    draft = invoice_service.create_draft_invoice(
        db_session,
        customer_id=customer.id,
        due_date=date.today() + timedelta(days=10),
        line_items=[make_line_item(unit_price=unit_price, quantity="1")],
        actor_id=admin_user.id,
    )
    return invoice_service.issue_invoice(db_session, draft.id, actor_id=admin_user.id)


def test_record_valid_payment_updates_amount_paid(db_session, customer, admin_user, active_tax_rate):
    invoice = _issued_invoice(db_session, customer, admin_user, active_tax_rate)
    partial = invoice.total_amount / 2

    payment, dup = payment_service.record_payment(
        db_session,
        invoice.id,
        amount=partial,
        payment_date=date.today(),
        method=PaymentMethod.cash,
        notes=None,
        recorded_by=admin_user.id,
    )
    db_session.refresh(invoice)
    assert dup is None
    assert invoice.amount_paid == partial
    assert invoice.status == InvoiceStatus.partially_paid


def test_overpayment_rejected_outright(db_session, customer, admin_user, active_tax_rate):
    invoice = _issued_invoice(db_session, customer, admin_user, active_tax_rate)
    with pytest.raises(OverpaymentError):
        payment_service.record_payment(
            db_session,
            invoice.id,
            amount=invoice.total_amount + Decimal("1.00"),
            payment_date=date.today(),
            method=PaymentMethod.cash,
            notes=None,
            recorded_by=admin_user.id,
        )
    db_session.refresh(invoice)
    assert invoice.amount_paid == Decimal("0.00")


def test_payment_exactly_matching_total_marks_paid_and_cancels_reminders(
    db_session, customer, admin_user, active_tax_rate
):
    from app.models.reminder_instance import ReminderInstance, ReminderInstanceStatus

    invoice = _issued_invoice(db_session, customer, admin_user, active_tax_rate)
    payment_service.record_payment(
        db_session,
        invoice.id,
        amount=invoice.total_amount,
        payment_date=date.today(),
        method=PaymentMethod.upi,
        notes=None,
        recorded_by=admin_user.id,
    )
    db_session.refresh(invoice)
    assert invoice.status == InvoiceStatus.paid

    remaining_scheduled = [
        ri
        for ri in db_session.query(ReminderInstance).filter(ReminderInstance.invoice_id == invoice.id)
        if ri.status == ReminderInstanceStatus.scheduled
    ]
    assert remaining_scheduled == []


def test_duplicate_payment_detected_and_requires_confirmation(db_session, customer, admin_user, active_tax_rate):
    invoice = _issued_invoice(db_session, customer, admin_user, active_tax_rate, unit_price="1000.00")
    amount = Decimal("100.00")

    payment_service.record_payment(
        db_session,
        invoice.id,
        amount=amount,
        payment_date=date.today(),
        method=PaymentMethod.cash,
        notes=None,
        recorded_by=admin_user.id,
    )

    with pytest.raises(DuplicatePaymentWarning):
        payment_service.record_payment(
            db_session,
            invoice.id,
            amount=amount,
            payment_date=date.today(),
            method=PaymentMethod.cash,
            notes=None,
            recorded_by=admin_user.id,
        )

    # Confirmed second submission still enforces overpayment validation, but
    # succeeds when within bounds.
    payment, dup = payment_service.record_payment(
        db_session,
        invoice.id,
        amount=amount,
        payment_date=date.today(),
        method=PaymentMethod.cash,
        notes=None,
        recorded_by=admin_user.id,
        confirm_duplicate=True,
    )
    assert dup is not None
    db_session.refresh(invoice)
    assert invoice.amount_paid == amount * 2


def test_partial_payment_keeps_reminders_scheduled(db_session, customer, admin_user, active_tax_rate):
    from app.models.reminder_instance import ReminderInstance, ReminderInstanceStatus

    invoice = _issued_invoice(db_session, customer, admin_user, active_tax_rate, unit_price="1000.00")
    payment_service.record_payment(
        db_session,
        invoice.id,
        amount=Decimal("10.00"),
        payment_date=date.today(),
        method=PaymentMethod.cash,
        notes=None,
        recorded_by=admin_user.id,
    )
    db_session.refresh(invoice)
    assert invoice.status == InvoiceStatus.partially_paid
    scheduled = [
        ri
        for ri in db_session.query(ReminderInstance).filter(ReminderInstance.invoice_id == invoice.id)
        if ri.status == ReminderInstanceStatus.scheduled
    ]
    assert len(scheduled) == 5
