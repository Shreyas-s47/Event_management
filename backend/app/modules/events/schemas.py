from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    model_validator,
)


def decimal_string(value):
    if not isinstance(value, (str, Decimal)):
        raise ValueError("Money must be a decimal string, for example '1000.00'")
    return value


Money = Annotated[
    Decimal,
    BeforeValidator(decimal_string),
    Field(ge=0, max_digits=14, decimal_places=2, allow_inf_nan=False),
]
EventStatus = Literal["draft", "submitted", "approved", "in_progress", "completed", "cancelled"]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EventInput(InputModel):
    title: str = Field(min_length=1, max_length=200, pattern=r"\S")
    event_type: str = Field(min_length=1, max_length=80, pattern=r"\S")
    requirements: str = Field(default="", max_length=20000)
    venue: str = Field(min_length=1, max_length=300, pattern=r"\S")
    # Object key and alt text only; upload authorization belongs to Member 6.
    venue_map: dict[str, str] = Field(default_factory=dict, max_length=10)
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    total_budget: Money
    currency: Literal["INR", "USD", "EUR", "GBP"] = "INR"

    @model_validator(mode="after")
    def valid_dates(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class EventOut(EventInput):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    client_id: UUID
    status: EventStatus
    created_at: AwareDatetime


class StatusInput(InputModel):
    status: EventStatus


class MemberInput(InputModel):
    user_id: UUID


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    event_id: UUID
    user_id: UUID


class AgendaInput(InputModel):
    title: str = Field(min_length=1, max_length=200, pattern=r"\S")
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    location: str = Field(default="", max_length=300)

    @model_validator(mode="after")
    def valid_dates(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class AgendaOut(AgendaInput):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    event_id: UUID
