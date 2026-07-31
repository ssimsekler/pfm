"""Keycloak-independent local admin authentication (Session 815, Batch 9).

Provides an always-available **local admin** login that does NOT depend on
Keycloak, so the app is usable even when Keycloak is down or a realm hasn't been
imported yet. The credential is stored (hashed) in `app_config` under
`auth.local_admin`, seeded from the `LOCAL_ADMIN_USERNAME`/`LOCAL_ADMIN_PASSWORD`
env vars on first run. We issue our **own HS256 session JWT** (signed with
`BACKEND_SECRET_KEY`) that `core.security.get_current_principal` accepts.

Password hashing uses stdlib PBKDF2-HMAC-SHA256 (no extra dependency).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Optional

from jose import jwt
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.meta import AppConfig

settings = get_settings()

_CONFIG_KEY = "auth.local_admin"
_PBKDF2_ITERATIONS = 200_000
# Local-admin session token lifetime (seconds). Kept modest; the SPA can
# re-login. 12h is convenient for a single-user desktop-style deployment.
_TOKEN_TTL_SECONDS = 12 * 3600
# Marker so we can distinguish our locally-issued tokens from Keycloak's.
LOCAL_ISSUER = "pfm-local"
LOCAL_ADMIN_ROLE = "Admin"


def _hash_password(password: str, *, salt: Optional[str] = None,
                   iterations: int = _PBKDF2_ITERATIONS) -> dict:
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), iterations
    )
    return {"salt": salt, "hash": dk.hex(), "iterations": iterations}


def _verify_password(password: str, stored: dict) -> bool:
    try:
        calc = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(stored["salt"]),
            int(stored.get("iterations", _PBKDF2_ITERATIONS)),
        ).hex()
        return hmac.compare_digest(calc, stored.get("hash", ""))
    except Exception:  # noqa: BLE001
        return False


def _load(db: Session) -> Optional[dict]:
    row = db.get(AppConfig, _CONFIG_KEY)
    if row is None or row.value is None:
        return None
    val = row.value
    if isinstance(val, str):
        try:
            val = json.loads(val)
        except Exception:  # noqa: BLE001
            return None
    return val


def _store(db: Session, data: dict) -> None:
    row = db.get(AppConfig, _CONFIG_KEY)
    if row is None:
        row = AppConfig(key=_CONFIG_KEY, value_type="json",
                        description="Local admin credential (hashed).")
        db.add(row)
    row.value = data
    row.value_type = "json"
    db.commit()


def ensure_seeded(db: Session) -> None:
    """Seed the local admin credential on first run (idempotent)."""
    if _load(db) is not None:
        return
    username = os.environ.get("LOCAL_ADMIN_USERNAME", "admin")
    password = os.environ.get("LOCAL_ADMIN_PASSWORD", "admin")
    data = {"username": username, **_hash_password(password)}
    _store(db, data)


def verify(db: Session, username: str, password: str) -> bool:
    data = _load(db)
    if not data:
        return False
    if (username or "").strip().lower() != str(data.get("username", "")).lower():
        return False
    return _verify_password(password, data)


def change_password(db: Session, username: str, old_password: str,
                    new_password: str) -> bool:
    """Change the local admin password after verifying the old one."""
    data = _load(db)
    if not data:
        return False
    if (username or "").strip().lower() != str(data.get("username", "")).lower():
        return False
    if not _verify_password(old_password, data):
        return False
    new_data = {"username": data["username"], **_hash_password(new_password)}
    _store(db, new_data)
    return True


def set_password(db: Session, new_password: str) -> None:
    """Force-set the local admin password (admin reset / no old-password check)."""
    data = _load(db) or {"username": os.environ.get("LOCAL_ADMIN_USERNAME", "admin")}
    new_data = {"username": data["username"], **_hash_password(new_password)}
    _store(db, new_data)


def get_username(db: Session) -> str:
    data = _load(db)
    return (data or {}).get("username", "admin")


def issue_token(username: str) -> dict:
    """Issue an HS256 session token for the local admin (accepted by security._decode)."""
    now = int(time.time())
    claims = {
        "iss": LOCAL_ISSUER,
        "sub": f"local:{username}",
        "preferred_username": username,
        "email": None,
        "realm_access": {"roles": [LOCAL_ADMIN_ROLE]},
        "iat": now,
        "exp": now + _TOKEN_TTL_SECONDS,
        "typ": "Bearer",
    }
    token = jwt.encode(claims, settings.backend_secret_key, algorithm="HS256")
    return {
        "access_token": token,
        "refresh_token": token,  # local tokens are long-lived; reuse as refresh
        "expires_in": _TOKEN_TTL_SECONDS,
        "token_type": "Bearer",
    }