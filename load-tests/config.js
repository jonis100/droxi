// Shared configuration for k6 load tests

export const BASE_URL = __ENV.BASE_URL || "http://backend:8000";

export const DEPARTMENTS = ["Dermatology", "Radiology", "Primary"];

export const THRESHOLDS = {
  http_req_duration: ["p(95)<5000", "p(99)<15000"],
  http_req_failed: ["rate<0.10"],
  http_reqs: ["rate>10"],
};

export function randomDepartment() {
  return DEPARTMENTS[Math.floor(Math.random() * DEPARTMENTS.length)];
}

export function randomPatientId() {
  return `PAT-${String(Math.floor(Math.random() * 10000)).padStart(5, "0")}`;
}

export function randomExternalId() {
  return `EXT-${Date.now()}-${Math.floor(Math.random() * 1000000)}`;
}
