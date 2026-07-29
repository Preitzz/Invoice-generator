from datetime import date, timedelta

from app.core.exceptions import CustomerHasOpenInvoicesError
from app.models.invoice import InvoiceStatus
from app.services import customers as customer_service
from app.services import invoices as invoice_service
from tests.factories import make_line_item


def test_assert_no_open_invoices_blocks_when_open_invoice_exists(db_session, customer, admin_user):
    invoice_service.create_draft_invoice(
        db_session,
        customer_id=customer.id,
        due_date=date.today() + timedelta(days=10),
        line_items=[make_line_item()],
        actor_id=admin_user.id,
    )
    import pytest

    with pytest.raises(CustomerHasOpenInvoicesError):
        customer_service.assert_no_open_invoices(db_session, customer)


def test_soft_delete_leaves_history_intact(db_session, customer, admin_user, active_tax_rate):
    draft = invoice_service.create_draft_invoice(
        db_session,
        customer_id=customer.id,
        due_date=date.today() + timedelta(days=10),
        line_items=[make_line_item()],
        actor_id=admin_user.id,
    )
    issued = invoice_service.issue_invoice(db_session, draft.id, actor_id=admin_user.id)
    invoice_service.cancel_invoice(db_session, issued.id, reason="unwanted", actor_id=admin_user.id)

    deleted = customer_service.delete_customer(db_session, customer.id, actor_id=admin_user.id)
    assert deleted.is_active is False

    still_there = invoice_service.get_invoice(db_session, issued.id)
    assert still_there.status == InvoiceStatus.cancelled


def test_customer_update_does_not_affect_issued_invoice_snapshot(db_session, customer, admin_user, active_tax_rate):
    draft = invoice_service.create_draft_invoice(
        db_session,
        customer_id=customer.id,
        due_date=date.today() + timedelta(days=10),
        line_items=[make_line_item()],
        actor_id=admin_user.id,
    )
    issued = invoice_service.issue_invoice(db_session, draft.id, actor_id=admin_user.id)
    original_email_snapshot = issued.customer_email_snapshot

    customer_service.update_customer(db_session, customer.id, actor_id=admin_user.id, email="changed@example.com")

    db_session.refresh(issued)
    assert issued.customer_email_snapshot == original_email_snapshot
    assert issued.customer_email_snapshot != "changed@example.com"
