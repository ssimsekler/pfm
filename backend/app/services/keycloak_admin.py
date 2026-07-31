"""Keycloak Admin REST API client (Session 742, Batch 1 — Bug 2).

Provisions users and role grants in the app realm using master-realm admin
credentials. Kept dependency-free (httpx only). All calls raise
``KeycloakAdminError`` on failure so the API layer can surface a 422 with detail.

Token flow: obtain an access token from the **master** realm's token endpoint
using ``KEYCLOAK_ADMIN``/``KEYCLOAK_ADMIN_PASSWORD`` (password grant, client
``admin-cli``), then call the Admin REST API scoped to the configured app realm.
"""

from __future__ import annotations

import httpx

from app.core.config import get_settings

settings = get_settings()


class KeycloakAdminError(Exception):
    """Raised when a Keycloak Admin API call fails."""


def _base() -> str:
    return settings.keycloak_url.rstrip("/")


def _admin_token() -> str:
    """Obtain a master-realm admin access token (client ``admin-cli``)."""
    url = f"{_base()}/realms/master/protocol/openid-connect/token"
    data = {
        "grant_type": "password",
        "client_id": "admin-cli",
        "username": settings.keycloak_admin,
        "password": settings.keycloak_admin_password,
    }
    try:
        resp = httpx.post(url, data=data, timeout=10.0)
    except Exception as exc:  # noqa: BLE001
        raise KeycloakAdminError(f"Keycloak unreachable: {exc}") from exc
    if resp.status_code != 200:
        raise KeycloakAdminError(
            f"Admin login failed ({resp.status_code}). Check KEYCLOAK_ADMIN credentials."
        )
    return resp.json().get("access_token", "")


def _headers() -> dict:
    return {"Authorization": f"Bearer {_admin_token()}", "Content-Type": "application/json"}


def _realm_url(path: str) -> str:
    return f"{_base()}/admin/realms/{settings.keycloak_realm}{path}"


def find_user_by_username(username: str) -> dict | None:
    """Return the user representation for ``username`` or None."""
    try:
        resp = httpx.get(
            _realm_url("/users"),
            params={"username": username, "exact": "true"},
            headers=_headers(),
            timeout=10.0,
        )
    except KeycloakAdminError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise KeycloakAdminError(f"Keycloak lookup failed: {exc}") from exc
    if resp.status_code != 200:
        raise KeycloakAdminError(f"User lookup failed ({resp.status_code}).")
    rows = resp.json() or []
    return rows[0] if rows else None


def create_user(
    *,
    username: str,
    email: str | None,
    first_name: str | None = None,
    temporary_password: str | None = None,
) -> str:
    """Create an enabled realm user; optionally set a temporary password.

    Returns the new user's Keycloak ``id`` (subject). Raises if the username
    already exists.
    """
    headers = _headers()
    payload = {
        "username": username,
        "email": email or None,
        "firstName": first_name or None,
        "enabled": True,
        "emailVerified": bool(email),
    }
    if temporary_password:
        payload["credentials"] = [
            {"type": "password", "value": temporary_password, "temporary": True}
        ]
    try:
        resp = httpx.post(_realm_url("/users"), json=payload, headers=headers, timeout=10.0)
    except Exception as exc:  # noqa: BLE001
        raise KeycloakAdminError(f"Keycloak create failed: {exc}") from exc
    # If the username already exists, reconcile by returning the existing id so
    # the caller can link/mirror it instead of hard-failing (Session 815, Item 10).
    if resp.status_code == 409:
        existing = find_user_by_username(username)
        if existing is not None:
            return existing["id"]
        raise KeycloakAdminError(f"User '{username}' already exists in Keycloak.")
    if resp.status_code not in (201, 204):
        raise KeycloakAdminError(f"Create user failed ({resp.status_code}): {resp.text}")

    # Keycloak returns the new resource URL in the Location header.
    location = resp.headers.get("Location", "")
    if location:
        return location.rstrip("/").rsplit("/", 1)[-1]
    # Fallback: look it up.
    user = find_user_by_username(username)
    if user is None:
        raise KeycloakAdminError("User created but could not resolve its id.")
    return user["id"]


def set_user_enabled(user_id: str, enabled: bool) -> None:
    """Enable/disable a realm user (Session 815, Item 6 — deactivate/reactivate)."""
    try:
        resp = httpx.put(
            _realm_url(f"/users/{user_id}"),
            json={"enabled": bool(enabled)},
            headers=_headers(),
            timeout=10.0,
        )
    except Exception as exc:  # noqa: BLE001
        raise KeycloakAdminError(f"Set enabled failed: {exc}") from exc
    if resp.status_code not in (204, 200):
        raise KeycloakAdminError(f"Set enabled failed ({resp.status_code}).")


def delete_user(user_id: str) -> None:
    """Hard-delete a realm user (Session 815, Item 6). 404 is treated as success."""
    try:
        resp = httpx.delete(_realm_url(f"/users/{user_id}"), headers=_headers(), timeout=10.0)
    except Exception as exc:  # noqa: BLE001
        raise KeycloakAdminError(f"Delete user failed: {exc}") from exc
    if resp.status_code not in (204, 200, 404):
        raise KeycloakAdminError(f"Delete user failed ({resp.status_code}).")


def set_password(user_id: str, password: str, *, temporary: bool = True) -> None:
    """Reset a user's password (temporary by default → must change on first login)."""
    body = {"type": "password", "value": password, "temporary": temporary}
    try:
        resp = httpx.put(
            _realm_url(f"/users/{user_id}/reset-password"),
            json=body,
            headers=_headers(),
            timeout=10.0,
        )
    except Exception as exc:  # noqa: BLE001
        raise KeycloakAdminError(f"Set password failed: {exc}") from exc
    if resp.status_code not in (204, 200):
        raise KeycloakAdminError(f"Set password failed ({resp.status_code}).")


def _get_realm_role(role_name: str) -> dict:
    try:
        resp = httpx.get(_realm_url(f"/roles/{role_name}"), headers=_headers(), timeout=10.0)
    except Exception as exc:  # noqa: BLE001
        raise KeycloakAdminError(f"Role lookup failed: {exc}") from exc
    if resp.status_code != 200:
        raise KeycloakAdminError(f"Unknown realm role '{role_name}' ({resp.status_code}).")
    return resp.json()


def assign_realm_role(user_id: str, role_name: str) -> None:
    """Assign a realm role to a user (idempotent)."""
    role = _get_realm_role(role_name)
    body = [{"id": role["id"], "name": role["name"]}]
    try:
        resp = httpx.post(
            _realm_url(f"/users/{user_id}/role-mappings/realm"),
            json=body,
            headers=_headers(),
            timeout=10.0,
        )
    except Exception as exc:  # noqa: BLE001
        raise KeycloakAdminError(f"Assign role failed: {exc}") from exc
    if resp.status_code not in (204, 200):
        raise KeycloakAdminError(f"Assign role failed ({resp.status_code}).")


def remove_realm_role(user_id: str, role_name: str) -> None:
    """Remove a realm role from a user (idempotent)."""
    role = _get_realm_role(role_name)
    body = [{"id": role["id"], "name": role["name"]}]
    try:
        resp = httpx.request(
            "DELETE",
            _realm_url(f"/users/{user_id}/role-mappings/realm"),
            json=body,
            headers=_headers(),
            timeout=10.0,
        )
    except Exception as exc:  # noqa: BLE001
        raise KeycloakAdminError(f"Remove role failed: {exc}") from exc
    if resp.status_code not in (204, 200):
        raise KeycloakAdminError(f"Remove role failed ({resp.status_code}).")


def refresh_token(refresh_tok: str) -> dict:
    """Exchange a refresh token for a new access token (app realm, frontend client)."""
    url = f"{_base()}/realms/{settings.keycloak_realm}/protocol/openid-connect/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": settings.keycloak_client_id,
        "refresh_token": refresh_tok,
    }
    try:
        resp = httpx.post(url, data=data, timeout=10.0)
    except Exception as exc:  # noqa: BLE001
        raise KeycloakAdminError(f"Keycloak unreachable: {exc}") from exc
    if resp.status_code != 200:
        raise KeycloakAdminError("Refresh failed")
    return resp.json()