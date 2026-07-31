// Thin API client for the PFM backend. Attaches the Keycloak bearer token and
// transparently renews the password-fallback session on a 401 (Session 742,
// Bug 3): one silent refresh + retry; if that still fails, the fallback session
// is cleared and a `pfm:session-expired` event is dispatched so the shell can
// prompt re-login instead of cascading raw 401 errors on every page.
import { getToken, refreshFallback, hasFallbackSession, clearFallbackSession, isAuthenticated } from "./auth";

const BASE = import.meta.env.VITE_API_BASE_URL || "/api";

function notifySessionExpired() {
  try {
    window.dispatchEvent(new CustomEvent("pfm:session-expired"));
  } catch {
    /* ignore */
  }
}

// Item 21: FastAPI 422 validation errors return `detail` as an **array of
// objects** ({loc, msg, type}); rendering that directly showed "[object Object]".
// Normalize any detail shape (string | object | array) into readable text.
function formatDetail(detail) {
  if (detail == null) return null;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => {
        if (typeof d === "string") return d;
        if (d && typeof d === "object") {
          const loc = Array.isArray(d.loc) ? d.loc.filter((x) => x !== "body").join(".") : "";
          const msg = d.msg || d.detail || JSON.stringify(d);
          return loc ? `${loc}: ${msg}` : msg;
        }
        return String(d);
      })
      .join("; ");
  }
  if (typeof detail === "object") return detail.msg || JSON.stringify(detail);
  return String(detail);
}

// Requests must never hang forever (otherwise DataGrid/BusyIndicator spin with
// no feedback). Abort after a timeout so the caller's catch runs and the UI can
// show an error / re-login prompt. (Session 815, Batch 7 follow-up.)
const REQUEST_TIMEOUT_MS = 20000;

async function doFetch(method, path, qs, body) {
  const headers = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers["Authorization"] = "Bearer " + token;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    return await fetch(BASE + path + qs, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
  } catch (e) {
    if (e && e.name === "AbortError") {
      throw new Error("Request timed out. The server did not respond.");
    }
    throw new Error("Network error: " + (e && e.message ? e.message : String(e)));
  } finally {
    clearTimeout(timer);
  }
}

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

  let resp = await doFetch(method, path, qs, body);

  // On 401 with a password-fallback session, try one silent refresh + retry.
  if (resp.status === 401 && hasFallbackSession()) {
    const renewed = await refreshFallback();
    if (renewed) {
      resp = await doFetch(method, path, qs, body);
    }
    if (resp.status === 401) {
      clearFallbackSession();
      notifySessionExpired();
    }
  } else if (resp.status === 401 && !isAuthenticated()) {
    // Guest / not-signed-in: the shell may have rendered before a completed
    // sign-in (or the session was never established). Prompt login instead of
    // leaving every list to fail silently with empty tables.
    notifySessionExpired();
  }

  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const err = await resp.json();
      detail = formatDetail(err.detail) || JSON.stringify(err);
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
  put: (path, body) => request("PUT", path, { body }),
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