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

