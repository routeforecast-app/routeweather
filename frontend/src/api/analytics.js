import apiClient from "./client";

export async function trackVisit(payload) {
  await apiClient.post("/analytics/visit", payload, {
    timeout: 5000,
  });
}
