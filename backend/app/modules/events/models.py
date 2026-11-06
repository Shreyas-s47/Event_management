import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import IdentityMixin
from app.db.session import Base


class Event(IdentityMixin, Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint("total_budget >= 0", name="positive_budget"),
        CheckConstraint("ends_at > starts_at", name="date_order"),
        CheckConstraint(
            "status IN ('draft','submitted','approved','in_progress','completed','cancelled')",
            name="status",
        ),
    )
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    event_type: Mapped[str] = mapped_column(String(80))
    requirements: Mapped[str] = mapped_column(Text, default="")
    venue: Mapped[str] = mapped_column(String(300))
    venue_map: Mapped[dict] = mapped_column(JSON, default=dict)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    total_budget: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3), default="INR")


class EventMembership(IdentityMixin, Base):
    __tablename__ = "event_memberships"
    __table_args__ = (UniqueConstraint("event_id", "user_id"),)
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)


class AgendaItem(IdentityMixin, Base):
    __tablename__ = "agenda_items"
    __table_args__ = (CheckConstraint("ends_at > starts_at", name="date_order"),)
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    location: Mapped[str] = mapped_column(String(300), default="")


class AuditLog(IdentityMixin, Base):
    __tablename__ = "audit_logs"
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    event_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("events.id"), index=True)
    action: Mapped[str] = mapped_column(String(120))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
