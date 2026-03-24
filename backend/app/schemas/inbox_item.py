from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.patient_request import Department, Status


class InboxItemIngest(BaseModel):
    external_id: str
    patient_id: str
    message_text: str | None = None
    medications: list[str] | None = None
    department: Department
    status: Status


class BatchIngestRequest(BaseModel):
    items: list[InboxItemIngest]


class DeclinedItem(BaseModel):
    external_id: str
    reason: str


class BatchIngestResponse(BaseModel):
    created: int
    updated: int
    closed: int
    declined: list[DeclinedItem] = []


class InboxItemResponse(BaseModel):
    id: UUID
    external_id: str
    patient_id: str
    message_text: str | None
    medications: list[str] | None
    department: Department
    status: Status
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None

    model_config = {"from_attributes": True}
