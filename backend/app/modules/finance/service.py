from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError, conflict
from app.modules.auth.models import User
from app.modules.events import service as events
from app.modules.finance.models import BudgetLine, Expense, Settlement
from app.modules.finance.schemas import BudgetInput, ExpenseInput


async def require_unsettled(db: AsyncSession, event_id: UUID):
    if await db.scalar(select(Settlement.id).where(Settlement.event_id == event_id)):
        raise conflict("Event finances are finalized")


async def add_budget(db: AsyncSession, user: User, event_id: UUID, data: BudgetInput):
    event = await events.require_event(db, user, event_id, manage=True, lock=True)
    events.editable(event)
    await require_unsettled(db, event_id)
    total = await db.scalar(
        select(func.coalesce(func.sum(BudgetLine.amount), 0)).where(
            BudgetLine.event_id == event_id,
        )
    )
    if total + data.amount > event.total_budget:
        raise conflict("Budget allocations exceed the event budget")
    line = BudgetLine(event_id=event_id, **data.model_dump())
    db.add(line)
    events.audit(db, user, event_id, "budget_line.created", amount=str(data.amount))
    await db.flush()
    return line


async def add_expense(db: AsyncSession, user: User, event_id: UUID, data: ExpenseInput):
    event = await events.require_event(db, user, event_id, lock=True)
    events.editable(event)
    await require_unsettled(db, event_id)
    expense = Expense(event_id=event_id, submitted_by=user.id, **data.model_dump())
    db.add(expense)
    events.audit(db, user, event_id, "expense.submitted", amount=str(data.amount))
    await db.flush()
    return expense


async def review_expense(
    db: AsyncSession, admin: User, event_id: UUID, expense_id: UUID, status: str
):
    await events.require_event(db, admin, event_id, lock=True)
    await require_unsettled(db, event_id)
    expense = await db.scalar(
        select(Expense)
        .where(
            Expense.id == expense_id,
            Expense.event_id == event_id,
        )
        .with_for_update()
    )
    if expense is None:
        raise DomainError(404, "not_found", "Expense not found")
    if expense.status != "pending":
        raise conflict("Expense has already been reviewed")
    if expense.submitted_by == admin.id:
        raise DomainError(403, "forbidden", "An expense requires a different reviewer")
    expense.status = status
    expense.reviewed_by = admin.id
    events.audit(db, admin, event_id, "expense.reviewed", expense_id=str(expense.id), status=status)
    await db.flush()
    return expense


async def summary(db: AsyncSession, user: User, event_id: UUID):
    event = await events.require_event(db, user, event_id, manage=True)
    rows = (
        await db.execute(
            select(Expense.status, func.sum(Expense.amount))
            .where(
                Expense.event_id == event_id,
            )
            .group_by(Expense.status)
        )
    ).all()
    amounts = {status: amount for status, amount in rows}
    allocated = await db.scalar(
        select(func.coalesce(func.sum(BudgetLine.amount), 0)).where(
            BudgetLine.event_id == event_id,
        )
    )
    approved = amounts.get("approved", Decimal("0.00"))
    return {
        "event_id": str(event_id),
        "currency": event.currency,
        "budget": format(event.total_budget, ".2f"),
        "allocated": format(allocated, ".2f"),
        "approved_expenses": format(approved, ".2f"),
        "pending_expenses": format(amounts.get("pending", Decimal(0)), ".2f"),
        "remaining_budget": format(event.total_budget - approved, ".2f"),
        "finalized": bool(
            await db.scalar(select(Settlement.id).where(Settlement.event_id == event_id))
        ),
    }


async def finalize(db: AsyncSession, admin: User, event_id: UUID):
    event = await events.require_event(db, admin, event_id, lock=True)
    if event.status != "completed":
        raise conflict("Complete the event before finalizing expenses")
    await require_unsettled(db, event_id)
    if await db.scalar(
        select(Expense.id)
        .where(
            Expense.event_id == event_id,
            Expense.status == "pending",
        )
        .limit(1)
    ):
        raise conflict("Review pending expenses first")
    totals = await summary(db, admin, event_id)
    settlement = Settlement(
        event_id=event_id,
        finalized_by=admin.id,
        budget=event.total_budget,
        approved_expenses=Decimal(totals["approved_expenses"]),
        currency=event.currency,
    )
    db.add(settlement)
    events.audit(db, admin, event_id, "settlement.finalized", totals=totals)
    await db.flush()
    return settlement
