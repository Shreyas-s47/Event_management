from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import DomainError
from app.core.security import decode_access
from app.db.models import utcnow
from app.db.session import get_db
from app.modules.auth.models import AuthSession, User

DB = Annotated[AsyncSession, Depends(get_db, scope="function")]
bearer = HTTPBearer(auto_error=False)


async def current_user(
    db: DB,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    if credentials is None:
        raise DomainError(401, "unauthorized", "Bearer token required")
    claims = decode_access(credentials.credentials)
    session = await db.get(AuthSession, UUID(claims["sid"]))
    if (
        session is None
        or session.user_id != UUID(claims["sub"])
        or session.revoked_at
        or session.expires_at <= utcnow()
    ):
        raise DomainError(401, "unauthorized", "Session expired or revoked")
    user = await db.get(User, session.user_id)
    if not user or not user.is_active:
        raise DomainError(401, "unauthorized", "Account is inactive")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role != "admin":
        raise DomainError(403, "forbidden", "Administrator access required")
    return user


Admin = Annotated[User, Depends(require_admin)]


def require_cookie_origin(request: Request) -> None:
    # A custom header prevents simple cross-site forms; Origin is mandatory, including for CLI.
    if (
        request.headers.get("origin") not in get_settings().cors_origins
        or request.headers.get("x-csrf-protection") != "1"
    ):
        raise DomainError(403, "csrf_rejected", "Allowed Origin and X-CSRF-Protection: 1 required")
