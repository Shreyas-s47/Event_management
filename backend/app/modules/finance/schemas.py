from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.events.schemas import InputModel, Money


class BudgetInput(InputModel):
    title: str = Field(min_length=1, max_length=200, pattern=r"\S")
    amount: Money

    @model_validator(mode="after")
    def positive(self):
        if self.amount <= 0:
            raise ValueError("amount must be positive")
        return self


class BudgetOut(BudgetInput):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    event_id: UUID


class ExpenseInput(InputModel):
    description: str = Field(min_length=1, max_length=500, pattern=r"\S")
    amount: Money

    @model_validator(mode="after")
    def positive(self):
        if self.amount <= 0:
            raise ValueError("amount must be positive")
        return self


class ExpenseOut(ExpenseInput):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    event_id: UUID
    submitted_by: UUID
    reviewed_by: UUID | None
    status: Literal["pending", "approved", "rejected"]


class ReviewInput(InputModel):
    status: Literal["approved", "rejected"]


class SettlementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    event_id: UUID
    finalized_by: UUID
    approved_expenses: Decimal
    budget: Decimal
    currency: str


class FinanceSummary(BaseModel):
    event_id: UUID
    currency: str
    budget: str
    allocated: str
    approved_expenses: str
    pending_expenses: str
    remaining_budget: str
    finalized: bool
