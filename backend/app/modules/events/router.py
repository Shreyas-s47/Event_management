from uuid import UUID

from fastapi import APIRouter, Response
from sqlalchemy import exists, select

from app.core.dependencies import DB, Admin, CurrentUser
from app.core.errors import DomainError
from app.core.pagination import paginate
from app.core.schemas import Page
from app.modules.events import service
from app.modules.events.models import AgendaItem, Event, EventMembership
from app.modules.events.schemas import (
    AgendaInput,
    AgendaOut,
    EventInput,
    EventOut,
    MemberInput,
    MemberOut,
    StatusInput,
)

router = APIRouter(prefix="/events", tags=["Events"])


@router.post("", response_model=EventOut, status_code=201)
async def create(data: EventInput, db: DB, user: CurrentUser):
    return await service.create_event(db, user, data)


@router.get("", response_model=Page[EventOut])
async def list_events(db: DB, user: CurrentUser, page: int = 1, page_size: int = 20):
    query = select(Event).order_by(Event.starts_at, Event.id)
    if user.role == "client":
        query = query.where(Event.client_id == user.id)
    elif user.role == "employee":
        query = query.where(
            exists().where(
                EventMembership.event_id == Event.id,
                EventMembership.user_id == user.id,
            )
        )
    elif user.role != "admin":
        query = query.where(False)
    return await paginate(db, query, EventOut, page, page_size)


@router.get("/{event_id}", response_model=EventOut)
async def get_event(event_id: UUID, db: DB, user: CurrentUser):
    return await service.require_event(db, user, event_id)


@router.put("/{event_id}", response_model=EventOut)
async def replace(event_id: UUID, data: EventInput, db: DB, user: CurrentUser):
    return await service.replace_event(db, user, event_id, data)


@router.patch("/{event_id}/status", response_model=EventOut)
async def status(event_id: UUID, data: StatusInput, db: DB, user: CurrentUser):
    return await service.transition(db, user, event_id, data.status)


@router.post("/{event_id}/members", response_model=MemberOut, status_code=201)
async def add_member(event_id: UUID, data: MemberInput, db: DB, admin: Admin):
    return await service.add_member(db, admin, event_id, data.user_id)


@router.get("/{event_id}/members", response_model=Page[MemberOut])
async def list_members(
    event_id: UUID, db: DB, user: CurrentUser, page: int = 1, page_size: int = 20
):
    await service.require_event(db, user, event_id, manage=True)
    return await paginate(
        db,
        select(EventMembership)
        .where(
            EventMembership.event_id == event_id,
        )
        .order_by(EventMembership.created_at, EventMembership.id),
        MemberOut,
        page,
        page_size,
    )


@router.delete("/{event_id}/members/{user_id}", status_code=204)
async def remove_member(event_id: UUID, user_id: UUID, db: DB, admin: Admin):
    event = await service.require_event(db, admin, event_id, lock=True)
    service.editable(event)
    member = await db.scalar(
        select(EventMembership).where(
            EventMembership.event_id == event_id,
            EventMembership.user_id == user_id,
        )
    )
    if member is None:
        raise DomainError(404, "not_found", "Membership not found")
    await db.delete(member)
    service.audit(db, admin, event_id, "event.member_removed", user_id=str(user_id))
    return Response(status_code=204)


@router.post("/{event_id}/agenda", response_model=AgendaOut, status_code=201)
async def add_agenda(event_id: UUID, data: AgendaInput, db: DB, user: CurrentUser):
    return await service.add_agenda(db, user, event_id, data)


@router.get("/{event_id}/agenda", response_model=Page[AgendaOut])
async def list_agenda(
    event_id: UUID, db: DB, user: CurrentUser, page: int = 1, page_size: int = 20
):
    await service.require_event(db, user, event_id)
    return await paginate(
        db,
        select(AgendaItem)
        .where(
            AgendaItem.event_id == event_id,
        )
        .order_by(AgendaItem.starts_at, AgendaItem.id),
        AgendaOut,
        page,
        page_size,
    )
