import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_batch_endpoint_returns_counts(client: AsyncClient):
    payload = {
        "items": [
            {
                "external_id": "api-ext-1",
                "patient_id": "patient-100",
                "message_text": "Need refill",
                "medications": ["Metformin"],
                "department": "Dermatology",
                "status": "Open",
            },
            {
                "external_id": "api-ext-2",
                "patient_id": "patient-100",
                "message_text": "Follow-up question",
                "department": "Dermatology",
                "status": "Open",
            },
        ]
    }
    response = await client.post("/api/inbox/batch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["created"] == 2
    assert data["updated"] == 0
    assert data["closed"] == 0


@pytest.mark.asyncio
async def test_list_requests_filter_by_department(client: AsyncClient):
    # Ingest items in two departments
    payload = {
        "items": [
            {
                "external_id": "filter-ext-1",
                "patient_id": "patient-200",
                "message_text": "Skin rash",
                "department": "Dermatology",
                "status": "Open",
            },
            {
                "external_id": "filter-ext-2",
                "patient_id": "patient-200",
                "message_text": "X-ray results",
                "department": "Radiology",
                "status": "Open",
            },
        ]
    }
    await client.post("/api/inbox/batch", json=payload)

    # Filter by Dermatology
    response = await client.get("/api/requests", params={"department": "Dermatology"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert all(r["department"] == "Dermatology" for r in data["items"])


@pytest.mark.asyncio
async def test_get_request_detail_includes_items(client: AsyncClient):
    # Ingest
    payload = {
        "items": [
            {
                "external_id": "detail-ext-1",
                "patient_id": "patient-300",
                "message_text": "Checkup needed",
                "department": "Primary",
                "status": "Open",
            }
        ]
    }
    await client.post("/api/inbox/batch", json=payload)

    # List to get ID
    list_resp = await client.get("/api/requests", params={"department": "Primary"})
    request_id = list_resp.json()["items"][0]["id"]

    # Get detail
    response = await client.get(f"/api/requests/{request_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == request_id
    assert len(data["items"]) == 1
    assert data["items"][0]["message_text"] == "Checkup needed"


@pytest.mark.asyncio
async def test_get_request_not_found(client: AsyncClient):
    response = await client.get("/api/requests/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
