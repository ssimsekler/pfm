"""Admin & settings API (Phase 11 Batch 3):
  - app_config key/value CRUD (A.7) incl. the LLM master switch
  - id_sequence (entity mnemonic prefixes) list/update
  - current-user profile get/update (name/email + display format prefs)

These power the App Settings, Entity Prefixes, and My Profile screens.
"""

import secrets
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
from app.services import keycloak_admin

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
    # Item 8: time locale (blank → browser default). Item 5: high-precision decimals.
    time_locale: str | None = None
    amount_decimals: int | None = None

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    base_currency: str | None = None
    date_format: str | None = None
    number_format: str | None = None
    time_format: str | None = None
    time_locale: str | None = None
    amount_decimals: int | None = None


def _get_or_create_user(db: Session, principal: Principal) -> AppUser | None:
    """Resolve (or lazily create) the app_user row for the caller.

    Resolution order (Session 742, Bug 1):
      1. by keycloak_subject == principal.subject
      2. by app_user.uuid == principal.subject (legacy: uuid == sub)
      3. by email
    If still not found and we have a real (non-dev) identity, **create** a row so
    profile save/read never 404s for a signed-in user.
    """
    subject = principal.subject if principal.subject not in (None, "dev-user") else None
    user = None

    if subject:
        user = db.execute(
            select(AppUser).where(AppUser.keycloak_subject == subject)
        ).scalar_one_or_none()
        if user is None:
            try:
                user = db.get(AppUser, uuid_lib.UUID(subject))
            except (ValueError, TypeError):
                user = None

    if user is None and principal.email:
        user = db.execute(
            select(AppUser).where(AppUser.email == principal.email)
        ).scalar_one_or_none()

    if user is None and (subject or principal.username):
        # Auto-provision a local mirror for the signed-in identity.
        from app.services.repository import Repository

        repo = Repository(AppUser, entity_type="app_user", event_domain="app_user")
        user = repo.create(
            db,
            {
                "name": principal.username or principal.email or "User",
                "email": principal.email,
                "keycloak_subject": subject,
                "username": principal.username,
            },
        )
        db.commit()
        db.refresh(user)

    # Backfill the subject link and username if we matched by email/uuid but
    # hadn't stored them yet (Item 12: keep username consistent everywhere).
    changed = False
    if user is not None and subject and not getattr(user, "keycloak_subject", None):
        user.keycloak_subject = subject
        changed = True
    if user is not None and principal.username and not getattr(user, "username", None):
        user.username = principal.username
        changed = True
    if changed:
        db.commit()
        db.refresh(user)

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
        time_locale=getattr(user, "time_locale", None),
        amount_decimals=getattr(user, "amount_decimals", None),
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
    for field in ["name", "email", "base_currency", "date_format", "number_format",
                  "time_format", "time_locale", "amount_decimals"]:
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
    username: str | None = None
    name: str | None = None
    email: str | None = None
    base_currency: str | None = None
    active: bool = True
    roles: list[str] = []
    # Only populated on create when a temporary password was generated (shown once).
    temp_password: str | None = None

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    username: str
    name: str | None = None
    email: str | None = None
    base_currency: str | None = None
    role: str | None = None  # optional realm role to grant
    password: str | None = None  # optional; a random temp password is generated if omitted


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
        uuid=user.uuid,
        username=getattr(user, "username", None),
        name=user.name, email=user.email,
        base_currency=user.base_currency,
        active=user.deleted_at is None,
        roles=_roles_for(db, user.uuid),
    )


@users_router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
    include_inactive: bool = False,
):
    stmt = select(AppUser)
    if not include_inactive:
        stmt = stmt.where(AppUser.deleted_at.is_(None))
    users = db.execute(stmt.order_by(AppUser.name)).scalars()
    return [_user_out(db, u) for u in users]


@users_router.post("", response_model=UserOut, status_code=201)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_write),
):
    """Provision a Keycloak user (full identity), then mirror locally (Session 742, Bug 2).

    - Creates the Keycloak user with a temporary password (generated if not supplied).
    - Assigns the requested realm role in Keycloak.
    - Mirrors an `app_user` row keyed by the Keycloak subject for local display/roles.
    Returns the temporary password once so the admin can hand it over.
    """
    from app.services.repository import Repository

    username = (payload.username or "").strip()
    if len(username) < 3:
        raise HTTPException(status_code=422, detail="Username must be at least 3 characters.")

    temp_password = payload.password or secrets.token_urlsafe(9)

    # 1) Keycloak provisioning (surface failures as 422 with detail). create_user
    #    reconciles an existing username by returning its subject (Item 10), so a
    #    retry after a partial failure no longer dead-ends on 409.
    try:
        subject = keycloak_admin.create_user(
            username=username,
            email=payload.email,
            first_name=payload.name,
            temporary_password=temp_password,
        )
        # Ensure the password is set even when the user already existed.
        keycloak_admin.set_password(subject, temp_password, temporary=True)
        if payload.role:
            keycloak_admin.assign_realm_role(subject, payload.role)
    except keycloak_admin.KeycloakAdminError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # 2) Local mirror (keyed by the Keycloak subject) — idempotent: if a row for
    #    this subject already exists (from a prior partial run), reuse it instead
    #    of creating a duplicate. All committed in one unit (Item 10).
    try:
        user = db.execute(
            select(AppUser).where(AppUser.keycloak_subject == subject)
        ).scalar_one_or_none()
        if user is None:
            repo = Repository(AppUser, entity_type="app_user", event_domain="app_user")
            user = repo.create(
                db,
                {
                    "name": payload.name or username,
                    "email": payload.email,
                    "base_currency": payload.base_currency,
                    "keycloak_subject": subject,
                    "username": username,
                },
            )
        else:
            # Reactivate + refresh details on an existing mirror.
            user.deleted_at = None
            user.username = username
            if payload.name:
                user.name = payload.name
            if payload.email:
                user.email = payload.email
        if payload.role:
            _grant_role(db, user.uuid, payload.role)
        db.commit()
        db.refresh(user)
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(status_code=422, detail=f"Local mirror failed: {exc}") from exc

    out = _user_out(db, user)
    out.temp_password = temp_password
    return out


# --- Deactivate / reactivate / delete (Session 815, Item 6) ------------------
@users_router.post("/{user_id}/deactivate", response_model=UserOut)
def deactivate_user(
    user_id: uuid_lib.UUID,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_write),
):
    """Soft-deactivate: disable in Keycloak (enabled=false) + soft-delete locally."""
    user = db.get(AppUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    if getattr(user, "keycloak_subject", None):
        try:
            keycloak_admin.set_user_enabled(user.keycloak_subject, False)
        except keycloak_admin.KeycloakAdminError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    from sqlalchemy import func as _func
    user.deleted_at = _func.now()
    db.commit()
    db.refresh(user)
    return _user_out(db, user)


@users_router.post("/{user_id}/reactivate", response_model=UserOut)
def reactivate_user(
    user_id: uuid_lib.UUID,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_write),
):
    """Re-enable in Keycloak + clear the local soft-delete."""
    user = db.get(AppUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    if getattr(user, "keycloak_subject", None):
        try:
            keycloak_admin.set_user_enabled(user.keycloak_subject, True)
        except keycloak_admin.KeycloakAdminError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    user.deleted_at = None
    db.commit()
    db.refresh(user)
    return _user_out(db, user)


@users_router.delete("/{user_id}")
def delete_user(
    user_id: uuid_lib.UUID,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_write),
):
    """Hard-delete the Keycloak user + remove the local mirror and its role links."""
    user = db.get(AppUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    if getattr(user, "keycloak_subject", None):
        try:
            keycloak_admin.delete_user(user.keycloak_subject)
        except keycloak_admin.KeycloakAdminError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    # Remove role links, then the mirror row.
    for link in db.execute(select(UserRole).where(UserRole.user_id == user_id)).scalars().all():
        db.delete(link)
    db.delete(user)
    db.commit()
    return {"deleted": True, "uuid": str(user_id)}


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
    """Add a local user_role link (idempotent). `grant_household_id` is nullable now."""
    role = db.execute(select(Role).where(Role.name == role_name)).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=422, detail=f"unknown role: {role_name}")
    existing = db.execute(
        select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role.uuid)
    ).scalar_one_or_none()
    if existing is None:
        db.add(UserRole(user_id=user_id, role_id=role.uuid, grant_household_id=None))


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
    # Mirror the grant in Keycloak when the user is linked to a subject.
    if getattr(user, "keycloak_subject", None):
        try:
            keycloak_admin.assign_realm_role(user.keycloak_subject, payload.role)
        except keycloak_admin.KeycloakAdminError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
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
    # Mirror the revoke in Keycloak when the user is linked to a subject.
    if getattr(user, "keycloak_subject", None):
        try:
            keycloak_admin.remove_realm_role(user.keycloak_subject, role_name)
        except keycloak_admin.KeycloakAdminError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
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


class RefreshIn(BaseModel):
    refresh_token: str


@auth_router.post("/refresh")
def refresh_session(payload: RefreshIn):
    """Exchange a refresh token for a fresh access token (Session 742, Bug 3).

    Lets the SPA silently renew the password-fallback session so the app doesn't
    cascade 401s once the short-lived access token expires.
    """
    try:
        body = keycloak_admin.refresh_token(payload.refresh_token)
    except keycloak_admin.KeycloakAdminError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return {
        "access_token": body.get("access_token"),
        "refresh_token": body.get("refresh_token"),
        "expires_in": body.get("expires_in"),
        "token_type": body.get("token_type", "Bearer"),
    }


ALL_ROUTERS = [app_config_router, prefix_router, profile_router, users_router, auth_router]
