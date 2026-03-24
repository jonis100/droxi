import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inbox_item import InboxItem
from app.models.patient_request import Status


async def get_by_external_id(db: AsyncSession, external_id: str) -> InboxItem | None:
    result = await db.execute(select(InboxItem).where(InboxItem.external_id == external_id))
    return result.scalar_one_or_none()


async def get_items_for_request(db: AsyncSession, request_id: uuid.UUID) -> list[InboxItem]:
    result = await db.execute(select(InboxItem).where(InboxItem.request_id == request_id))
    return list(result.scalars().all())


async def count_open_items_for_request(db: AsyncSession, request_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(InboxItem)
        .where(InboxItem.request_id == request_id, InboxItem.status == Status.OPEN)
    )
    return result.scalar_one()
