"""Password hashing and session/token issuance+verification."""

import uuid
from datetime import datetime, timedelta

import bcrypt
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import settings

TOKEN_MAX_AGE_SECONDS = int(timedelta(hours=12).total_seconds())


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.SECRET_KEY, salt="invoice-reminder-session")


def issue_token(user_id: uuid.UUID) -> str:
    return _serializer().dumps({"user_id": str(user_id)})


def verify_token(token: str) -> uuid.UUID | None:
    try:
        data = _serializer().loads(token, max_age=TOKEN_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return None
    try:
        return uuid.UUID(data["user_id"])
    except (KeyError, ValueError, TypeError):
        return None
