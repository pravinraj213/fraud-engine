export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === "string" ? detail : `Request failed (${status})`);
    this.status = status;
    this.detail = detail;
  }
}

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`/api${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    throw new ApiError(0, "Cannot reach the API. Is the backend running?");
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = body?.detail;
    const message = Array.isArray(detail) ? detail.map((d) => d.msg).join("; ") : detail;
    throw new ApiError(res.status, message || `${res.status} ${res.statusText}`);
  }
  return body;
}

export const api = {
  stats: () => request("/stats"),
  system: () => request("/system"),
  createTransaction: (body) => request("/transactions", { method: "POST", body: JSON.stringify(body) }),
  rules: () => request("/rules"),
  flags: (params) => request(`/flags?${new URLSearchParams(params)}`),
  transaction: (id) => request(`/transactions/${encodeURIComponent(id)}`),
  review: (id, { action, reviewer, note }) =>
    request(`/transactions/${encodeURIComponent(id)}/review`, {
      method: "POST",
      body: JSON.stringify({ action, reviewer, note: note || null }),
    }),
};
