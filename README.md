# Clinic Inbox

A system for organizing patient inbox items into consolidated requests per department, with a live dashboard for doctors.

## Quick Start

```bash
# 1. Clone and navigate
cd droxi

# 2. Start all services
docker-compose up --build

# 3. Access
# - Frontend:  http://localhost:4200
# - API docs:  http://localhost:8000/docs
# - Health:    http://localhost:8000/api/health
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for system design, data model, trade-offs, and scaling guidelines.

## Tech Stack

| Component      | Technology                                            |
| -------------- | ----------------------------------------------------- |
| Backend        | Python 3.12, FastAPI, SQLAlchemy 2.0 (async)          |
| Database       | PostgreSQL 16                                         |
| Frontend       | Angular 19, Angular Material                          |
| Live updates   | Server-Sent Events (SSE)                              |
| Infrastructure | Docker, Docker Compose                                |

## API Endpoints

| Method | Path                               | Description                                                |
| ------ | ---------------------------------- | ---------------------------------------------------------- |
| POST   | `/api/inbox/batch`                 | Ingest a batch of inbox items                              |
| GET    | `/api/requests`                    | List requests (filter by `department`, `status`, paginate) |
| GET    | `/api/requests/{id}`               | Get request detail with items                              |
| GET    | `/api/events/updates?department=X` | SSE stream for live updates                                |
| GET    | `/api/health`                      | Health check                                               |

Full OpenAPI documentation available at `http://localhost:8000/docs` when running.

## Environment Variables

| Variable            | Default                     | Description          |
| ------------------- | --------------------------- | -------------------- |
| `POSTGRES_DB`       | `clinic_inbox`              | Database name        |
| `POSTGRES_USER`     | `clinic`                    | Database user        |
| `POSTGRES_PASSWORD` | `clinic_pass`               | Database password    |
| `CORS_ORIGINS`      | `["http://localhost:4200"]` | Allowed CORS origins |
| `BACKEND_PORT`      | `8000`                      | Backend exposed port |

Copy `.env.example` to `.env` and adjust as needed.

## Development — Live Reload

Docker Compose Watch automatically syncs or rebuilds containers when source files change.

```bash
docker-compose up --build --watch
```

| Service    | Trigger                     | Action                                                               |
| ---------- | --------------------------- | -------------------------------------------------------------------- |
| `backend`  | any file in `backend/`      | synced into the container; uvicorn `--reload` restarts automatically |
| `backend`  | `backend/requirements.txt`  | full image rebuild                                                   |
| `frontend` | any file in `frontend/src/` | full image rebuild + container restart                               |
| `frontend` | `frontend/package.json`     | full image rebuild + container restart                               |

> Requires Docker Compose v2.22+. Run `docker compose version` to check.

## Running Tests

```bash
# Backend tests (requires Python 3.12+ and dependencies)
cd backend
pip install -r requirements.txt
pytest

# Or via Docker
docker-compose exec backend pytest
```

## Sample Batch Request

```bash
curl -X POST http://localhost:8000/api/inbox/batch \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {
        "external_id": "ext-001",
        "patient_id": "patient-123",
        "message_text": "I need a medication refill",
        "medications": ["Ibuprofen", "Metformin"],
        "department": "Primary",
        "status": "Open"
      },
      {
        "external_id": "ext-002",
        "patient_id": "patient-123",
        "message_text": "Skin rash follow-up",
        "department": "Dermatology",
        "status": "Open"
      }
    ]
  }'
```

## Project Structure

```
droxi/
├── docker-compose.yml          # Orchestrates all services
├── .env                        # Environment configuration
├── ARCHITECTURE.md             # Design document
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI application
│   │   ├── config.py           # Settings from env vars
│   │   ├── database.py         # SQLAlchemy async setup
│   │   ├── models/             # ORM models
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── repositories/       # Data access layer
│   │   ├── services/           # Business logic
│   │   ├── api/                # Route handlers
│   │   └── events/             # SSE broadcast manager
│   └── tests/                  # pytest test suite
└── frontend/
    ├── src/app/
    │   ├── components/         # Dashboard, request list, detail
    │   ├── services/           # API + SSE services
    │   └── models/             # TypeScript interfaces
    ├── nginx.conf              # Reverse proxy config
    └── Dockerfile              # Multi-stage build
```
