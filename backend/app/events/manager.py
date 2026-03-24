import asyncio
import json
from collections import defaultdict


class SSEManager:
    def __init__(self):
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)

    def subscribe(self, department: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers[department].append(queue)
        return queue

    def unsubscribe(self, department: str, queue: asyncio.Queue):
        if department in self._subscribers:
            self._subscribers[department] = [
                q for q in self._subscribers[department] if q is not queue
            ]

    async def broadcast(self, department: str, request_ids: list[str]):
        data = json.dumps({"event": "requests_updated", "request_ids": request_ids})
        for queue in self._subscribers.get(department, []):
            await queue.put(data)


sse_manager = SSEManager()
