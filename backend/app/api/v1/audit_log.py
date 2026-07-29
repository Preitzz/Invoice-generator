import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.permissions import require_admin
from app.models.audit_log import AuditLogEntry
from app.models.user import User
from app.schemas.audit import AuditLogEntryRead

router = APIRouter(prefix="/audit-log", tags=["audit-log"])


@router.get("", response_model=list[AuditLogEntryRead])
def list_audit_log(
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[AuditLogEntryRead]:
    stmt = select(AuditLogEntry)
    if entity_type is not None:
        stmt = stmt.where(AuditLogEntry.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(AuditLogEntry.entity_id == entity_id)
    stmt = stmt.order_by(AuditLogEntry.timestamp.desc())
    return [AuditLogEntryRead.model_validate(e) for e in db.execute(stmt).scalars()]
