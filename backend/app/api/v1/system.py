from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.permissions import require_admin
from app.models.user import User
from app.services import reminders as reminder_service

router = APIRouter(prefix="/system", tags=["system"])


class KillSwitchRequest(BaseModel):
    enabled: bool


class KillSwitchResponse(BaseModel):
    enabled: bool


@router.post("/reminders/kill-switch", response_model=KillSwitchResponse)
def set_kill_switch(
    payload: KillSwitchRequest, db: Session = Depends(get_db), user: User = Depends(require_admin)
) -> KillSwitchResponse:
    setting = reminder_service.set_kill_switch(db, enabled=payload.enabled, actor_id=user.id)
    return KillSwitchResponse(enabled=setting.value.get("enabled", False))
