# Load Test Plan — Clinic Inbox

## 1. Objectives

Validate that the Clinic Inbox backend meets performance requirements under expected and peak loads:

- **Response time**: API endpoints respond within acceptable latency thresholds
- **Throughput**: System handles the expected request rate without errors
- **Stability**: No degradation under sustained load
- **Concurrency**: Batch ingestion and dashboard browsing work correctly under simultaneous load

## 2. Scope

### In Scope
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check availability |
| `/api/inbox/batch` | POST | Batch item ingestion (core write path) |
| `/api/requests` | GET | List/filter patient requests (core read path) |
| `/api/requests/{id}` | GET | Request detail view |

### Out of Scope
- `/api/events/updates` (SSE) — long-lived connections require separate tooling
- Frontend rendering performance
- Database-specific benchmarks (covered by DB tooling)

## 3. Test Scenarios

### 3.1 Health Check (`health-check.js`)
| Parameter | Value |
|-----------|-------|
| Virtual Users | 5 |
| Duration | 30 seconds |
| Purpose | Baseline availability check |

**Pass Criteria:**
- 100% success rate
- p95 response time < 200ms

---

### 3.2 Batch Ingestion (`batch-ingest.js`)
| Parameter | Value |
|-----------|-------|
| Ramp-up | 1 → 5 → 10 → 20 VUs |
| Duration | ~3.5 minutes |
| Batch sizes | 10, 50, 100 items (random) |
| Purpose | Stress test the write path |

**Pass Criteria:**
- Error rate < 5%
- p95 response time < 2 seconds
- p95 batch processing < 2 seconds

---

### 3.3 Dashboard Browsing (`browse-requests.js`)
| Parameter | Value |
|-----------|-------|
| Ramp-up | 1 → 10 → 50 VUs |
| Duration | ~3 minutes |
| Actions | List by department, view detail, paginate |
| Purpose | Simulate concurrent doctors browsing |

**Pass Criteria:**
- Error rate < 5%
- p95 list response time < 500ms
- p95 detail response time < 300ms

---

### 3.4 Full Load — Mixed Workload (`full-load.js`)
| Parameter | Value |
|-----------|-------|
| Batch ingest rate | 2 requests/second (constant arrival) |
| Dashboard VUs | 5 → 20 → 50 |
| Duration | 3 minutes |
| Purpose | Realistic mixed read/write workload |

**Batch composition per iteration (~14–17 items):**

| Group | Items | Status | Effect |
|-------|-------|--------|--------|
| Fully-closed request | 3 | all Closed | Request auto-closes (no open items) |
| Partially-closed request | 4 | 2 Open + 2 Closed | Request stays Open |
| Fully-open request | 3 | all Open | Request stays Open |
| Reusable items (new) | 4 | all Open | Created for future updates |
| Content updates | 2 | Open → Open | Updates `message_text`/`medications` on prior items |
| Status closure | 1 | Open → Closed | Closes an item from the previous iteration |

- New items use unique `external_id`s; updates reuse deterministic `external_id`s across iterations
- Each VU builds up its own update chain (`PAT-UPD-{vuId}`)

**Pass Criteria:**
- Error rate < 5%
- p95 batch duration < 15 seconds
- p95 browse duration < 3 seconds

## 4. Performance Thresholds (Global)

| Metric | Threshold |
|--------|-----------|
| `http_req_duration` p95 | < 500ms |
| `http_req_duration` p99 | < 1000ms |
| `http_req_failed` rate | < 5% |
| `http_reqs` rate | > 10 req/s |

## 5. Test Environment

- **Infrastructure**: Docker Compose (same as development)
- **Database**: PostgreSQL 16 Alpine (single instance)
- **Backend**: FastAPI with Uvicorn (single instance, `--reload` disabled for tests)
- **Load generator**: k6 running in a Docker container on the same Docker network

## 6. Test Data

- Patient IDs: randomly generated (`PAT-00000` to `PAT-09999`)
- External IDs: unique per request using timestamp + random suffix
- Deterministic external IDs (`EXT-REUSE-{vu}-{slot}`) for update/close scenarios in full-load
- Departments: evenly distributed across Dermatology, Radiology, Primary
- Item status mix in full-load: fully-closed, partially-closed, and fully-open request groups
- Full-load patient prefixes: `PAT-CL-` (closed), `PAT-PC-` (partial), `PAT-OP-` (open), `PAT-UPD-` (updates)

## 7. How to Run

```bash
# Run all tests with report output
docker compose --profile load-test run --rm k6-health
docker compose --profile load-test run --rm k6-batch
docker compose --profile load-test run --rm k6-browse
docker compose --profile load-test run --rm k6-full

# Or run a specific test manually
docker compose run --rm k6 run /scripts/health-check.js
```

Reports are written to the `report/` directory as JSON files.

## 8. Report Outputs

Each test run produces:
- **Console summary**: printed to stdout during the run
- **JSON report**: detailed metrics saved to `report/k6-<test-name>-report.json`

### Key Metrics in Reports
- `http_req_duration`: response time distribution (min, max, avg, p90, p95, p99)
- `http_req_failed`: error rate
- `http_reqs`: total requests and throughput (req/s)
- `iterations`: completed test iterations
- Custom metrics: `batch_processing_duration`, `items_created`, `items_updated`, `items_closed`, `total_items_ingested`

## 9. Scale Assumptions (from Architecture Document)

| Dimension | Expected |
|-----------|----------|
| Concurrent dashboard users | 50–200 |
| Batch size | 100–1,000 items |
| Batch frequency | every few minutes |
| Active patients | ~50K total |
| Active items | ~500K total |

The load tests simulate the **upper range** of these assumptions to validate headroom.
