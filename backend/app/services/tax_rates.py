import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.tax_rate import TaxRate
from app.services.audit import record_audit


def get_active_tax_rate(session: Session) -> TaxRate:
    """Fetches the single "current global rate" row — the one with
    is_active=True and effective_to IS NULL. Enforced as a service-layer
    invariant (documented, not a DB constraint) via SELECT ... FOR UPDATE
    when flipping which row is active.
    """
    rate = session.execute(
        select(TaxRate)
        .where(TaxRate.is_active.is_(True), TaxRate.effective_to.is_(None))
        .order_by(TaxRate.effective_from.desc())
        .limit(1)
    ).scalar_one_or_none()
    if rate is None:
        raise NotFoundError("No active tax rate configured")
    return rate


def list_tax_rates(session: Session) -> list[TaxRate]:
    return list(session.execute(select(TaxRate).order_by(TaxRate.effective_from.desc())).scalars())


def create_tax_rate(
    session: Session,
    *,
    name: str,
    rate_percent: Decimal,
    effective_from: date,
    actor_id: uuid.UUID,
) -> TaxRate:
    """Creating a new rate deactivates the prior active one, inside the same
    transaction, using SELECT ... FOR UPDATE to serialize concurrent flips."""
    existing_active = session.execute(
        select(TaxRate)
        .where(TaxRate.is_active.is_(True), TaxRate.effective_to.is_(None))
        .with_for_update()
    ).scalar_one_or_none()

    if existing_active is not None:
        before = _snapshot(existing_active)
        existing_active.is_active = False
        existing_active.effective_to = effective_from
        session.flush()
        record_audit(
            session,
            entity_type="tax_rate",
            entity_id=existing_active.id,
            action="tax_rate_deactivated",
            actor_id=actor_id,
            before=before,
            after=_snapshot(existing_active),
        )

    new_rate = TaxRate(
        name=name,
        rate_percent=rate_percent,
        effective_from=effective_from,
        effective_to=None,
        is_active=True,
    )
    session.add(new_rate)
    session.flush()
    record_audit(
        session,
        entity_type="tax_rate",
        entity_id=new_rate.id,
        action="tax_rate_created",
        actor_id=actor_id,
        before=None,
        after=_snapshot(new_rate),
    )
    session.commit()
    session.refresh(new_rate)
    return new_rate


def _snapshot(rate: TaxRate) -> dict:
    return {
        "id": str(rate.id),
        "name": rate.name,
        "rate_percent": str(rate.rate_percent),
        "effective_from": rate.effective_from.isoformat(),
        "effective_to": rate.effective_to.isoformat() if rate.effective_to else None,
        "is_active": rate.is_active,
    }
