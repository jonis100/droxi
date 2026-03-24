import http from "k6/http";
import { check, sleep } from "k6";
import { BASE_URL, THRESHOLDS } from "./config.js";

export const options = {
  scenarios: {
    health_check: {
      executor: "constant-vus",
      vus: 5,
      duration: "30s",
    },
  },
  thresholds: THRESHOLDS,
};

export default function () {
  const res = http.get(`${BASE_URL}/api/health`);

  check(res, {
    "status is 200": (r) => r.status === 200,
    "response has healthy status": (r) => r.json().status === "healthy",
    "response time < 200ms": (r) => r.timings.duration < 200,
  });

  sleep(0.5);
}
