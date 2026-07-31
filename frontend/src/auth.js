// Keycloak-based authentication for the PFM frontend.
//
// Exposes a small, framework-agnostic API used by App.jsx and api.js:
//   - initAuth():  initialize Keycloak (SSO check), start token refresh
//   - getUser():   { name, roles } for the current user (guest if not logged in)
//   - getToken():  current bearer token (or null)
//   - login():     redirect to Keycloak login
//   - logout():    redirect to Keycloak logout
//
// Configuration comes from Vite env vars (build-time), defaulting to the
// reverse-proxied paths used by the docker-compose/Traefik setup.
import Keycloak from "keycloak-js";

const KC_URL = import.meta.env.VITE_KEYCLOAK_URL || "/auth";
const KC_REALM = import.meta.env.VITE_KEYCLOAK_REALM || "pfm";
const KC_CLIENT_ID = import.meta.env.VITE_KEYCLOAK_CLIENT_ID || "pfm-frontend";

let keycloak = null;
let authenticated = false;

// Password-fallback session (#14): when Keycloak's redirect flow isn't used, the
// SPA can sign in via the backend `/v1/auth/password-login` proxy. We keep the
// resulting token + refresh token in memory + sessionStorage and decode it for
// identity/roles. The refresh token lets us silently renew (Session 742, Bug 3).
let fallbackToken = sessionStorage.getItem("pfm_fallback_token") || null;
let fallbackRefreshToken = sessionStorage.getItem("pfm_fallback_refresh") || null;

function guestUser() {
  return { name: "Guest", roles: [], authenticated: false };
}

function decodeJwt(token) {
  try {
    const payload = token.split(".")[1];
    const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(decodeURIComponent(escape(json)));
  } catch {
    return null;
  }
}

/**
 * Initialize Keycloak. Uses `check-sso` so the app can load for anonymous
 * users without forcing a login redirect. If Keycloak is unreachable (e.g.
 * the realm hasn't been imported yet in a fresh dev environment) we fail
 * soft and continue as a guest so the UI still renders.
 */
// Remove OIDC callback params (state/code/session_state/iss) that Keycloak
// appends to the redirect URL. With HashRouter these land on the query string
// of the base URL; leaving them there makes `check-sso` re-trigger on the next
// mount, causing an endless redirect loop (a new `state` each time).
function stripOidcParams() {
  try {
    const url = new URL(window.location.href);
    let changed = false;
    ["state", "code", "session_state", "iss", "error"].forEach((k) => {
      if (url.searchParams.has(k)) { url.searchParams.delete(k); changed = true; }
    });
    if (changed) {
      const qs = url.searchParams.toString();
      const clean = url.origin + url.pathname + (qs ? `?${qs}` : "") + url.hash;
      window.history.replaceState({}, document.title, clean);
    }
  } catch {
    /* ignore */
  }
}

export async function initAuth() {
  // If we already have a password-fallback session, don't run the SSO redirect
  // flow at all (avoids the OIDC callback/redirect loop).
  if (fallbackToken) {
    return true;
  }
  try {
    keycloak = new Keycloak({
      url: KC_URL,
      realm: KC_REALM,
      clientId: KC_CLIENT_ID,
    });

    // Initialize WITHOUT onLoad:"check-sso". The silent-SSO iframe/redirect flow
    // loops behind the dev proxy (HashRouter leaves state/code on the base URL,
    // and the iframe session check re-triggers). We only complete a login if the
    // URL already carries an OIDC callback (state+code from a real login); the
    // rest of the time the app loads as guest and the user signs in explicitly
    // (SSO button or the password dialog). This removes the redirect loop.
    const hasCallback = (() => {
      try {
        const p = new URLSearchParams(window.location.search);
        return p.has("code") && p.has("state");
      } catch {
        return false;
      }
    })();

    authenticated = await keycloak.init({
      pkceMethod: "S256",
      checkLoginIframe: false,
      ...(hasCallback ? {} : { onLoad: undefined }),
    });

    // Clean any leftover OIDC callback params so we don't loop on re-mount.
    stripOidcParams();

    if (authenticated) {
      // Keep the token fresh; refresh when it has <60s of validity left.
      setInterval(() => {
        keycloak.updateToken(60).catch(() => {
          // On refresh failure, drop to guest state (session likely expired).
          authenticated = false;
        });
      }, 30000);
    }
  } catch (err) {
    // Non-fatal: continue as guest so the app remains usable in dev.
    // eslint-disable-next-line no-console
    console.warn("Keycloak init failed; continuing as guest.", err);
    authenticated = false;
    stripOidcParams();
  }
  return authenticated;
}

/** Current user profile derived from the Keycloak (or fallback) token. */
export function getUser() {
  if ((!keycloak || !authenticated || !keycloak.tokenParsed) && fallbackToken) {
    const t = decodeJwt(fallbackToken);
    if (t) {
      const realmRoles = (t.realm_access && t.realm_access.roles) || [];
      return {
        name: t.name || t.preferred_username || t.email || "User",
        username: t.preferred_username,
        email: t.email,
        roles: realmRoles,
        authenticated: true,
      };
    }
  }
  if (!keycloak || !authenticated || !keycloak.tokenParsed) {
    return guestUser();
  }
  const t = keycloak.tokenParsed;
  const realmRoles = (t.realm_access && t.realm_access.roles) || [];
  const clientRoles =
    (t.resource_access &&
      t.resource_access[KC_CLIENT_ID] &&
      t.resource_access[KC_CLIENT_ID].roles) ||
    [];
  return {
    name: t.name || t.preferred_username || t.email || "User",
    username: t.preferred_username,
    email: t.email,
    roles: [...new Set([...realmRoles, ...clientRoles])],
    authenticated: true,
  };
}

/** Current bearer token, or null if not authenticated. */
export function getToken() {
  if (keycloak && authenticated && keycloak.token) return keycloak.token;
  return fallbackToken;
}

/** Whether the current user is authenticated. */
export function isAuthenticated() {
  return authenticated || Boolean(fallbackToken);
}

/**
 * Password fallback login (#14): exchanges username/password for a token via the
 * backend proxy to Keycloak's direct-access grant. Returns true on success.
 */
export async function passwordLogin(username, password) {
  const base = import.meta.env.VITE_API_BASE_URL || "/api";
  const resp = await fetch(base + "/v1/auth/password-login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!resp.ok) {
    let detail = "Invalid username or password";
    try { detail = (await resp.json()).detail || detail; } catch { /* ignore */ }
    throw new Error(detail);
  }
  const body = await resp.json();
  fallbackToken = body.access_token || null;
  fallbackRefreshToken = body.refresh_token || null;
  if (fallbackToken) sessionStorage.setItem("pfm_fallback_token", fallbackToken);
  if (fallbackRefreshToken) sessionStorage.setItem("pfm_fallback_refresh", fallbackRefreshToken);
  return Boolean(fallbackToken);
}

/**
 * Silently renew the password-fallback session using the stored refresh token
 * (Session 742, Bug 3). Returns the new access token, or null if renewal failed
 * (in which case the fallback session is cleared so callers can prompt re-login).
 */
export async function refreshFallback() {
  if (!fallbackRefreshToken) return null;
  const base = import.meta.env.VITE_API_BASE_URL || "/api";
  try {
    const resp = await fetch(base + "/v1/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: fallbackRefreshToken }),
    });
    if (!resp.ok) throw new Error("refresh failed");
    const body = await resp.json();
    fallbackToken = body.access_token || null;
    fallbackRefreshToken = body.refresh_token || fallbackRefreshToken;
    if (fallbackToken) sessionStorage.setItem("pfm_fallback_token", fallbackToken);
    if (fallbackRefreshToken) sessionStorage.setItem("pfm_fallback_refresh", fallbackRefreshToken);
    return fallbackToken;
  } catch {
    clearFallbackSession();
    return null;
  }
}

/** Whether the current session is the password-fallback (vs Keycloak SSO) one. */
export function hasFallbackSession() {
  return Boolean(fallbackToken);
}

/** Clear the password-fallback session (in-memory + sessionStorage). */
export function clearFallbackSession() {
  fallbackToken = null;
  fallbackRefreshToken = null;
  sessionStorage.removeItem("pfm_fallback_token");
  sessionStorage.removeItem("pfm_fallback_refresh");
}

/** Redirect to the Keycloak login page. */
export function login() {
  if (keycloak) {
    keycloak.login({ redirectUri: window.location.href });
  }
}

/** Redirect to the Keycloak logout endpoint (or clear the fallback session). */
export function logout() {
  if (fallbackToken) {
    clearFallbackSession();
    window.location.reload();
    return;
  }
  if (keycloak) {
    keycloak.logout({ redirectUri: window.location.origin });
  }
}

export default {
  initAuth,
  getUser,
  getToken,
  isAuthenticated,
  login,
  logout,
  passwordLogin,
  refreshFallback,
  hasFallbackSession,
  clearFallbackSession,
};
