import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient_request import Department, Status
from app.repositories import patient_request_repo
from app.schemas.inbox_item import InboxItemResponse
from app.schemas.patient_request import PaginatedResponse, PatientRequestDetail


async def list_requests(
    db: AsyncSession,
    department: Department | None = None,
    status: Status | None = None,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse:
    requests, total = await patient_request_repo.list_requests(
        db, department=department, status=status, page=page, page_size=page_size
    )
    return PaginatedResponse(
        items=[
            PatientRequestDetail(
                id=r.id,
                patient_id=r.patient_id,
                department=r.department,
                status=r.status,
                open_item_count=r.open_item_count,
                created_at=r.created_at,
                updated_at=r.updated_at,
                items=[InboxItemResponse.model_validate(item) for item in r.items],
            )
            for r in requests
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_request_detail(
    db: AsyncSession, request_id: uuid.UUID
) -> PatientRequestDetail | None:
    request = await patient_request_repo.get_by_id(db, request_id)
    if request is None:
        return None

    open_count = sum(1 for item in request.items if item.status == Status.OPEN)

    return PatientRequestDetail(
        id=request.id,
        patient_id=request.patient_id,
        department=request.department,
        status=request.status,
        open_item_count=open_count,
        created_at=request.created_at,
        updated_at=request.updated_at,
        items=[InboxItemResponse.model_validate(item) for item in request.items],
    )
