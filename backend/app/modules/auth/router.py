from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select

from app.core.config import get_settings
from app.core.dependencies import DB, Admin, CurrentUser, require_cookie_origin
from app.core.errors import DomainError
from app.core.pagination import paginate
from app.core.schemas import Page
from app.modules.auth import service
from app.modules.auth.models import User
from app.modules.auth.schemas import LoginInput, RegisterInput, TokenOut, UserCreate, UserOut
from app.modules.events.service import audit

router = APIRouter(tags=["Identity"])
cookie_path = "/api/v1/auth"


def set_refresh_cookie(response: Response, raw: str, expires) -> None:
    response.set_cookie(
        "refresh_token",
        raw,
        httponly=True,
        secure=get_settings().cookie_secure,
        samesite="strict",
        path=cookie_path,
        expires=expires,
    )
    response.headers["Cache-Control"] = "no-store"


@router.post("/auth/register", response_model=UserOut, status_code=201)
async def register(data: RegisterInput, db: DB):
    return await service.create_user(db, data)


@router.post("/auth/login", response_model=TokenOut, dependencies=[Depends(require_cookie_origin)])
async def login(data: LoginInput, response: Response, db: DB):
    user = await service.authenticate(db, str(data.email), data.password)
    result, raw, expires = await service.issue_tokens(db, user)
    set_refresh_cookie(response, raw, expires)
    return result


@router.post(
    "/auth/refresh", response_model=TokenOut, dependencies=[Depends(require_cookie_origin)]
)
async def refresh(request: Request, response: Response, db: DB):
    raw = request.cookies.get("refresh_token")
    if not raw:
        raise DomainError(401, "unauthorized", "Refresh cookie required")
    result, new_raw, expires = await service.rotate_refresh(db, raw)
    set_refresh_cookie(response, new_raw, expires)
    return result


@router.post("/auth/logout", status_code=204, dependencies=[Depends(require_cookie_origin)])
async def logout(request: Request, db: DB):
    if raw := request.cookies.get("refresh_token"):
        await service.revoke_refresh(db, raw)
    response = Response(status_code=204)
    response.delete_cookie(
        "refresh_token",
        path=cookie_path,
        secure=get_settings().cookie_secure,
        httponly=True,
        samesite="strict",
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/auth/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user


@router.post("/users", response_model=UserOut, status_code=201)
async def provision_user(data: UserCreate, db: DB, admin: Admin):
    user = await service.create_user(db, data, data.role)
    audit(db, admin, None, "user.provisioned", user_id=str(user.id), role=user.role)
    return user


@router.get("/users", response_model=Page[UserOut])
async def users(db: DB, admin: Admin, page: int = 1, page_size: int = 20):
    return await paginate(
        db, select(User).order_by(User.created_at, User.id), UserOut, page, page_size
    )
