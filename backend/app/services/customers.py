import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import CustomerHasOpenInvoicesError, NotFoundError
from app.models.customer import Customer
from app.models.invoice import Invoice, InvoiceStatus
from app.services.audit import record_audit

OPEN_STATUSES = (
    InvoiceStatus.draft,
    InvoiceStatus.issued,
    InvoiceStatus.partially_paid,
)


def get_customer(session: Session, customer_id: uuid.UUID) -> Customer:
    customer = session.get(Customer, customer_id)
    if customer is None:
        raise NotFoundError("Customer not found")
    return customer


def list_customers(session: Session) -> list[Customer]:
    return list(session.execute(select(Customer).order_by(Customer.name)).scalars())


def create_customer(
    session: Session, *, name: str, email: str, phone: str | None, billing_address: str, actor_id: uuid.UUID
) -> Customer:
    customer = Customer(name=name, email=email, phone=phone, billing_address=billing_address)
    session.add(customer)
    session.flush()
    record_audit(
        session,
        entity_type="customer",
        entity_id=customer.id,
        action="customer_created",
        actor_id=actor_id,
        before=None,
        after=_snapshot(customer),
    )
    session.commit()
    session.refresh(customer)
    return customer


def update_customer(
    session: Session,
    customer_id: uuid.UUID,
    *,
    actor_id: uuid.UUID,
    name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    billing_address: str | None = None,
) -> Customer:
    customer = get_customer(session, customer_id)
    before = _snapshot(customer)

    if name is not None:
        customer.name = name
    if email is not None:
        customer.email = email
    if phone is not None:
        customer.phone = phone
    if billing_address is not None:
        customer.billing_address = billing_address

    session.flush()
    record_audit(
        session,
        entity_type="customer",
        entity_id=customer.id,
        action="customer_updated",
        actor_id=actor_id,
        before=before,
        after=_snapshot(customer),
    )
    session.commit()
    session.refresh(customer)
    return customer


def assert_no_open_invoices(session: Session, customer: Customer) -> None:
    open_invoice = session.execute(
        select(Invoice).where(Invoice.customer_id == customer.id, Invoice.status.in_(OPEN_STATUSES))
    ).first()
    if open_invoice is not None:
        raise CustomerHasOpenInvoicesError(
            "Customer has at least one invoice not in Paid or Cancelled status; "
            "hard delete is blocked, converting to soft delete."
        )


def delete_customer(session: Session, customer_id: uuid.UUID, *, actor_id: uuid.UUID) -> Customer:
    """Always resolves to soft-delete per business rule — hard delete is
    never permitted while the customer has any open invoice, and even when
    it would be technically possible, v1 only ever performs soft-delete."""
    customer = get_customer(session, customer_id)
    before = _snapshot(customer)

    # Business rule check retained for auditability/clarity even though the
    # outcome (soft-delete) is the same either way in v1's API surface.
    try:
        assert_no_open_invoices(session, customer)
    except CustomerHasOpenInvoicesError:
        pass

    customer.is_active = False
    session.flush()
    record_audit(
        session,
        entity_type="customer",
        entity_id=customer.id,
        action="customer_soft_deleted",
        actor_id=actor_id,
        before=before,
        after=_snapshot(customer),
    )
    session.commit()
    session.refresh(customer)
    return customer


def _snapshot(customer: Customer) -> dict:
    return {
        "id": str(customer.id),
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
        "billing_address": customer.billing_address,
        "is_active": customer.is_active,
    }
