from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.manager import sse_manager
from app.models.inbox_item import InboxItem
from app.models.patient_request import Department, PatientRequest, Status
from app.repositories import inbox_item_repo, patient_request_repo
from app.schemas.inbox_item import BatchIngestResponse, DeclinedItem, InboxItemIngest


async def _find_or_create_open_request(
    db: AsyncSession, patient_id: str, department: Department
) -> PatientRequest:
    request = await patient_request_repo.get_open_request(db, patient_id, department)
    if request is None:
        try:
            async with db.begin_nested():
                request = PatientRequest(
                    patient_id=patient_id,
                    department=department,
                    status=Status.OPEN,
                )
                db.add(request)
                await db.flush()
        except IntegrityError:
            request = await patient_request_repo.get_open_request(db, patient_id, department)
            if request is None:
                raise
    return request


async def _maybe_close_request(db: AsyncSession, request_id) -> None:
    open_count = await inbox_item_repo.count_open_items_for_request(db, request_id)
    if open_count == 0:
        request = await db.get(PatientRequest, request_id)
        if request and request.status == Status.OPEN:
            request.status = Status.CLOSED
            request.updated_at = datetime.now(timezone.utc)


async def process_batch(
    db: AsyncSession, items: list[InboxItemIngest]
) -> BatchIngestResponse:
    created = 0
    updated = 0
    closed = 0
    declined: list[DeclinedItem] = []
    affected_request_ids: set = set()
    affected_departments: set[str] = set()
    now = datetime.now(timezone.utc)

    for item_data in items:
        existing = await inbox_item_repo.get_by_external_id(db, item_data.external_id)

        if existing is None:
            request = await _find_or_create_open_request(
                db, item_data.patient_id, item_data.department
            )
            new_item = InboxItem(
                external_id=item_data.external_id,
                patient_id=item_data.patient_id,
                message_text=item_data.message_text,
                medications=item_data.medications,
                department=item_data.department,
                status=item_data.status,
                request_id=request.id,
                closed_at=now if item_data.status == Status.CLOSED else None,
            )
            db.add(new_item)
            affected_request_ids.add(request.id)
            affected_departments.add(item_data.department.value)
            created += 1
        else:
            # Patient ID mismatch
            if existing.patient_id != item_data.patient_id:
                declined.append(DeclinedItem(
                    external_id=item_data.external_id,
                    reason="patient_id cannot be changed for an existing item.",
                ))
                continue

            old_dept = existing.department
            old_request_id = existing.request_id

            # Department reassignment
            if old_dept != item_data.department:
                affected_request_ids.add(old_request_id)
                affected_departments.add(old_dept.value)
                new_request = await _find_or_create_open_request(
                    db, item_data.patient_id, item_data.department
                )
                existing.request_id = new_request.id
                existing.department = item_data.department
                affected_request_ids.add(new_request.id)
                affected_departments.add(item_data.department.value)

            # Status change to Closed
            if item_data.status == Status.CLOSED and existing.status == Status.OPEN:
                existing.status = Status.CLOSED
                existing.closed_at = now
                affected_request_ids.add(existing.request_id)
                affected_departments.add(existing.department.value)
                closed += 1
            elif item_data.status == Status.OPEN and existing.status == Status.CLOSED:
                declined.append(DeclinedItem(
                    external_id=item_data.external_id,
                    reason="Item is closed and cannot be reopened.",
                ))
                continue
            elif item_data.status == Status.CLOSED and existing.status == Status.CLOSED:
                declined.append(DeclinedItem(
                    external_id=item_data.external_id,
                    reason="Item is already closed.",
                ))
                continue
            else:
                existing.message_text = item_data.message_text
                existing.medications = item_data.medications

            existing.updated_at = now
            updated += 1

    # Check if any affected requests should be closed
    for request_id in affected_request_ids:
        await _maybe_close_request(db, request_id)

    await db.commit()

    # Broadcast SSE updates per department
    for dept in affected_departments:
        request_ids_for_dept = [
            str(rid) for rid in affected_request_ids
        ]
        await sse_manager.broadcast(dept, request_ids_for_dept)

    return BatchIngestResponse(created=created, updated=updated, closed=closed, declined=declined)
