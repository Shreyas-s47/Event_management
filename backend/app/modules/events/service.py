from uuid import UUID

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError, conflict
from app.modules.auth.models import User
from app.modules.events.models import AgendaItem, AuditLog, Event, EventMembership
from app.modules.events.schemas import AgendaInput, EventInput


def audit(db: AsyncSession, user: User, event_id: UUID | None, action: str, **details):
    db.add(AuditLog(actor_id=user.id, event_id=event_id, action=action, details=details))


async def require_event(
    db: AsyncSession,
    user: User,
    event_id: UUID,
    *,
    manage: bool = False,
    lock: bool = False,
) -> Event:
    query = select(Event).where(Event.id == event_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    event = await db.scalar(query)
    if event is None:
        raise DomainError(404, "not_found", "Event not found")
    owner = user.role == "client" and event.client_id == user.id
    member = await db.scalar(
        select(
            exists().where(
                EventMembership.event_id == event_id,
                EventMembership.user_id == user.id,
            )
        )
    )
    if user.role != "admin" and not owner and not (user.role == "employee" and member):
        raise DomainError(404, "not_found", "Event not found")
    if manage and user.role != "admin" and not owner:
        raise DomainError(403, "forbidden", "Event manager access required")
    return event


def editable(event: Event) -> None:
    if event.status in {"completed", "cancelled"}:
        raise conflict("Event is closed")


async def create_event(db: AsyncSession, user: User, data: EventInput) -> Event:
    if user.role != "client":
        raise DomainError(403, "forbidden", "Only clients create their events")
    event = Event(client_id=user.id, **data.model_dump())
    db.add(event)
    await db.flush()
    audit(db, user, event.id, "event.created")
    return event


async def replace_event(db: AsyncSession, user: User, event_id: UUID, data: EventInput):
    from app.modules.finance.models import BudgetLine, Expense

    event = await require_event(db, user, event_id, manage=True, lock=True)
    if event.status != "draft":
        raise conflict("Only draft events can be edited")
    allocated = await db.scalar(
        select(func.coalesce(func.sum(BudgetLine.amount), 0)).where(
            BudgetLine.event_id == event_id,
        )
    )
    if data.total_budget < allocated:
        raise conflict("Budget cannot be reduced below existing allocations")
    has_expenses = await db.scalar(select(Expense.id).where(Expense.event_id == event_id).limit(1))
    if data.currency != event.currency and (allocated or has_expenses):
        raise conflict("Currency cannot change after financial entries exist")
    outside_agenda = await db.scalar(
        select(AgendaItem.id)
        .where(
            AgendaItem.event_id == event_id,
            (AgendaItem.starts_at < data.starts_at) | (AgendaItem.ends_at > data.ends_at),
        )
        .limit(1)
    )
    if outside_agenda:
        raise conflict("Event dates must contain the existing agenda")
    for key, value in data.model_dump().items():
        setattr(event, key, value)
    audit(db, user, event.id, "event.updated")
    await db.flush()
    return event


async def transition(db: AsyncSession, user: User, event_id: UUID, target: str) -> Event:
    event = await require_event(db, user, event_id, manage=True, lock=True)
    transitions = {
        "draft": {"submitted", "cancelled"},
        "submitted": {"approved", "draft", "cancelled"},
        "approved": {"in_progress", "cancelled"},
        "in_progress": {"completed", "cancelled"},
        "completed": set(),
        "cancelled": set(),
    }
    if target not in transitions[event.status]:
        raise conflict(f"Cannot move event from {event.status} to {target}")
    if user.role != "admin" and (
        event.status != "draft" or target not in {"submitted", "cancelled"}
    ):
        raise DomainError(403, "forbidden", "Administrator must review this transition")
    previous = event.status
    event.status = target
    audit(db, user, event.id, "event.status_changed", previous=previous, status=target)
    await db.flush()
    return event


async def add_member(db: AsyncSession, admin: User, event_id: UUID, user_id: UUID):
    event = await require_event(db, admin, event_id, lock=True)
    editable(event)
    user = await db.get(User, user_id)
    if not user or not user.is_active or user.role != "employee":
        raise DomainError(422, "invalid_member", "Select an active employee")
    if await db.scalar(
        select(EventMembership.id).where(
            EventMembership.event_id == event_id,
            EventMembership.user_id == user_id,
        )
    ):
        raise conflict("Employee is already an event member")
    member = EventMembership(event_id=event_id, user_id=user_id)
    db.add(member)
    audit(db, admin, event_id, "event.member_added", user_id=str(user_id))
    await db.flush()
    return member


async def add_agenda(db: AsyncSession, user: User, event_id: UUID, data: AgendaInput):
    event = await require_event(db, user, event_id, manage=True, lock=True)
    editable(event)
    if data.starts_at < event.starts_at or data.ends_at > event.ends_at:
        raise DomainError(422, "invalid_agenda", "Agenda must fit within event dates")
    item = AgendaItem(event_id=event_id, **data.model_dump())
    db.add(item)
    audit(db, user, event_id, "agenda.created")
    await db.flush()
    return item
