from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError
from app.core.security import verify_token
from app.db.session import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise AuthenticationError("Not authenticated")

    user_id = verify_token(credentials.credentials)
    if user_id is None:
        raise AuthenticationError("Invalid or expired token")

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("Invalid or expired token")

    return user
