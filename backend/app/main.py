import json
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException

from app.core.config import get_settings
from app.core.dependencies import DB
from app.core.errors import DomainError
from app.core.schemas import ErrorOut
from app.db.models import load_models
from app.db.session import engine
from app.modules.auth.router import router as auth_router
from app.modules.events.router import router as events_router
from app.modules.finance.router import router as finance_router

load_models()
logger = logging.getLogger("event_api")
logging.basicConfig(level=logging.INFO, format="%(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(
    title="Event Management API",
    version="0.1.0",
    lifespan=lifespan,
    responses={code: {"model": ErrorOut} for code in (401, 403, 404, 409, 422, 500)},
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-CSRF-Protection"],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request.state.request_id = str(uuid.uuid4())
    started = time.monotonic()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Do not record URL/query strings, authorization headers, or request bodies.
    route = request.scope.get("route")
    logger.info(
        json.dumps(
            {
                "request_id": request.state.request_id,
                "method": request.method,
                "route": getattr(route, "path", "unmatched"),
                "status": response.status_code,
                "duration_ms": round((time.monotonic() - started) * 1000, 2),
            }
        )
    )
    return response


def error_response(request: Request, status: int, code: str, message: str, fields=None):
    response = JSONResponse(
        status_code=status,
        content={
            "error": {"code": code, "message": message, "field_errors": fields or []},
            "request_id": getattr(request.state, "request_id", None),
        },
    )
    if status == 401:
        response.headers["WWW-Authenticate"] = "Bearer"
    return response


@app.exception_handler(DomainError)
async def domain_error(request: Request, exc: DomainError):
    return error_response(request, exc.status, exc.code, exc.message, exc.fields)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    # Never echo rejected values (especially passwords/tokens) in error responses.
    fields = [{"field": ".".join(map(str, e["loc"])), "message": e["msg"]} for e in exc.errors()]
    return error_response(request, 422, "validation_error", "Request validation failed", fields)


@app.exception_handler(IntegrityError)
async def integrity_error(request: Request, exc: IntegrityError):
    return error_response(request, 409, "conflict", "Record conflicts with existing data")


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    return error_response(request, exc.status_code, "http_error", str(exc.detail))


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    # Do not log SQL parameters or secrets embedded in exception messages.
    logger.error(
        json.dumps(
            {
                "request_id": getattr(request.state, "request_id", None),
                "exception_type": type(exc).__name__,
                "message": "Unhandled server error",
            }
        )
    )
    response = error_response(request, 500, "internal_error", "An unexpected error occurred")
    response.headers["X-Request-ID"] = getattr(request.state, "request_id", "")
    return response


@app.get("/health/live", tags=["Health"])
async def live():
    return {"status": "ok"}


@app.get("/health/ready", tags=["Health"])
async def ready(db: DB):
    try:
        await db.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError):
        raise DomainError(503, "unavailable", "Database is unavailable") from None
    return {"status": "ready"}


for router in (auth_router, events_router, finance_router):
    app.include_router(router, prefix="/api/v1")
