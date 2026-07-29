"""Phase 7 gate: a raw SQL UPDATE/DELETE against audit_log, issued as the
application's runtime DB role, must be rejected by Postgres itself — not
merely by absence of an app-level UPDATE/DELETE code path.
"""

import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import ProgrammingError

from app.services.audit import record_audit


def test_app_role_cannot_update_audit_log(db_session, admin_user):
    entry = record_audit(
        db_session,
        entity_type="test_entity",
        entity_id=uuid.uuid4(),
        action="test_action",
        actor_id=admin_user.id,
        before=None,
        after={"x": 1},
    )
    db_session.commit()

    with pytest.raises(ProgrammingError) as excinfo:
        db_session.execute(
            sa.text("UPDATE audit_log SET action = 'tampered' WHERE id = :id"), {"id": entry.id}
        )
        db_session.commit()
    assert "permission denied" in str(excinfo.value).lower()
    db_session.rollback()


def test_app_role_cannot_delete_audit_log(db_session, admin_user):
    entry = record_audit(
        db_session,
        entity_type="test_entity",
        entity_id=uuid.uuid4(),
        action="test_action_2",
        actor_id=admin_user.id,
        before=None,
        after={"x": 2},
    )
    db_session.commit()

    with pytest.raises(ProgrammingError) as excinfo:
        db_session.execute(sa.text("DELETE FROM audit_log WHERE id = :id"), {"id": entry.id})
        db_session.commit()
    assert "permission denied" in str(excinfo.value).lower()
    db_session.rollback()


def test_app_role_can_still_insert_and_select_audit_log(db_session, admin_user):
    entry = record_audit(
        db_session,
        entity_type="test_entity",
        entity_id=uuid.uuid4(),
        action="test_action_3",
        actor_id=admin_user.id,
        before=None,
        after={"x": 3},
    )
    db_session.commit()

    fetched = db_session.execute(
        sa.text("SELECT action FROM audit_log WHERE id = :id"), {"id": entry.id}
    ).scalar_one()
    assert fetched == "test_action_3"


def test_no_service_layer_update_or_delete_helper_exists_for_audit_log():
    """Defense-in-depth check on the app-code side: services/audit.py only
    ever exposes record() (an INSERT), no update/delete function."""
    import app.services.audit as audit_module

    public_callables = [name for name in dir(audit_module) if not name.startswith("_")]
    forbidden_substrings = ("update", "delete", "edit", "modify")
    offending = [
        name
        for name in public_callables
        if callable(getattr(audit_module, name))
        and any(sub in name.lower() for sub in forbidden_substrings)
    ]
    assert offending == []
