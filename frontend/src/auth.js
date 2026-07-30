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

function guestUser() {
  return { name: "Guest", roles: [], authenticated: false };
}

/**
 * Initialize Keycloak. Uses `check-sso` so the app can load for anonymous
 * users without forcing a login redirect. If Keycloak is unreachable (e.g.
 * the realm hasn't been imported yet in a fresh dev environment) we fail
 * soft and continue as a guest so the UI still renders.
 */
export async function initAuth() {
  try {
    keycloak = new Keycloak({
      url: KC_URL,
      realm: KC_REALM,
      clientId: KC_CLIENT_ID,
    });

    authenticated = await keycloak.init({
      onLoad: "check-sso",
      pkceMethod: "S256",
      checkLoginIframe: false,
      silentCheckSsoRedirectUri: window.location.origin + "/silent-check-sso.html",
    });

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
  }
  return authenticated;
}

/** Current user profile derived from the Keycloak token. */
export function getUser() {
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
  return keycloak && authenticated ? keycloak.token || null : null;
}

/** Whether the current user is authenticated. */
export function isAuthenticated() {
  return authenticated;
}

/** Redirect to the Keycloak login page. */
export function login() {
  if (keycloak) {
    keycloak.login({ redirectUri: window.location.href });
  }
}

/** Redirect to the Keycloak logout endpoint. */
export function logout() {
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
};