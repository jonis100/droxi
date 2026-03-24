import http from "k6/http";
import { check, group, sleep } from "k6";
import { BASE_URL, THRESHOLDS, DEPARTMENTS } from "./config.js";

export const options = {
  scenarios: {
    // Simulate doctors browsing the dashboard
    browsing: {
      executor: "ramping-vus",
      startVUs: 1,
      stages: [
        { duration: "30s", target: 10 },
        { duration: "1m", target: 50 },
        { duration: "1m", target: 50 },
        { duration: "30s", target: 0 },
      ],
    },
  },
  thresholds: THRESHOLDS,
};

export default function () {
  const dept =
    DEPARTMENTS[Math.floor(Math.random() * DEPARTMENTS.length)];

  group("List requests by department", () => {
    const res = http.get(
      `${BASE_URL}/api/requests?department=${dept}&status=Open&page=1&page_size=20`
    );

    check(res, {
      "status is 200": (r) => r.status === 200,
      "has items array": (r) => Array.isArray(r.json().items),
      "has pagination": (r) => r.json().total !== undefined,
      "response time < 500ms": (r) => r.timings.duration < 500,
    });

    // Drill into a request detail if results exist
    const items = res.json().items;
    if (items && items.length > 0) {
      const requestId = items[Math.floor(Math.random() * items.length)].id;

      group("View request detail", () => {
        const detailRes = http.get(
          `${BASE_URL}/api/requests/${requestId}`
        );

        check(detailRes, {
          "detail status is 200": (r) => r.status === 200,
          "detail has items": (r) => Array.isArray(r.json().items),
          "detail response time < 300ms": (r) => r.timings.duration < 300,
        });
      });
    }
  });

  // Simulate browsing multiple pages
  group("Paginate through requests", () => {
    for (let page = 1; page <= 3; page++) {
      const res = http.get(
        `${BASE_URL}/api/requests?department=${dept}&page=${page}&page_size=20`
      );

      check(res, {
        [`page ${page} status 200`]: (r) => r.status === 200,
      });
    }
  });

  sleep(2);
}
