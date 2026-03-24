import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Department(str, enum.Enum):
    DERMATOLOGY = "Dermatology"
    RADIOLOGY = "Radiology"
    PRIMARY = "Primary"


class Status(str, enum.Enum):
    OPEN = "Open"
    CLOSED = "Closed"


class PatientRequest(Base):
    __tablename__ = "patient_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[str] = mapped_column(String(100), nullable=False)
    department: Mapped[Department] = mapped_column(Enum(Department, name="department_enum", values_callable=lambda e: [m.value for m in e]), nullable=False)
    status: Mapped[Status] = mapped_column(Enum(Status, name="status_enum", values_callable=lambda e: [m.value for m in e]), nullable=False, default=Status.OPEN)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    items = relationship("InboxItem", back_populates="request", lazy="selectin")

    __table_args__ = (
        Index("idx_requests_department_status", "department", "status"),
        Index("idx_requests_patient", "patient_id"),
        Index(
            "uq_open_request_per_patient_dept",
            "patient_id",
            "department",
            unique=True,
            postgresql_where=(status == Status.OPEN),
        ),
    )
