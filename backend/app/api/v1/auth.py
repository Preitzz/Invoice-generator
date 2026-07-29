from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.user import LoginRequest, LoginResponse, UserRead
from app.services.auth import authenticate

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user, token = authenticate(db, email=payload.email, password=payload.password)
    return LoginResponse(access_token=token, user=UserRead.model_validate(user))


@router.post("/logout")
def logout(user: User = Depends(get_current_user)) -> dict:
    # Stateless signed tokens — "logout" is a client-side discard of the
    # bearer token. No server-side session store to invalidate in v1.
    return {"status": "logged_out"}
