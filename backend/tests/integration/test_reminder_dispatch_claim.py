"""Exactly-once dispatch claim under real concurrency.

This test deliberately bypasses the `db_session` SAVEPOINT-per-test fixture:
concurrent-claim correctness only exercises real guarantees when two
genuinely separate DB connections race against committed rows, so this test
commits directly via app.db.session.SessionLocal and cleans up afterward.
"""

import threading
import uuid
from datetime import date, timedelta

from app.db.session import SessionLocal
from app.models.reminder_instance import ReminderInstanceStatus
from app.services import invoices as invoice_service
from app.services import reminders as reminder_service
from app.services.audit import record_audit
from tests.factories import make_line_item


def _setup_issued_invoice_with_admin_and_customer():
    session = SessionLocal()
    from app.core.security import hash_password
    from app.models.customer import Customer
    from app.models.tax_rate import TaxRate
    from app.models.user import User, UserRole
    from decimal import Decimal
    from sqlalchemy import select

    tax_rate = session.execute(
        select(TaxRate).where(TaxRate.is_active.is_(True), TaxRate.effective_to.is_(None))
    ).scalar_one_or_none()
    if tax_rate is None:
        tax_rate = TaxRate(
            name="Standard Flat Rate", rate_percent=Decimal("18.00"), effective_from=date.today(), is_active=True
        )
        session.add(tax_rate)
        session.commit()

    admin = User(
        name="Concurrency Admin",
        email=f"concurrency-{uuid.uuid4().hex[:8]}@example.com",
        role=UserRole.admin,
        password_hash=hash_password("x"),
        is_active=True,
    )
    customer = Customer(name="Concurrency Co", email="c@example.com", billing_address="addr")
    session.add_all([admin, customer])
    session.commit()

    draft = invoice_service.create_draft_invoice(
        session,
        customer_id=customer.id,
        due_date=date.today() + timedelta(days=10),
        line_items=[make_line_item()],
        actor_id=admin.id,
    )
    issued = invoice_service.issue_invoice(session, draft.id, actor_id=admin.id)
    instance_id = issued.reminder_instances[0].id if False else None
    from app.models.reminder_instance import ReminderInstance

    instance = session.execute(
        select(ReminderInstance).where(ReminderInstance.invoice_id == issued.id).limit(1)
    ).scalar_one()
    instance_id = instance.id
    admin_id, customer_id, invoice_id = admin.id, customer.id, issued.id
    session.close()
    return instance_id, admin_id, customer_id, invoice_id


def _cleanup(admin_id, customer_id, invoice_id):
    import sqlalchemy as sa

    from app.config import settings

    # audit_log and payments rows can only be deleted by the DB owner/admin
    # role in this schema (the runtime app_user role has no DELETE grant on
    # either — see migrations 0007/0010), so cleanup connects as admin.
    admin_engine = sa.create_engine(settings.DATABASE_URL_SYNC_ADMIN, future=True)
    with admin_engine.begin() as conn:
        conn.execute(
            sa.text("DELETE FROM audit_log WHERE entity_id IN (:a, :b, :c) OR actor_id = :b"),
            {"a": invoice_id, "b": admin_id, "c": customer_id},
        )
        conn.execute(sa.text("DELETE FROM payments WHERE invoice_id = :inv"), {"inv": invoice_id})
        conn.execute(sa.text("DELETE FROM reminder_instances WHERE invoice_id = :inv"), {"inv": invoice_id})
        conn.execute(sa.text("DELETE FROM invoice_line_items WHERE invoice_id = :inv"), {"inv": invoice_id})
        conn.execute(sa.text("DELETE FROM invoices WHERE id = :inv"), {"inv": invoice_id})
        conn.execute(sa.text("DELETE FROM customers WHERE id = :cid"), {"cid": customer_id})
        conn.execute(sa.text("DELETE FROM users WHERE id = :uid"), {"uid": admin_id})
    admin_engine.dispose()


def test_concurrent_claim_attempts_only_one_succeeds():
    instance_id, admin_id, customer_id, invoice_id = _setup_issued_invoice_with_admin_and_customer()
    try:
        results = []
        barrier = threading.Barrier(2)

        def _attempt_claim():
            session = SessionLocal()
            try:
                barrier.wait(timeout=5)
                claimed = reminder_service.claim_reminder_instance(session, instance_id)
                results.append(claimed is not None)
            finally:
                session.close()

        t1 = threading.Thread(target=_attempt_claim)
        t2 = threading.Thread(target=_attempt_claim)
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        assert results.count(True) == 1, f"expected exactly one successful claim, got {results}"
        assert results.count(False) == 1

        verify_session = SessionLocal()
        from app.models.reminder_instance import ReminderInstance

        instance = verify_session.get(ReminderInstance, instance_id)
        assert instance.status == ReminderInstanceStatus.sending
        assert instance.attempt_count == 1
        verify_session.close()
    finally:
        _cleanup(admin_id, customer_id, invoice_id)


def test_payment_race_cancels_instead_of_double_claim():
    """When an invoice becomes Paid concurrently with dispatch, the claim
    still succeeds (claim is purely about the reminder_instances row), but
    send_single_reminder's invoice re-check inside the same transaction is
    what prevents an actual send — covered by test_reminder_retry_failure's
    sibling assertions in the unit layer (recompute_invoice_status_after_payment
    already cancels remaining `scheduled` instances synchronously, so by the
    time dispatch scans for candidates there is nothing left to claim)."""
    instance_id, admin_id, customer_id, invoice_id = _setup_issued_invoice_with_admin_and_customer()
    try:
        from datetime import date as date_
        from decimal import Decimal

        from app.models.payment import PaymentMethod
        from app.services import payments as payment_service

        session = SessionLocal()
        invoice = invoice_service.get_invoice(session, invoice_id)
        payment_service.record_payment(
            session,
            invoice_id,
            amount=Decimal(str(invoice.total_amount)),
            payment_date=date_.today(),
            method=PaymentMethod.cash,
            notes=None,
            recorded_by=admin_id,
        )
        session.close()

        verify_session = SessionLocal()
        claimed = reminder_service.claim_reminder_instance(verify_session, instance_id)
        verify_session.close()
        assert claimed is None  # already cancelled by the payment, nothing to claim
    finally:
        _cleanup(admin_id, customer_id, invoice_id)
