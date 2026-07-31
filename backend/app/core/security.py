"""Authentication & RBAC via Keycloak OIDC (Decision #3).

Validates bearer tokens against the Keycloak realm JWKS. In dev, if Keycloak is
unreachable or no token is supplied, a permissive fallback identity is used so the
app remains usable while the realm is being set up. Production should set
`auth_required=True` semantics by supplying valid tokens.
"""

from dataclasses import dataclass, field
from functools import lru_cache

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt

from app.core.config import get_settings

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)

# Session 815, Item 6: the top role is now "Admin" (was "Owner"). "Owner" is kept
# in the write set for backward compatibility with any not-yet-migrated tokens.
ROLE_ADMIN = "Admin"
ROLE_OWNER = "Owner"  # legacy alias
ROLE_EDITOR = "Editor"
ROLE_VIEWER = "Viewer"
WRITE_ROLES = {ROLE_ADMIN, ROLE_OWNER, ROLE_EDITOR}


@dataclass
class Principal:
    subject: str
    username: str | None = None
    email: str | None = None
    roles: set[str] = field(default_factory=set)

    @property
    def can_write(self) -> bool:
        # Permissive default when no roles are present (single-user/dev).
        return not self.roles or bool(self.roles & WRITE_ROLES)


@lru_cache
def _jwks_url() -> str:
    return f"{settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/certs"


@lru_cache
def _get_jwks() -> dict | None:
    try:
        resp = httpx.get(_jwks_url(), timeout=5.0)
        resp.raise_for_status()
        return resp.json()
    except Exception:  # noqa: BLE001
        return None


def _decode(token: str) -> dict:
    jwks = _get_jwks()
    if jwks is None:
        # Cannot verify signature (Keycloak not reachable) — decode without verify (dev).
        return jwt.get_unverified_claims(token)
    return jwt.decode(
        token,
        jwks,
        algorithms=["RS256"],
        options={"verify_aud": False},
    )


def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> Principal:
    """Resolve the caller. Dev-friendly fallback when no token is provided."""
    if credentials is None or not credentials.credentials:
        return Principal(subject="dev-user", username="dev", roles=set())
    try:
        claims = _decode(credentials.credentials)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        ) from exc
    realm_roles = set(claims.get("realm_access", {}).get("roles", []))
    return Principal(
        subject=claims.get("sub", "unknown"),
        username=claims.get("preferred_username"),
        email=claims.get("email"),
        roles=realm_roles,
    )


def require_write(principal: Principal = Depends(get_current_principal)) -> Principal:
    """Dependency guarding create/update/delete endpoints (Owner/Editor)."""
    if not principal.can_write:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access requires Owner or Editor role.",
        )
    return principal