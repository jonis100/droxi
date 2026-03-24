from fastapi import APIRouter

from app.api import health, inbox, requests, sse

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(inbox.router)
api_router.include_router(requests.router)
api_router.include_router(sse.router)
