from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError
from app.core.security import issue_token, verify_password
from app.models.user import User


def authenticate(session: Session, *, email: str, password: str) -> tuple[User, str]:
    user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
    # Reject without revealing whether the username exists: identical error
    # regardless of "no such user" vs "wrong password".
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise AuthenticationError("Invalid email or password")

    token = issue_token(user.id)
    return user, token
