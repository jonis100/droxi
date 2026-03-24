from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.inbox_item import BatchIngestRequest, BatchIngestResponse
from app.services import ingestion_service

router = APIRouter(tags=["Inbox"])


@router.post("/inbox/batch", response_model=BatchIngestResponse)
async def ingest_batch(
    payload: BatchIngestRequest,
    db: AsyncSession = Depends(get_db),
):
    """Ingest a batch of inbox items from the external system."""
    return await ingestion_service.process_batch(db, payload.items)
