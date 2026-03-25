from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.patient_request import Department, Status
from app.schemas.patient_request import PaginatedResponse
from app.services import request_service

router = APIRouter(tags=["Requests"])


@router.get("/requests", response_model=PaginatedResponse)
async def list_requests(
    department: Department | None = Query(None),
    status: Status | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List patient requests with optional department/status filters."""
    return await request_service.list_requests(
        db, department=department, status=status, page=page, page_size=page_size
    )
