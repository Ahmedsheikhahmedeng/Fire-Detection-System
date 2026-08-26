const configuredApiBaseUrl = (import.meta.env.VITE_API_BASE_URL || "").trim();

export const API_BASE_URL =
  configuredApiBaseUrl && configuredApiBaseUrl !== "/"
    ? configuredApiBaseUrl.replace(/\/$/, "")
    : "";

export const WS_BASE_URL = API_BASE_URL
  ? API_BASE_URL.replace(/^http/, "ws")
  : `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`;

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
  getMapStatus: () => request("/api/map/status"),
  getSchedulerStatus: () => request("/api/scheduler/status"),
  getMapHotspots: () => request("/api/map/hotspots"),
  getMapStats: () => request("/api/map/stats"),
  sendTestEmail: (email) =>
    request("/api/alerts/email-subscribe", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  subscribeSms: (phone) =>
    request("/api/alerts/sms-subscribe", {
      method: "POST",
      body: JSON.stringify({ phone }),
    }),
};
