import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.patient_request import Department, Status


class InboxItem(Base):
    __tablename__ = "inbox_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    external_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    patient_id: Mapped[str] = mapped_column(String(100), nullable=False)
    message_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    medications: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    department: Mapped[Department] = mapped_column(Enum(Department, name="department_enum", values_callable=lambda e: [m.value for m in e]), nullable=False)
    status: Mapped[Status] = mapped_column(Enum(Status, name="status_enum", values_callable=lambda e: [m.value for m in e]), nullable=False, default=Status.OPEN)
    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patient_requests.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    request = relationship("PatientRequest", back_populates="items")

    __table_args__ = (
        Index("idx_items_request_id", "request_id"),
        Index("idx_items_patient_dept", "patient_id", "department"),
    )
