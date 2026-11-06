import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Uuid
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class IdentityMixin:
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# Explicit imports keep Alembic aware of every registered module. Add new domains here.
def load_models() -> None:
    from app.modules.auth import models as auth_models  # noqa: F401
    from app.modules.events import models as event_models  # noqa: F401
    from app.modules.finance import models as finance_models  # noqa: F401
