import http from "k6/http";
import { check, sleep } from "k6";
import { Counter, Trend } from "k6/metrics";
import {
  BASE_URL,
  THRESHOLDS,
  randomDepartment,
  randomPatientId,
  randomExternalId,
} from "./config.js";

const itemsCreated = new Counter("items_created");
const itemsUpdated = new Counter("items_updated");
const batchDuration = new Trend("batch_processing_duration");

export const options = {
  scenarios: {
    // Ramp up: simulate increasing batch load
    ramp_up: {
      executor: "ramping-vus",
      startVUs: 1,
      stages: [
        { duration: "30s", target: 5 },
        { duration: "1m", target: 10 },
        { duration: "30s", target: 20 },
        { duration: "1m", target: 20 },
        { duration: "30s", target: 0 },
      ],
    },
  },
  thresholds: {
    ...THRESHOLDS,
    batch_processing_duration: ["p(95)<10000"],
  },
};

function generateBatchPayload(size) {
  const items = [];
  for (let i = 0; i < size; i++) {
    items.push({
      external_id: randomExternalId(),
      patient_id: randomPatientId(),
      message_text: `Load test message ${i + 1} - ${Date.now()}`,
      medications: ["Medication A", "Medication B"],
      department: randomDepartment(),
      status: "Open",
    });
  }
  return { items };
}

export default function () {
  // Vary batch sizes: small (10), medium (50), large (100)
  const batchSizes = [10, 50, 100];
  const batchSize = batchSizes[Math.floor(Math.random() * batchSizes.length)];

  const payload = JSON.stringify(generateBatchPayload(batchSize));

  const res = http.post(`${BASE_URL}/api/inbox/batch`, payload, {
    headers: { "Content-Type": "application/json" },
    tags: { batch_size: String(batchSize) },
  });

  batchDuration.add(res.timings.duration);

  check(res, {
    "batch accepted (200)": (r) => r.status === 200,
    "response has created count": (r) => r.json().created !== undefined,
    "response has updated count": (r) => r.json().updated !== undefined,
    "response time < 5s": (r) => r.timings.duration < 5000,
  });

  if (res.status === 200) {
    const body = res.json();
    itemsCreated.add(body.created);
    itemsUpdated.add(body.updated);
  }

  sleep(1);
}
