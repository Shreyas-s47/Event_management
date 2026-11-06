import uuid
from decimal import Decimal

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import IdentityMixin
from app.db.session import Base


class BudgetLine(IdentityMixin, Base):
    __tablename__ = "budget_lines"
    __table_args__ = (CheckConstraint("amount > 0", name="positive_amount"),)
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))


class Expense(IdentityMixin, Base):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("amount > 0", name="positive_amount"),
        CheckConstraint("status IN ('pending','approved','rejected')", name="status"),
    )
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), index=True)
    submitted_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    description: Mapped[str] = mapped_column(String(500))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    status: Mapped[str] = mapped_column(String(20), default="pending")


class Settlement(IdentityMixin, Base):
    __tablename__ = "settlements"
    __table_args__ = (UniqueConstraint("event_id"),)
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"))
    finalized_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    approved_expenses: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    budget: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3))


class ProcessedOperation(IdentityMixin, Base):
    __tablename__ = "processed_operations"
    __table_args__ = (UniqueConstraint("actor_id", "scope", "key"),)
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    scope: Mapped[str] = mapped_column(String(200))
    key: Mapped[str] = mapped_column(String(128))
    request_hash: Mapped[str] = mapped_column(String(64))
    response: Mapped[dict] = mapped_column(JSON)
