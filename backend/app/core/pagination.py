from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError


async def paginate(db: AsyncSession, query, schema, page: int, page_size: int) -> dict:
    if page < 1 or not 1 <= page_size <= 100:
        raise DomainError(
            422, "validation_error", "page >= 1 and page_size between 1 and 100 required"
        )
    total = await db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    rows = (await db.scalars(query.offset((page - 1) * page_size).limit(page_size))).all()
    return {
        "items": [schema.model_validate(row).model_dump(mode="json") for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
