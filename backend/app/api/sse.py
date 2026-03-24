import asyncio

from fastapi import APIRouter, Query
from sse_starlette.sse import EventSourceResponse

from app.events.manager import sse_manager
from app.models.patient_request import Department

router = APIRouter(tags=["Events"])


@router.get("/events/updates")
async def event_stream(department: Department | None = Query(None)):
    """SSE endpoint for live updates. Subscribe to one or all departments."""
    if department:
        departments = [department.value]
    else:
        departments = [d.value for d in Department]

    merged: asyncio.Queue = asyncio.Queue()
    dept_queues: dict[str, asyncio.Queue] = {}
    relay_tasks: list[asyncio.Task] = []

    for d in departments:
        q = sse_manager.subscribe(d)
        dept_queues[d] = q

        async def relay(source=q):
            try:
                while True:
                    data = await source.get()
                    await merged.put(data)
            except asyncio.CancelledError:
                return

        relay_tasks.append(asyncio.create_task(relay()))

    async def generate():
        try:
            while True:
                try:
                    data = await asyncio.wait_for(merged.get(), timeout=30)
                    yield {"event": "update", "data": data}
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": ""}
        except asyncio.CancelledError:
            return
        finally:
            for task in relay_tasks:
                task.cancel()
            for d, q in dept_queues.items():
                sse_manager.unsubscribe(d, q)

    return EventSourceResponse(generate())
