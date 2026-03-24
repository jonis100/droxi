import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.inbox_item import InboxItem
from app.models.patient_request import Department, PatientRequest, Status
from app.schemas.inbox_item import InboxItemIngest
from app.services.ingestion_service import process_batch


def _mock_db():
    """Create a mock AsyncSession with proper begin_nested support."""
    db = AsyncMock()

    @asynccontextmanager
    async def _begin_nested():
        yield

    db.begin_nested = _begin_nested
    db.add = MagicMock()  # sync method, avoids coroutine warnings
    return db


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


def _make_request(
    patient_id="patient-1",
    department=Department.DERMATOLOGY,
    status=Status.OPEN,
) -> PatientRequest:
    req = MagicMock(spec=PatientRequest)
    req.id = uuid.uuid4()
    req.patient_id = patient_id
    req.department = department
    req.status = status
    req.items = []
    return req


def _make_existing_item(
    external_id="ext-1",
    department=Department.DERMATOLOGY,
    status=Status.OPEN,
    request_id=None,
) -> InboxItem:
    item = MagicMock(spec=InboxItem)
    item.external_id = external_id
    item.department = department
    item.status = status
    item.request_id = request_id or uuid.uuid4()
    item.message_text = "Original"
    item.medications = ["Aspirin"]
    item.closed_at = None
    item.updated_at = None
    return item


@pytest.mark.asyncio
@patch("app.services.ingestion_service.sse_manager")
@patch("app.services.ingestion_service.inbox_item_repo")
@patch("app.services.ingestion_service.patient_request_repo")
async def test_new_item_creates_request_and_counts(mock_req_repo, mock_item_repo, mock_sse):
    db = _mock_db()
    request = _make_request()
    mock_req_repo.get_open_request = AsyncMock(return_value=None)
    mock_item_repo.get_by_external_id = AsyncMock(return_value=None)
    mock_item_repo.count_open_items_for_request = AsyncMock(return_value=1)
    mock_sse.broadcast = AsyncMock()

    with patch("app.services.ingestion_service.PatientRequest", return_value=request):
        result = await process_batch(db, [_make_item()])

    assert result.created == 1
    assert result.updated == 0
    assert result.closed == 0
    db.add.assert_called()
    mock_sse.broadcast.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.ingestion_service.sse_manager")
@patch("app.services.ingestion_service.inbox_item_repo")
@patch("app.services.ingestion_service.patient_request_repo")
async def test_existing_item_is_updated(mock_req_repo, mock_item_repo, mock_sse):
    db = AsyncMock()
    existing = _make_existing_item()

    mock_item_repo.get_by_external_id = AsyncMock(return_value=existing)
    mock_item_repo.count_open_items_for_request = AsyncMock(return_value=1)
    mock_sse.broadcast = AsyncMock()
    db.get = AsyncMock(return_value=None)

    result = await process_batch(db, [_make_item(message_text="Updated")])

    assert result.created == 0
    assert result.updated == 1
    assert existing.message_text == "Updated"


@pytest.mark.asyncio
@patch("app.services.ingestion_service.sse_manager")
@patch("app.services.ingestion_service.inbox_item_repo")
@patch("app.services.ingestion_service.patient_request_repo")
async def test_close_item_clears_content(mock_req_repo, mock_item_repo, mock_sse):
    db = AsyncMock()
    existing = _make_existing_item(status=Status.OPEN)

    mock_item_repo.get_by_external_id = AsyncMock(return_value=existing)
    mock_item_repo.count_open_items_for_request = AsyncMock(return_value=0)
    mock_sse.broadcast = AsyncMock()

    # _maybe_close_request will call db.get to load the request
    request = _make_request(status=Status.OPEN)
    db.get = AsyncMock(return_value=request)

    result = await process_batch(db, [_make_item(status=Status.CLOSED)])

    assert result.closed == 1
    assert existing.status == Status.CLOSED
    assert existing.message_text is None
    assert existing.medications is None
    assert existing.closed_at is not None


@pytest.mark.asyncio
@patch("app.services.ingestion_service.sse_manager")
@patch("app.services.ingestion_service.inbox_item_repo")
@patch("app.services.ingestion_service.patient_request_repo")
async def test_close_all_items_closes_request(mock_req_repo, mock_item_repo, mock_sse):
    db = AsyncMock()
    request = _make_request(status=Status.OPEN)
    request_id = request.id

    item1 = _make_existing_item(external_id="ext-1", request_id=request_id)
    item2 = _make_existing_item(external_id="ext-2", request_id=request_id)

    mock_item_repo.get_by_external_id = AsyncMock(side_effect=[item1, item2])
    mock_item_repo.count_open_items_for_request = AsyncMock(return_value=0)
    mock_sse.broadcast = AsyncMock()
    db.get = AsyncMock(return_value=request)

    await process_batch(db, [
        _make_item(external_id="ext-1", status=Status.CLOSED),
        _make_item(external_id="ext-2", status=Status.CLOSED),
    ])

    assert request.status == Status.CLOSED


@pytest.mark.asyncio
@patch("app.services.ingestion_service.sse_manager")
@patch("app.services.ingestion_service.inbox_item_repo")
@patch("app.services.ingestion_service.patient_request_repo")
async def test_close_subset_keeps_request_open(mock_req_repo, mock_item_repo, mock_sse):
    db = AsyncMock()
    request = _make_request(status=Status.OPEN)
    request_id = request.id

    existing = _make_existing_item(external_id="ext-1", request_id=request_id)

    mock_item_repo.get_by_external_id = AsyncMock(return_value=existing)
    # Still 1 open item remaining
    mock_item_repo.count_open_items_for_request = AsyncMock(return_value=1)
    mock_sse.broadcast = AsyncMock()
    db.get = AsyncMock(return_value=request)

    await process_batch(db, [_make_item(external_id="ext-1", status=Status.CLOSED)])

    # Request stays open because count_open > 0
    assert request.status == Status.OPEN


@pytest.mark.asyncio
@patch("app.services.ingestion_service.sse_manager")
@patch("app.services.ingestion_service.inbox_item_repo")
@patch("app.services.ingestion_service.patient_request_repo")
async def test_department_reassignment(mock_req_repo, mock_item_repo, mock_sse):
    db = _mock_db()
    old_request = _make_request(department=Department.DERMATOLOGY)
    new_request = _make_request(department=Department.RADIOLOGY)

    existing = _make_existing_item(
        department=Department.DERMATOLOGY,
        request_id=old_request.id,
    )

    mock_item_repo.get_by_external_id = AsyncMock(return_value=existing)
    mock_req_repo.get_open_request = AsyncMock(return_value=None)
    mock_item_repo.count_open_items_for_request = AsyncMock(return_value=0)
    mock_sse.broadcast = AsyncMock()
    db.get = AsyncMock(return_value=old_request)

    with patch("app.services.ingestion_service.PatientRequest", return_value=new_request):
        await process_batch(db, [_make_item(department=Department.RADIOLOGY)])

    assert existing.department == Department.RADIOLOGY
    assert existing.request_id == new_request.id


@pytest.mark.asyncio
@patch("app.services.ingestion_service.sse_manager")
@patch("app.services.ingestion_service.inbox_item_repo")
@patch("app.services.ingestion_service.patient_request_repo")
async def test_idempotent_update_no_create(mock_req_repo, mock_item_repo, mock_sse):
    db = AsyncMock()
    existing = _make_existing_item()

    mock_item_repo.get_by_external_id = AsyncMock(return_value=existing)
    mock_item_repo.count_open_items_for_request = AsyncMock(return_value=1)
    mock_sse.broadcast = AsyncMock()
    db.get = AsyncMock(return_value=None)

    result = await process_batch(db, [_make_item()])

    assert result.created == 0
    assert result.updated == 1


@pytest.mark.asyncio
@patch("app.services.ingestion_service.sse_manager")
@patch("app.services.ingestion_service.inbox_item_repo")
@patch("app.services.ingestion_service.patient_request_repo")
async def test_sse_broadcast_called_per_department(mock_req_repo, mock_item_repo, mock_sse):
    db = _mock_db()
    req1 = _make_request(department=Department.DERMATOLOGY)
    req2 = _make_request(department=Department.RADIOLOGY)

    mock_item_repo.get_by_external_id = AsyncMock(return_value=None)
    mock_item_repo.count_open_items_for_request = AsyncMock(return_value=1)
    mock_req_repo.get_open_request = AsyncMock(return_value=None)
    mock_sse.broadcast = AsyncMock()

    call_count = 0
    def make_request(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return req1 if call_count == 1 else req2

    with patch("app.services.ingestion_service.PatientRequest", side_effect=make_request):
        await process_batch(db, [
            _make_item(external_id="ext-1", department=Department.DERMATOLOGY),
            _make_item(external_id="ext-2", department=Department.RADIOLOGY),
        ])

    assert mock_sse.broadcast.call_count == 2


@pytest.mark.asyncio
@patch("app.services.ingestion_service.sse_manager")
@patch("app.services.ingestion_service.inbox_item_repo")
@patch("app.services.ingestion_service.patient_request_repo")
async def test_new_closed_item_has_no_content(mock_req_repo, mock_item_repo, mock_sse):
    db = _mock_db()
    request = _make_request()

    mock_item_repo.get_by_external_id = AsyncMock(return_value=None)
    mock_item_repo.count_open_items_for_request = AsyncMock(return_value=0)
    mock_req_repo.get_open_request = AsyncMock(return_value=None)
    mock_sse.broadcast = AsyncMock()
    db.get = AsyncMock(return_value=request)

    with patch("app.services.ingestion_service.InboxItem") as MockItem:
        instance = MagicMock()
        MockItem.return_value = instance
        await process_batch(db, [_make_item(status=Status.CLOSED, message_text="secret", medications=["Med"])])

    # InboxItem was constructed with message_text=None and medications=None for CLOSED status
    call_kwargs = MockItem.call_args
    assert call_kwargs.kwargs["message_text"] is None
    assert call_kwargs.kwargs["medications"] is None
