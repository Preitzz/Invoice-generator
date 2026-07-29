"""Idempotent dev-environment seed script.

Run with: python -m seed.seed_dev

Checks existing rows by natural key before inserting, so it is safe to run
repeatedly against the same (already-migrated) database.
"""

import sys
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.customer import Customer
from app.models.payment import PaymentMethod
from app.models.tax_rate import TaxRate
from app.models.user import User, UserRole
from app.services import invoices as invoice_service
from app.services import payments as payment_service

CUSTOMERS = [
    {
        "name": "Acme Retail Pvt Ltd",
        "email": "billing@acmeretail.example",
        "phone": "9820011122",
        "billing_address": "12 MG Road, Bengaluru, KA 560001",
    },
    {
        "name": "Bharat Textiles Co",
        "email": "accounts@bharattextiles.example",
        "phone": "9830022233",
        "billing_address": "45 Anna Salai, Chennai, TN 600002",
    },
    {
        "name": "Chandra Logistics",
        "email": "finance@chandralogistics.example",
        "phone": "9840033344",
        "billing_address": "7 Park Street, Kolkata, WB 700016",
    },
    {
        "name": "Delta Software Solutions",
        "email": "ap@deltasoftware.example",
        "phone": "9850044455",
        "billing_address": "88 Hitech City Rd, Hyderabad, TS 500081",
    },
    {
        "name": "Everest Traders",
        "email": "payables@everesttraders.example",
        "phone": "9860055566",
        "billing_address": "3 Connaught Place, New Delhi, DL 110001",
    },
]


def _ensure_user(session, *, name: str, email: str, role: UserRole, password: str) -> User:
    user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is not None:
        return user
    user = User(name=name, email=email, role=role, password_hash=hash_password(password), is_active=True)
    session.add(user)
    session.commit()
    session.refresh(user)
    print(f"  created user {email} ({role.value})")
    return user


def _ensure_active_tax_rate(session) -> TaxRate:
    rate = session.execute(
        select(TaxRate).where(TaxRate.is_active.is_(True), TaxRate.effective_to.is_(None))
    ).scalar_one_or_none()
    if rate is not None:
        return rate
    rate = TaxRate(name="Standard Flat Rate", rate_percent=Decimal("18.00"), effective_from=date.today(), is_active=True)
    session.add(rate)
    session.commit()
    session.refresh(rate)
    print("  created default active tax rate")
    return rate


def _ensure_customer(session, data: dict) -> Customer:
    customer = session.execute(select(Customer).where(Customer.email == data["email"])).scalar_one_or_none()
    if customer is not None:
        return customer
    customer = Customer(**data)
    session.add(customer)
    session.commit()
    session.refresh(customer)
    print(f"  created customer {data['name']}")
    return customer


def _line_items():
    return [
        {"description": "Consulting services", "quantity": "10", "unit_price": "1500.00"},
        {"description": "Software license", "quantity": "1", "unit_price": "25000.00"},
    ]


def seed() -> None:
    session = SessionLocal()
    try:
        print("Seeding users...")
        admin = _ensure_user(
            session, name="Admin User", email="admin@example.com", role=UserRole.admin, password=settings.SEED_ADMIN_PASSWORD
        )
        _ensure_user(
            session,
            name="Finance Staff",
            email="finance@example.com",
            role=UserRole.finance_staff,
            password=settings.SEED_ADMIN_PASSWORD,
        )
        _ensure_user(
            session, name="Viewer User", email="viewer@example.com", role=UserRole.viewer, password=settings.SEED_ADMIN_PASSWORD
        )

        print("Seeding tax rate...")
        _ensure_active_tax_rate(session)

        print("Seeding customers...")
        customers = [_ensure_customer(session, data) for data in CUSTOMERS]

        print("Seeding invoices...")
        existing_invoice_count = len(invoice_service.list_invoices(session))
        if existing_invoice_count >= 10:
            print(f"  {existing_invoice_count} invoices already exist — skipping invoice/payment seeding")
            return

        plans = [
            # (customer_index, due_offset_days, action)
            (0, 20, "draft"),
            (1, 25, "draft"),
            (2, -10, "issued_overdue"),
            (3, -20, "issued_overdue"),
            (4, 15, "issued_upcoming"),
            (0, -5, "issued_overdue"),
            (1, 10, "partially_paid"),
            (2, 30, "partially_paid"),
            (3, 5, "paid"),
            (4, 12, "cancelled"),
        ]

        for customer_idx, due_offset, action in plans:
            customer = customers[customer_idx]
            draft = invoice_service.create_draft_invoice(
                session,
                customer_id=customer.id,
                due_date=date.today() + timedelta(days=due_offset),
                line_items=_line_items(),
                actor_id=admin.id,
            )

            if action == "draft":
                continue

            issued = invoice_service.issue_invoice(session, draft.id, actor_id=admin.id)

            if action in ("issued_overdue", "issued_upcoming"):
                continue

            if action == "partially_paid":
                partial_amount = round(Decimal(str(issued.total_amount)) / 3, 2)
                payment_service.record_payment(
                    session,
                    issued.id,
                    amount=partial_amount,
                    payment_date=date.today(),
                    method=PaymentMethod.bank_transfer,
                    notes="Partial payment (seed data)",
                    recorded_by=admin.id,
                )
            elif action == "paid":
                payment_service.record_payment(
                    session,
                    issued.id,
                    amount=Decimal(str(issued.total_amount)),
                    payment_date=date.today(),
                    method=PaymentMethod.upi,
                    notes="Payment in full (seed data)",
                    recorded_by=admin.id,
                )
            elif action == "cancelled":
                invoice_service.cancel_invoice(session, issued.id, reason="Seed data cancellation example", actor_id=admin.id)

        print("Seed complete.")
    finally:
        session.close()


if __name__ == "__main__":
    try:
        seed()
    except Exception as exc:  # noqa: BLE001
        print(f"Seeding failed: {exc}", file=sys.stderr)
        raise
