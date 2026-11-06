from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header
from sqlalchemy import select

from app.core.dependencies import DB, Admin, CurrentUser
from app.core.idempotency import begin_operation
from app.core.pagination import paginate
from app.core.schemas import Page
from app.modules.events.service import require_event
from app.modules.finance import service
from app.modules.finance.models import BudgetLine, Expense
from app.modules.finance.schemas import (
    BudgetInput,
    BudgetOut,
    ExpenseInput,
    ExpenseOut,
    FinanceSummary,
    ReviewInput,
    SettlementOut,
)

router = APIRouter(prefix="/events/{event_id}", tags=["Finance"])
IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)]


@router.post("/budget-lines", response_model=BudgetOut, status_code=201)
async def add_budget(
    event_id: UUID, data: BudgetInput, db: DB, user: CurrentUser, key: IdempotencyKey
):
    await require_event(db, user, event_id, manage=True)
    op, replay = await begin_operation(
        db, user.id, f"budget:{event_id}", key, data.model_dump(mode="json")
    )
    if not replay:
        result = await service.add_budget(db, user, event_id, data)
        op.response = BudgetOut.model_validate(result).model_dump(mode="json")
    return op.response


@router.get("/budget-lines", response_model=Page[BudgetOut])
async def list_budget(
    event_id: UUID, db: DB, user: CurrentUser, page: int = 1, page_size: int = 20
):
    await require_event(db, user, event_id, manage=True)
    return await paginate(
        db,
        select(BudgetLine)
        .where(BudgetLine.event_id == event_id)
        .order_by(
            BudgetLine.created_at,
            BudgetLine.id,
        ),
        BudgetOut,
        page,
        page_size,
    )


@router.post("/expenses", response_model=ExpenseOut, status_code=201)
async def add_expense(
    event_id: UUID, data: ExpenseInput, db: DB, user: CurrentUser, key: IdempotencyKey
):
    await require_event(db, user, event_id)
    op, replay = await begin_operation(
        db, user.id, f"expense:{event_id}", key, data.model_dump(mode="json")
    )
    if not replay:
        result = await service.add_expense(db, user, event_id, data)
        op.response = ExpenseOut.model_validate(result).model_dump(mode="json")
    return op.response


@router.get("/expenses", response_model=Page[ExpenseOut])
async def list_expenses(
    event_id: UUID, db: DB, user: CurrentUser, page: int = 1, page_size: int = 20
):
    await require_event(db, user, event_id)
    query = select(Expense).where(Expense.event_id == event_id)
    if user.role == "employee":
        query = query.where(Expense.submitted_by == user.id)
    return await paginate(
        db, query.order_by(Expense.created_at, Expense.id), ExpenseOut, page, page_size
    )


@router.patch("/expenses/{expense_id}", response_model=ExpenseOut)
async def review(event_id: UUID, expense_id: UUID, data: ReviewInput, db: DB, admin: Admin):
    return await service.review_expense(db, admin, event_id, expense_id, data.status)


@router.get("/settlements/summary", response_model=FinanceSummary)
async def summary(event_id: UUID, db: DB, user: CurrentUser):
    return await service.summary(db, user, event_id)


@router.post("/settlements", response_model=SettlementOut, status_code=201)
async def finalize(event_id: UUID, db: DB, admin: Admin, key: IdempotencyKey):
    await require_event(db, admin, event_id, manage=True)
    op, replay = await begin_operation(db, admin.id, f"settlement:{event_id}", key, {})
    if not replay:
        result = await service.finalize(db, admin, event_id)
        op.response = SettlementOut.model_validate(result).model_dump(mode="json")
    return op.response
