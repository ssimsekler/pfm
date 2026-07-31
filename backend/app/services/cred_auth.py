"""Runtime credential consumption (Session 815, Batch 11).

Turns a stored Credentials Store entry (referenced by mnemonic_id/uuid) into the
concrete auth to attach to an outbound HTTP call:

  - api_key       → a request header (default Authorization) or a query param
  - basic_auth    → HTTP Basic (httpx auth tuple)
  - bearer_token  → Authorization: Bearer <token>
  - oauth2        → performs the grant at call time (client_credentials / password
                    / refresh_token), CACHES the access token until ~expiry, and
                    attaches Authorization: Bearer <access_token>
  - llm_provider  → api_key (+ optional base_url override) for LLM calls

Usage:
    auth = build_auth(db, credentials_ref)
    resp = httpx.get(url, headers={**auth.headers}, params={**auth.params},
                     auth=auth.basic, follow_redirects=True)

OAuth2 tokens are cached in-process keyed by the credential id + a hash of its
token parameters, so a config change invalidates the cache.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from app.api.credentials import resolve_values
from app.models.credentials import Credential, CredentialCategory


@dataclass
class AppliedAuth:
    headers: dict = field(default_factory=dict)
    params: dict = field(default_factory=dict)
    basic: Optional[tuple] = None          # (username, password) for httpx auth=
    base_url: Optional[str] = None         # llm_provider base_url override
    api_key: Optional[str] = None          # raw key (llm_provider convenience)


# --- OAuth2 token cache -----------------------------------------------------
# key -> (access_token, expires_at_epoch)
_TOKEN_CACHE: dict[str, tuple[str, float]] = {}


def _cache_key(ref: str, vals: dict) -> str:
    material = "|".join(
        str(vals.get(k, "")) for k in
        ("grant_type", "token_url", "client_id", "client_secret", "scope",
         "username", "password", "refresh_token", "audience")
    )
    return f"{ref}:{hashlib.sha256(material.encode()).hexdigest()}"


def _category_key(db: Session, cred: Credential) -> str | None:
    cat = db.get(CredentialCategory, cred.category_id)
    return cat.category_key if cat else None


def _find_credential(db: Session, ref: str) -> Credential | None:
    import uuid as _uuid
    from sqlalchemy import select

    cred = db.execute(
        select(Credential).where(Credential.mnemonic_id == ref)
    ).scalar_one_or_none()
    if cred is None:
        try:
            cred = db.get(Credential, _uuid.UUID(str(ref)))
        except (ValueError, TypeError):
            cred = None
    return cred


def _oauth2_token(ref: str, vals: dict) -> str | None:
    """Acquire (and cache) an OAuth2 access token for the stored parameters."""
    now = time.time()
    key = _cache_key(ref, vals)
    cached = _TOKEN_CACHE.get(key)
    if cached and cached[1] - 30 > now:  # 30s safety margin
        return cached[0]

    token_url = vals.get("token_url")
    if not token_url:
        return None
    grant = (vals.get("grant_type") or "client_credentials").strip()
    data = {"grant_type": grant}
    if vals.get("scope"):
        data["scope"] = vals["scope"]
    if vals.get("audience"):
        data["audience"] = vals["audience"]

    headers = {"Accept": "application/json"}
    client_id = vals.get("client_id")
    client_secret = vals.get("client_secret") or ""
    auth = None

    if grant == "client_credentials":
        # Prefer HTTP Basic client auth; fall back to body params.
        if client_id:
            auth = (client_id, client_secret)
    elif grant == "password":
        data["username"] = vals.get("username", "")
        data["password"] = vals.get("password", "")
        if client_id:
            data["client_id"] = client_id
            if client_secret:
                data["client_secret"] = client_secret
    elif grant == "refresh_token":
        data["refresh_token"] = vals.get("refresh_token", "")
        if client_id:
            data["client_id"] = client_id
            if client_secret:
                data["client_secret"] = client_secret
    else:
        # Unknown/interactive grant (authorization_code) — cannot run headless.
        return None

    try:
        resp = httpx.post(token_url, data=data, headers=headers, auth=auth,
                          timeout=15.0, follow_redirects=True)
        if resp.status_code != 200:
            return None
        body = resp.json()
    except Exception:  # noqa: BLE001
        return None

    access = body.get("access_token")
    if not access:
        return None
    expires_in = body.get("expires_in")
    try:
        ttl = int(expires_in) if expires_in is not None else 300
    except (TypeError, ValueError):
        ttl = 300
    _TOKEN_CACHE[key] = (access, now + ttl)
    return access


def build_auth(db: Session, ref: str | None) -> AppliedAuth:
    """Resolve a credentials_ref into applied auth. Returns an empty AppliedAuth
    when ref is blank or the credential can't be resolved (call proceeds
    unauthenticated)."""
    out = AppliedAuth()
    if not ref:
        return out
    cred = _find_credential(db, ref)
    if cred is None:
        return out
    vals = resolve_values(db, ref) or {}  # unmasked values
    kind = _category_key(db, cred)

    if kind == "api_key":
        key = vals.get("api_key")
        if key:
            header = (vals.get("header_name") or "Authorization").strip()
            qp = (vals.get("query_param") or "").strip()
            if qp:
                out.params[qp] = key
            else:
                # If using Authorization without a scheme, send as-is; many APIs
                # expect a raw key or "Bearer <key>". We send the raw key under
                # the chosen header (Authorization by default).
                out.headers[header] = key
    elif kind == "basic_auth":
        u, p = vals.get("username"), vals.get("password")
        if u is not None:
            out.basic = (u, p or "")
    elif kind == "bearer_token":
        tok = vals.get("token")
        if tok:
            out.headers["Authorization"] = f"Bearer {tok}"
    elif kind == "oauth2":
        access = _oauth2_token(ref, vals)
        if access:
            out.headers["Authorization"] = f"Bearer {access}"
    elif kind == "llm_provider":
        out.api_key = vals.get("api_key")
        if vals.get("base_url"):
            out.base_url = str(vals["base_url"]).rstrip("/")
        if out.api_key:
            out.headers["Authorization"] = f"Bearer {out.api_key}"
    return out


def clear_token_cache() -> None:
    """Drop all cached OAuth2 tokens (e.g. after a credential edit)."""
    _TOKEN_CACHE.clear()