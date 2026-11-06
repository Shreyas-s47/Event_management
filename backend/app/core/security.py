import hashlib
from datetime import timedelta
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings
from app.core.errors import DomainError
from app.db.models import utcnow

password_hasher = PasswordHash.recommended()
# Equalize the expensive hash check for unknown accounts.
DUMMY_HASH = password_hasher.hash("not-a-real-account-password")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def access_token(user_id: UUID, session_id: UUID) -> str:
    settings = get_settings()
    now = utcnow()
    return jwt.encode(
        {
            "sub": str(user_id),
            "sid": str(session_id),
            "iat": now,
            "exp": now + timedelta(minutes=settings.access_token_minutes),
            "iss": "event-management",
            "aud": "event-api",
            "type": "access",
        },
        settings.jwt_secret,
        algorithm="HS256",
    )


def decode_access(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            get_settings().jwt_secret,
            algorithms=["HS256"],
            issuer="event-management",
            audience="event-api",
            options={"require": ["sub", "sid", "exp", "iat", "type"]},
        )
        UUID(payload["sub"])
        UUID(payload["sid"])
        if payload["type"] != "access":
            raise ValueError("Wrong token type")
        return payload
    except (jwt.InvalidTokenError, ValueError, TypeError, KeyError):
        raise DomainError(401, "unauthorized", "Invalid or expired access token") from None
