import secrets
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.core.errors import DomainError, conflict
from app.core.security import DUMMY_HASH, access_token, hash_token, password_hasher
from app.db.models import utcnow
from app.modules.auth.models import AuthSession, RefreshToken, User
from app.modules.auth.schemas import RegisterInput, TokenOut, UserOut


async def create_user(db: AsyncSession, data: RegisterInput, role: str = "client") -> User:
    email = str(data.email).lower()
    if await db.scalar(select(User.id).where(User.email == email)):
        raise conflict("Email is already registered")
    user = User(
        email=email,
        full_name=data.full_name,
        password_hash=await run_in_threadpool(password_hasher.hash, data.password),
        role=role,
    )
    db.add(user)
    await db.flush()
    return user


async def authenticate(db: AsyncSession, email: str, password: str) -> User:
    user = await db.scalar(select(User).where(User.email == email.lower()))
    valid = await run_in_threadpool(
        password_hasher.verify, password, user.password_hash if user else DUMMY_HASH
    )
    if not user or not valid or not user.is_active:
        raise DomainError(401, "unauthorized", "Invalid email or password")
    return user


async def issue_tokens(db: AsyncSession, user: User, session: AuthSession | None = None):
    settings = get_settings()
    if session is None:
        session = AuthSession(
            user_id=user.id,
            expires_at=utcnow() + timedelta(days=settings.refresh_token_days),
        )
        db.add(session)
        await db.flush()
    raw = secrets.token_urlsafe(48)
    db.add(RefreshToken(session_id=session.id, token_hash=hash_token(raw)))
    await db.flush()
    return (
        TokenOut(
            access_token=access_token(user.id, session.id),
            expires_in=settings.access_token_minutes * 60,
            user=UserOut.model_validate(user),
        ),
        raw,
        session.expires_at,
    )


async def rotate_refresh(db: AsyncSession, raw: str):
    token = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw)))
    if token is None:
        raise DomainError(401, "unauthorized", "Invalid refresh token")
    # Lock the family, then re-read token state after acquiring the lock.
    session = await db.scalar(
        select(AuthSession).where(AuthSession.id == token.session_id).with_for_update()
    )
    await db.refresh(token)
    if token.used_at is not None:
        session.revoked_at = utcnow()
        await db.commit()  # Persist replay revocation even though the request fails.
        raise DomainError(401, "refresh_reused", "Refresh token reused; sign in again")
    if session.revoked_at or session.expires_at <= utcnow():
        raise DomainError(401, "unauthorized", "Session expired or revoked")
    user = await db.get(User, session.user_id)
    if not user.is_active:
        raise DomainError(401, "unauthorized", "Account is inactive")
    token.used_at = utcnow()
    return await issue_tokens(db, user, session)


async def revoke_refresh(db: AsyncSession, raw: str) -> None:
    token = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw)))
    if token:
        session = await db.scalar(
            select(AuthSession).where(AuthSession.id == token.session_id).with_for_update()
        )
        session.revoked_at = utcnow()
