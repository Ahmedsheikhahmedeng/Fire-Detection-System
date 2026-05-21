export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const WS_BASE_URL = API_BASE_URL.replace(/^http/, "ws");

export async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(data?.detail || "API request failed");
  }

  return data;
}

export const api = {
  getHealth: () => request("/health"),
  getMapStatus: () => request("/map/status"),
  getSchedulerStatus: () => request("/scheduler/status"),
  getMapHotspots: () => request("/map/hotspots"),
  getMapStats: () => request("/map/stats"),
  sendTestEmail: (email) =>
    request("/alerts/test-email", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
};
