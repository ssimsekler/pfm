// Thin API client for the PFM backend. Attaches the Keycloak bearer token.
import { getToken } from "./auth";

const BASE = import.meta.env.VITE_API_BASE_URL || "/api";

async function request(method, path, opts) {
  const { body, params } = opts || {};
  let qs = "";
  if (params) {
    const usp = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") usp.set(k, v);
    });
    const s = usp.toString();
    if (s) qs = "?" + s;
  }
  const headers = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers["Authorization"] = "Bearer " + token;

  const resp = await fetch(BASE + path + qs, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const err = await resp.json();
      detail = err.detail || JSON.stringify(err);
    } catch (_) {
      /* ignore */
    }
    throw new Error(resp.status + ": " + detail);
  }
  if (resp.status === 204) return null;
  const ct = resp.headers.get("content-type") || "";
  return ct.includes("application/json") ? resp.json() : resp.text();
}

export const api = {
  get: (path, params) => request("GET", path, { params }),
  post: (path, body) => request("POST", path, { body }),
  patch: (path, body) => request("PATCH", path, { body }),
  del: (path) => request("DELETE", path),

  async upload(path, file, fields) {
    const form = new FormData();
    form.append("file", file);
    Object.entries(fields || {}).forEach(([k, v]) => form.append(k, v));
    const headers = {};
    const token = getToken();
    if (token) headers["Authorization"] = "Bearer " + token;
    const resp = await fetch(BASE + path, { method: "POST", headers, body: form });
    if (!resp.ok) throw new Error(resp.status + ": " + (await resp.text()));
    return resp.json();
  },
};

// Convenience: value-help (code list values).
export async function loadCodeValues(listKey) {
  try {
    return await api.get("/v1/code-lists/" + listKey + "/values");
  } catch {
    return [];
  }
}