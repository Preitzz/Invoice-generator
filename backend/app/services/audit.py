"""Append-only audit log writer. The only way any code path may touch
audit_log — no update/delete helper exists anywhere in this module or model.
"""

import uuid

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLogEntry


def record_audit(
    session: Session,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    action: str,
    actor_id: uuid.UUID | None,
    before: dict | None = None,
    after: dict | None = None,
) -> AuditLogEntry:
    entry = AuditLogEntry(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor_id=actor_id,
        before_state=before,
        after_state=after,
    )
    session.add(entry)
    session.flush()
    return entry
