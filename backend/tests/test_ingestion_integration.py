import pytest
from unittest.mock import patch, AsyncMock
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inbox_item import InboxItem
from app.models.patient_request import Department, PatientRequest, Status
from app.schemas.inbox_item import InboxItemIngest
from app.services.ingestion_service import process_batch

pytestmark = pytest.mark.integration


def _make_item(**overrides) -> InboxItemIngest:
    defaults = {
        "external_id": "ext-1",
        "patient_id": "patient-1",
        "message_text": "I need help",
        "medications": ["Ibuprofen"],
        "department": Department.DERMATOLOGY,
        "status": Status.OPEN,
    }
    defaults.update(overrides)
    return InboxItemIngest(**defaults)


@pytest.mark.asyncio
@patch("app.services.ingestion_service.sse_manager", new_callable=lambda: type("M", (), {"broadcast": AsyncMock()}))
async def test_new_items_create_request(mock_sse, db: AsyncSession):
    items = [
        _make_item(external_id="ext-1"),
        _make_item(external_id="ext-2", message_text="Second message"),
    ]
    result = await process_batch(db, items)

    assert result.created == 2
    assert result.updated == 0

    requests = (await db.execute(select(PatientRequest))).scalars().all()
    assert len(requests) == 1
    assert requests[0].status == Status.OPEN

    db_items = (await db.execute(select(InboxItem))).scalars().all()
    assert len(db_items) == 2
    assert all(item.request_id == requests[0].id for item in db_items)


@pytest.mark.asyncio
@patch("app.services.ingestion_service.sse_manager", new_callable=lambda: type("M", (), {"broadcast": AsyncMock()}))
async def test_attach_to_existing_open_request(mock_sse, db: AsyncSession):
    await process_batch(db, [_make_item(external_id="ext-1")])

    result = await process_batch(db, [_make_item(external_id="ext-2")])
    assert result.created == 1

    requests = (await db.execute(select(PatientRequest))).scalars().all()
    assert len(requests) == 1


@pytest.mark.asyncio
@patch("app.services.ingestion_service.sse_manager", new_callable=lambda: type("M", (), {"broadcast": AsyncMock()}))
async def test_different_departments_create_separate_requests(mock_sse, db: AsyncSession):
    items = [
        _make_item(external_id="ext-1", department=Department.DERMATOLOGY),
        _make_item(external_id="ext-2", department=Department.RADIOLOGY),
    ]
    await process_batch(db, items)

    requests = (await db.execute(select(PatientRequest))).scalars().all()
    assert len(requests) == 2
    departments = {r.department for r in requests}
    assert departments == {Department.DERMATOLOGY, Department.RADIOLOGY}


@pytest.mark.asyncio
@patch("app.services.ingestion_service.sse_manager", new_callable=lambda: type("M", (), {"broadcast": AsyncMock()}))
async def test_update_item_content(mock_sse, db: AsyncSession):
    await process_batch(db, [_make_item(external_id="ext-1", message_text="Original")])
    result = await process_batch(db, [_make_item(external_id="ext-1", message_text="Updated")])

    assert result.updated == 1
    assert result.created == 0

    item = (await db.execute(select(InboxItem))).scalar_one()
    assert item.message_text == "Updated"


@pytest.mark.asyncio
@patch("app.services.ingestion_service.sse_manager", new_callable=lambda: type("M", (), {"broadcast": AsyncMock()}))
async def test_close_item_clears_content(mock_sse, db: AsyncSession):
    await process_batch(db, [_make_item(external_id="ext-1", message_text="Hello", medications=["Aspirin"])])
    await process_batch(db, [_make_item(external_id="ext-1", status=Status.CLOSED)])

    item = (await db.execute(select(InboxItem))).scalar_one()
    assert item.status == Status.CLOSED
    assert item.message_text is None
    assert item.medications is None
    assert item.closed_at is not None


@pytest.mark.asyncio
@patch("app.services.ingestion_service.sse_manager", new_callable=lambda: type("M", (), {"broadcast": AsyncMock()}))
async def test_close_all_items_closes_request(mock_sse, db: AsyncSession):
    await process_batch(db, [
        _make_item(external_id="ext-1"),
        _make_item(external_id="ext-2"),
    ])

    await process_batch(db, [
        _make_item(external_id="ext-1", status=Status.CLOSED),
        _make_item(external_id="ext-2", status=Status.CLOSED),
    ])

    request = (await db.execute(select(PatientRequest))).scalar_one()
    assert request.status == Status.CLOSED


@pytest.mark.asyncio
@patch("app.services.ingestion_service.sse_manager", new_callable=lambda: type("M", (), {"broadcast": AsyncMock()}))
async def test_close_subset_keeps_request_open(mock_sse, db: AsyncSession):
    await process_batch(db, [
        _make_item(external_id="ext-1"),
        _make_item(external_id="ext-2"),
    ])

    await process_batch(db, [_make_item(external_id="ext-1", status=Status.CLOSED)])

    request = (await db.execute(select(PatientRequest))).scalar_one()
    assert request.status == Status.OPEN


@pytest.mark.asyncio
@patch("app.services.ingestion_service.sse_manager", new_callable=lambda: type("M", (), {"broadcast": AsyncMock()}))
async def test_department_reassignment(mock_sse, db: AsyncSession):
    await process_batch(db, [_make_item(external_id="ext-1", department=Department.DERMATOLOGY)])

    await process_batch(db, [_make_item(external_id="ext-1", department=Department.RADIOLOGY)])

    item = (await db.execute(select(InboxItem))).scalar_one()
    assert item.department == Department.RADIOLOGY

    requests = (await db.execute(select(PatientRequest))).scalars().all()
    derm_req = [r for r in requests if r.department == Department.DERMATOLOGY]
    rad_req = [r for r in requests if r.department == Department.RADIOLOGY]
    assert len(derm_req) == 1
    assert derm_req[0].status == Status.CLOSED
    assert len(rad_req) == 1
    assert rad_req[0].status == Status.OPEN


@pytest.mark.asyncio
@patch("app.services.ingestion_service.sse_manager", new_callable=lambda: type("M", (), {"broadcast": AsyncMock()}))
async def test_batch_idempotency(mock_sse, db: AsyncSession):
    batch = [_make_item(external_id="ext-1")]
    await process_batch(db, batch)
    await process_batch(db, batch)

    items = (await db.execute(select(InboxItem))).scalars().all()
    assert len(items) == 1


@pytest.mark.asyncio
@patch("app.services.ingestion_service.sse_manager", new_callable=lambda: type("M", (), {"broadcast": AsyncMock()}))
async def test_closed_request_preserved_new_request_created(mock_sse, db: AsyncSession):
    await process_batch(db, [_make_item(external_id="ext-1")])
    await process_batch(db, [_make_item(external_id="ext-1", status=Status.CLOSED)])

    await process_batch(db, [_make_item(external_id="ext-2", message_text="New issue")])

    requests = (await db.execute(select(PatientRequest))).scalars().all()
    assert len(requests) == 2
    statuses = {r.status for r in requests}
    assert statuses == {Status.OPEN, Status.CLOSED}
