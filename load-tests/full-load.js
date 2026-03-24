import http from "k6/http";
import { check, group, sleep } from "k6";
import { Counter, Trend } from "k6/metrics";
import {
  BASE_URL,
  THRESHOLDS,
  DEPARTMENTS,
  randomDepartment,
  randomExternalId,
} from "./config.js";

const batchDuration = new Trend("batch_processing_duration");
const totalItemsIngested = new Counter("total_items_ingested");
const itemsCreated = new Counter("items_created");
const itemsUpdated = new Counter("items_updated");
const itemsClosed = new Counter("items_closed");

// Deterministic external_id for items that will be updated in later iterations
function reusableExternalId(vuId, slot) {
  return `EXT-REUSE-${vuId}-${slot}`;
}

export const options = {
  scenarios: {
    // External system sending batches (new + updates + closures)
    batch_ingest: {
      executor: "constant-arrival-rate",
      rate: 2,
      timeUnit: "1s",
      duration: "3m",
      preAllocatedVUs: 10,
      maxVUs: 30,
      exec: "ingestMixedBatch",
    },
    // Doctors browsing the dashboard
    dashboard_browse: {
      executor: "ramping-vus",
      startVUs: 5,
      stages: [
        { duration: "30s", target: 20 },
        { duration: "2m", target: 50 },
        { duration: "30s", target: 0 },
      ],
      exec: "browseDashboard",
    },
  },
  thresholds: {
    ...THRESHOLDS,
    "http_req_duration{scenario:batch_ingest}": ["p(95)<15000"],
    "http_req_duration{scenario:dashboard_browse}": ["p(95)<3000"],
    batch_processing_duration: ["p(95)<15000"],
  },
};

/**
 * Builds a batch that exercises all ingestion paths:
 *
 * 1. Fully-closed request  — all items Closed → request auto-closes
 * 2. Partially-closed request — mix of Open & Closed → request stays Open
 * 3. Fully-open request — all items Open → request stays Open
 * 4. Reusable items — created Open now, will be updated/closed in later iterations
 * 5. Updates — content updates and status closures for items from prior iterations
 */
function buildMixedBatch(vuId, iter) {
  const items = [];

  // --- 1. Fully-closed request (3 Closed items, same patient+dept) ---
  const closedDept = randomDepartment();
  for (let i = 0; i < 3; i++) {
    items.push({
      external_id: randomExternalId(),
      patient_id: `PAT-CL-${vuId}-${iter}`,
      message_text: `Closed-group item ${i}`,
      medications: ["Med A"],
      department: closedDept,
      status: "Closed",
    });
  }

  // --- 2. Partially-closed request (2 Open + 2 Closed, same patient+dept) ---
  const partialDept = randomDepartment();
  for (let i = 0; i < 4; i++) {
    items.push({
      external_id: randomExternalId(),
      patient_id: `PAT-PC-${vuId}-${iter}`,
      message_text: `Partial-group item ${i}`,
      medications: ["Med B"],
      department: partialDept,
      status: i < 2 ? "Open" : "Closed",
    });
  }

  // --- 3. Fully-open request (3 Open items, same patient+dept) ---
  const openDept = randomDepartment();
  for (let i = 0; i < 3; i++) {
    items.push({
      external_id: randomExternalId(),
      patient_id: `PAT-OP-${vuId}-${iter}`,
      message_text: `Open-group item ${i}`,
      medications: ["Med C"],
      department: openDept,
      status: "Open",
    });
  }

  // --- 4. Reusable items — Open now, updated/closed in future iterations ---
  const reuseDept = DEPARTMENTS[0];
  for (let i = 0; i < 3; i++) {
    items.push({
      external_id: reusableExternalId(vuId, iter * 10 + i),
      patient_id: `PAT-UPD-${vuId}`,
      message_text: `Reusable item ${i} created at iter ${iter}`,
      medications: ["Med D"],
      department: reuseDept,
      status: "Open",
    });
  }
  // Extra item at slot +5 that will be specifically closed later
  items.push({
    external_id: reusableExternalId(vuId, iter * 10 + 5),
    patient_id: `PAT-UPD-${vuId}`,
    message_text: `Closeable item created at iter ${iter}`,
    medications: ["Med D"],
    department: reuseDept,
    status: "Open",
  });

  // --- 5. Updates to items created in the previous iteration ---
  if (iter > 0) {
    const prev = iter - 1;

    // Content updates (keep Open)
    for (let i = 0; i < 2; i++) {
      items.push({
        external_id: reusableExternalId(vuId, prev * 10 + i),
        patient_id: `PAT-UPD-${vuId}`,
        message_text: `Updated content at iter ${iter}`,
        medications: ["Med Updated"],
        department: reuseDept,
        status: "Open",
      });
    }

    // Close one item from the previous iteration
    items.push({
      external_id: reusableExternalId(vuId, prev * 10 + 5),
      patient_id: `PAT-UPD-${vuId}`,
      message_text: `Closing item from iter ${prev}`,
      medications: [],
      department: reuseDept,
      status: "Closed",
    });
  }

  return items;
}

export function ingestMixedBatch() {
  const items = buildMixedBatch(__VU, __ITER);

  const res = http.post(
    `${BASE_URL}/api/inbox/batch`,
    JSON.stringify({ items }),
    { headers: { "Content-Type": "application/json" } }
  );

  batchDuration.add(res.timings.duration);

  check(res, {
    "batch status 200": (r) => r.status === 200,
    "batch under 15s": (r) => r.timings.duration < 15000,
  });

  if (res.status === 200) {
    const body = res.json();
    totalItemsIngested.add(items.length);
    itemsCreated.add(body.created || 0);
    itemsUpdated.add(body.updated || 0);
    itemsClosed.add(body.closed || 0);
  }
}

export function browseDashboard() {
  const dept = DEPARTMENTS[Math.floor(Math.random() * DEPARTMENTS.length)];

  group("Dashboard flow", () => {
    // List requests
    const listRes = http.get(
      `${BASE_URL}/api/requests?department=${dept}&status=Open&page=1&page_size=20`
    );

    check(listRes, {
      "list status 200": (r) => r.status === 200,
      "list under 2s": (r) => r.timings.duration < 2000,
    });

    // View a detail if available
    if (listRes.status !== 200) return;
    const reqItems = listRes.json().items;
    if (reqItems && reqItems.length > 0) {
      const id = reqItems[Math.floor(Math.random() * reqItems.length)].id;
      const detailRes = http.get(`${BASE_URL}/api/requests/${id}`);

      check(detailRes, {
        "detail status 200": (r) => r.status === 200,
        "detail under 2s": (r) => r.timings.duration < 2000,
      });
    }
  });

  sleep(2);
}
