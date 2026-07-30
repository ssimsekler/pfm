"""Admin & settings API (Phase 11 Batch 3):
  - app_config key/value CRUD (A.7) incl. the LLM master switch
  - id_sequence (entity mnemonic prefixes) list/update
  - current-user profile get/update (name/email + display format prefs)

These power the App Settings, Entity Prefixes, and My Profile screens.
"""

import uuid as uuid_lib

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import Principal, get_current_principal, require_write
from app.models.meta import AppConfig, IdSequence
from app.models.security import AppUser, Role, UserRole

settings = get_settings()

# ---------------------------------------------------------------------------
# App config (key/value settings)
# ---------------------------------------------------------------------------
app_config_router = APIRouter(prefix="/api/v1/app-config", tags=["app-config"])


class AppConfigOut(BaseModel):
    key: str
    value: object | None = None
    value_type: str
    description: str | None = None

    class Config:
        from_attributes = True


class AppConfigUpsert(BaseModel):
    value: object | None = None
    value_type: str | None = None
    description: str | None = None


@app_config_router.get("", response_model=list[AppConfigOut])
def list_config(db: Session = Depends(get_db), _: Principal = Depends(get_current_principal)):
    return list(db.execute(select(AppConfig).order_by(AppConfig.key)).scalars())


@app_config_router.put("/{key}", response_model=AppConfigOut)
def upsert_config(
    key: str,
    payload: AppConfigUpsert,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_write),
):
    row = db.get(AppConfig, key)
    if row is None:
        row = AppConfig(key=key, value_type=payload.value_type or "string")
        db.add(row)
    if payload.value is not None:
        row.value = payload.value
    if payload.value_type is not None:
        row.value_type = payload.value_type
    if payload.description is not None:
        row.description = payload.description
    db.commit()
    db.refresh(row)
    return row


# ---------------------------------------------------------------------------
# Entity prefixes (id_sequence)
# ---------------------------------------------------------------------------
prefix_router = APIRouter(prefix="/api/v1/id-sequences", tags=["id-sequences"])


class IdSequenceOut(BaseModel):
    prefix: str
    entity_type: str
    pad_width: int
    current_seq: int

    class Config:
        from_attributes = True


class IdSequenceUpdate(BaseModel):
    pad_width: int | None = None


@prefix_router.get("", response_model=list[IdSequenceOut])
def list_prefixes(db: Session = Depends(get_db), _: Principal = Depends(get_current_principal)):
    return list(db.execute(select(IdSequence).order_by(IdSequence.entity_type)).scalars())


@prefix_router.patch("/{prefix}", response_model=IdSequenceOut)
def update_prefix(
    prefix: str,
    payload: IdSequenceUpdate,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_write),
):
    row = db.get(IdSequence, prefix)
    if row is None:
        raise HTTPException(status_code=404, detail="prefix not found")
    if payload.pad_width is not None:
        if payload.pad_width < 1 or payload.pad_width > 18:
            raise HTTPException(status_code=422, detail="pad_width must be 1..18")
        row.pad_width = payload.pad_width
    db.commit()
    db.refresh(row)
    return row


# ---------------------------------------------------------------------------
# Current-user profile
# ---------------------------------------------------------------------------
profile_router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


class ProfileOut(BaseModel):
    uuid: uuid_lib.UUID | None = None
    username: str | None = None
    name: str | None = None
    email: str | None = None
    base_currency: str | None = None
    date_format: str | None = None
    number_format: str | None = None
    time_format: str | None = None

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    base_currency: str | None = None
    date_format: str | None = None
    number_format: str | None = None
    time_format: str | None = None


def _get_or_create_user(db: Session, principal: Principal) -> AppUser:
    """Resolve (or lazily create) the app_user row for the caller."""
    user = None
    if principal.subject and principal.subject not in (None, "dev-user"):
        try:
            user = db.get(AppUser, uuid_lib.UUID(principal.subject))
        except (ValueError, TypeError):
            user = None
    if user is None and principal.username:
        user = db.execute(
            select(AppUser).where(AppUser.email == (principal.email or ""))
        ).scalar_one_or_none()
    return user


@profile_router.get("", response_model=ProfileOut)
def get_profile(db: Session = Depends(get_db), principal: Principal = Depends(get_current_principal)):
    user = _get_or_create_user(db, principal)
    if user is None:
        # No persisted row yet — return the token-derived identity.
        return ProfileOut(username=principal.username, name=principal.username, email=principal.email)
    return ProfileOut(
        uuid=user.uuid, username=principal.username, name=user.name, email=user.email,
        base_currency=user.base_currency,
        date_format=getattr(user, "date_format", None),
        number_format=getattr(user, "number_format", None),
        time_format=getattr(user, "time_format", None),
    )


@profile_router.put("", response_model=ProfileOut)
def update_profile(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_write),
):
    user = _get_or_create_user(db, principal)
    if user is None:
        raise HTTPException(status_code=404, detail="No user profile row for the current identity yet.")
    for field in ["name", "email", "base_currency", "date_format", "number_format", "time_format"]:
        val = getattr(payload, field)
        if val is not None and hasattr(user, field):
            setattr(user, field, val)
    db.commit()
    db.refresh(user)
    return get_profile(db, principal)


# ---------------------------------------------------------------------------
# Users admin (local app_user / role / user_role mirror) — #14
# ---------------------------------------------------------------------------
users_router = APIRouter(prefix="/api/v1/users", tags=["users"])


class UserOut(BaseModel):
    uuid: uuid_lib.UUID
    name: str | None = None
    email: str | None = None
    base_currency: str | None = None
    roles: list[str] = []

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    name: str
    email: str | None = None
    base_currency: str | None = None
    role: str | None = None  # optional role name to grant


class UserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    base_currency: str | None = None


def _roles_for(db: Session, user_id: uuid_lib.UUID) -> list[str]:
    rows = db.execute(
        select(Role.name).join(UserRole, UserRole.role_id == Role.uuid).where(UserRole.user_id == user_id)
    ).scalars()
    return [r for r in rows if r]


def _user_out(db: Session, user: AppUser) -> UserOut:
    return UserOut(
        uuid=user.uuid, name=user.name, email=user.email,
        base_currency=user.base_currency, roles=_roles_for(db, user.uuid),
    )


@users_router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: Principal = Depends(get_current_principal)):
    users = db.execute(select(AppUser).where(AppUser.deleted_at.is_(None)).order_by(AppUser.name)).scalars()
    return [_user_out(db, u) for u in users]


@users_router.post("", response_model=UserOut, status_code=201)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_write),
):
    from app.services.repository import Repository

    repo = Repository(AppUser, entity_type="app_user", event_domain="app_user")
    user = repo.create(db, {"name": payload.name, "email": payload.email, "base_currency": payload.base_currency})
    if payload.role:
        _grant_role(db, user.uuid, payload.role)
    db.commit()
    db.refresh(user)
    return _user_out(db, user)


@users_router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: uuid_lib.UUID,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_write),
):
    user = db.get(AppUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    for field in ["name", "email", "base_currency"]:
        val = getattr(payload, field)
        if val is not None:
            setattr(user, field, val)
    db.commit()
    db.refresh(user)
    return _user_out(db, user)


class RoleGrant(BaseModel):
    role: str


def _grant_role(db: Session, user_id: uuid_lib.UUID, role_name: str) -> None:
    role = db.execute(select(Role).where(Role.name == role_name)).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=422, detail=f"unknown role: {role_name}")
    existing = db.execute(
        select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role.uuid)
    ).scalar_one_or_none()
    if existing is None:
        db.add(UserRole(user_id=user_id, role_id=role.uuid, grant_household_id=role.uuid))


@users_router.post("/{user_id}/roles", response_model=UserOut)
def grant_role(
    user_id: uuid_lib.UUID,
    payload: RoleGrant,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_write),
):
    user = db.get(AppUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    _grant_role(db, user_id, payload.role)
    db.commit()
    return _user_out(db, user)


@users_router.delete("/{user_id}/roles/{role_name}", response_model=UserOut)
def revoke_role(
    user_id: uuid_lib.UUID,
    role_name: str,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_write),
):
    user = db.get(AppUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    role = db.execute(select(Role).where(Role.name == role_name)).scalar_one_or_none()
    if role is not None:
        link = db.execute(
            select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role.uuid)
        ).scalar_one_or_none()
        if link is not None:
            db.delete(link)
            db.commit()
    return _user_out(db, user)


# ---------------------------------------------------------------------------
# Password-login fallback (#14): proxy Keycloak's direct-access grant so the SPA
# can sign in with username/password when the redirect flow isn't convenient.
# ---------------------------------------------------------------------------
auth_router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class PasswordLoginIn(BaseModel):
    username: str
    password: str


@auth_router.post("/password-login")
def password_login(payload: PasswordLoginIn):
    token_url = (
        f"{settings.keycloak_url}/realms/{settings.keycloak_realm}"
        "/protocol/openid-connect/token"
    )
    data = {
        "grant_type": "password",
        "client_id": settings.keycloak_client_id,
        "username": payload.username,
        "password": payload.password,
    }
    try:
        resp = httpx.post(token_url, data=data, timeout=10.0)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Auth server unreachable: {exc}") from exc
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    body = resp.json()
    return {
        "access_token": body.get("access_token"),
        "refresh_token": body.get("refresh_token"),
        "expires_in": body.get("expires_in"),
        "token_type": body.get("token_type", "Bearer"),
    }


ALL_ROUTERS = [app_config_router, prefix_router, profile_router, users_router, auth_router]
