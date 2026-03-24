import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.inbox_item import InboxItem
from app.models.patient_request import Department, PatientRequest, Status


async def get_open_request(db: AsyncSession, patient_id: str, department: Department) -> PatientRequest | None:
    result = await db.execute(
        select(PatientRequest).where(
            PatientRequest.patient_id == patient_id,
            PatientRequest.department == department,
            PatientRequest.status == Status.OPEN,
        )
    )
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, request_id: uuid.UUID) -> PatientRequest | None:
    result = await db.execute(
        select(PatientRequest)
        .options(selectinload(PatientRequest.items))
        .where(PatientRequest.id == request_id)
    )
    return result.scalar_one_or_none()


async def list_requests(
    db: AsyncSession,
    department: Department | None = None,
    status: Status | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[PatientRequest], int]:
    query = select(PatientRequest).options(selectinload(PatientRequest.items))
    count_query = select(func.count()).select_from(PatientRequest)

    if department:
        query = query.where(PatientRequest.department == department)
        count_query = count_query.where(PatientRequest.department == department)
    if status:
        query = query.where(PatientRequest.status == status)
        count_query = count_query.where(PatientRequest.status == status)

    total = (await db.execute(count_query)).scalar_one()

    query = query.order_by(PatientRequest.updated_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    requests = list(result.unique().scalars().all())

    # Compute open_item_count from eagerly loaded items
    for req in requests:
        req.open_item_count = sum(1 for item in req.items if item.status == Status.OPEN)

    return requests, total
