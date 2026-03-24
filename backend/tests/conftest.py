import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import JSON, String, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.types import TypeDecorator

from app.database import Base, get_db
from app.models.inbox_item import InboxItem  # noqa: F401
from app.models.patient_request import Department, PatientRequest, Status  # noqa: F401


class StringEnum(TypeDecorator):
    """Stores enum values as strings (for SQLite) but coerces back to the enum on load."""

    impl = String(50)
    cache_ok = True

    def __init__(self, enum_class):
        super().__init__()
        self.enum_class = enum_class

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return value.value if isinstance(value, self.enum_class) else value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return self.enum_class(value)


# Override JSONB → JSON for SQLite compatibility
@event.listens_for(Base.metadata, "column_reflect")
def _setup_column(inspector, table, column_info):
    pass


# Create SQLite async engine for unit tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"



@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Store originals
    orig_medications_type = InboxItem.__table__.c.medications.type
    orig_dept_type_item = InboxItem.__table__.c.department.type
    orig_status_type_item = InboxItem.__table__.c.status.type
    orig_dept_type_req = PatientRequest.__table__.c.department.type
    orig_status_type_req = PatientRequest.__table__.c.status.type

    # Swap to SQLite-compatible types that preserve enum coercion
    InboxItem.__table__.c.medications.type = JSON()
    for col, enum_cls in [
        (InboxItem.__table__.c.department, Department),
        (InboxItem.__table__.c.status, Status),
        (PatientRequest.__table__.c.department, Department),
        (PatientRequest.__table__.c.status, Status),
    ]:
        col.type = StringEnum(enum_cls)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # The model defines a postgresql_where partial index which SQLite ignores,
        # creating a full unique constraint instead. Fix it: drop and recreate as
        # a proper SQLite partial unique index.
        await conn.exec_driver_sql("DROP INDEX IF EXISTS uq_open_request_per_patient_dept")
        await conn.exec_driver_sql(
            "CREATE UNIQUE INDEX uq_open_request_per_patient_dept "
            "ON patient_requests (patient_id, department) WHERE status = 'Open'"
        )

    yield engine

    # Restore original types
    InboxItem.__table__.c.medications.type = orig_medications_type
    InboxItem.__table__.c.department.type = orig_dept_type_item
    InboxItem.__table__.c.status.type = orig_status_type_item
    PatientRequest.__table__.c.department.type = orig_dept_type_req
    PatientRequest.__table__.c.status.type = orig_status_type_req

    await engine.dispose()


@pytest_asyncio.fixture
async def db(db_engine):
    async_session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_engine):
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async_session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with async_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
