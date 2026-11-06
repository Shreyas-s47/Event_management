import hashlib
import json

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import conflict
from app.modules.finance.models import ProcessedOperation


async def begin_operation(db: AsyncSession, actor_id, scope: str, key: str, payload: dict):
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    # ON CONFLICT waits for a concurrent transaction, then reads its committed response.
    result = await db.execute(
        insert(ProcessedOperation)
        .values(
            actor_id=actor_id,
            scope=scope,
            key=key,
            request_hash=digest,
            response={},
        )
        .on_conflict_do_nothing(index_elements=["actor_id", "scope", "key"])
        .returning(
            ProcessedOperation.id,
        )
    )
    inserted = result.scalar_one_or_none()
    operation = await db.scalar(
        select(ProcessedOperation).where(
            ProcessedOperation.actor_id == actor_id,
            ProcessedOperation.scope == scope,
            ProcessedOperation.key == key,
        )
    )
    if operation.request_hash != digest:
        raise conflict("Idempotency key was used with a different request")
    return operation, inserted is None
