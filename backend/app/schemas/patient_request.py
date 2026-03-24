from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.patient_request import Department, Status
from app.schemas.inbox_item import InboxItemResponse


class PatientRequestSummary(BaseModel):
    id: UUID
    patient_id: str
    department: Department
    status: Status
    open_item_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PatientRequestDetail(PatientRequestSummary):
    items: list[InboxItemResponse]


class PaginatedResponse(BaseModel):
    items: list[PatientRequestDetail]
    total: int
    page: int
    page_size: int
