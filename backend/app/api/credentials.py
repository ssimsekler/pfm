"""Credentials Store API (Session 815, Item 19).

Exposes:
  - GET  /v1/credential-categories            list categories (+ their param schema)
  - GET  /v1/credentials                       list credentials (values masked)
  - POST /v1/credentials                       create a credential (dynamic values)
  - GET  /v1/credentials/{id}                  one credential (values masked)
  - PATCH/DELETE /v1/credentials/{id}          update/soft-delete

Sensitive parameter values (params with `sensitive: true`) are **masked** on read
(never returned in clear) and preserved on update when the client submits the mask
placeholder unchanged. `resolve_values()` returns the real (unmasked) values for
server-side consumers (e.g. the notification/SMTP sender).
"""

import uuid as uuid_lib

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import Principal, get_current_principal, require_write
from app.models.credentials import Credential, CredentialCategory
from app.services.repository import Repository

MASK = "********"

category_router = APIRouter(prefix="/api/v1/credential-categories", tags=["credentials"])
credential_router = APIRouter(prefix="/api/v1/credentials", tags=["credentials"])


# ---------------------------------------------------------------------------
# Categories (read-only from the UI; seeded/system-defined)
# ---------------------------------------------------------------------------
class CategoryOut(BaseModel):
    uuid: uuid_lib.UUID
    name: str
    category_key: str
    params: list | None = None

    class Config:
        from_attributes = True


@category_router.get("", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db), _: Principal = Depends(get_current_principal)):
    return list(db.execute(select(CredentialCategory).order_by(CredentialCategory.name)).scalars())


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------
class CredentialOut(BaseModel):
    uuid: uuid_lib.UUID
    mnemonic_id: str
    name: str
    category_id: uuid_lib.UUID
    category_key: str | None = None
    values: dict | None = None  # sensitive values masked

    class Config:
        from_attributes = True


class CredentialCreate(BaseModel):
    name: str
    category_id: uuid_lib.UUID
    values: dict | None = None


class CredentialUpdate(BaseModel):
    name: str | None = None
    values: dict | None = None


def _sensitive_keys(category: CredentialCategory | None) -> set[str]:
    keys: set[str] = set()
    for p in (category.params or []) if category else []:
        if isinstance(p, dict) and p.get("sensitive"):
            keys.add(p.get("key"))
    return {k for k in keys if k}


def _mask(values: dict | None, sensitive: set[str]) -> dict:
    out = dict(values or {})
    for k in sensitive:
        if out.get(k) not in (None, ""):
            out[k] = MASK
    return out


def _out(db: Session, cred: Credential) -> CredentialOut:
    cat = db.get(CredentialCategory, cred.category_id)
    return CredentialOut(
        uuid=cred.uuid, mnemonic_id=cred.mnemonic_id, name=cred.name,
        category_id=cred.category_id,
        category_key=cat.category_key if cat else None,
        values=_mask(cred.values, _sensitive_keys(cat)),
    )


def resolve_values(db: Session, ref: str | None) -> dict | None:
    """Return the **real** (unmasked) values for a credential referenced by its
    mnemonic_id or uuid. For server-side consumers (SMTP sender, etc.)."""
    if not ref:
        return None
    cred = db.execute(
        select(Credential).where(Credential.mnemonic_id == ref)
    ).scalar_one_or_none()
    if cred is None:
        try:
            cred = db.get(Credential, uuid_lib.UUID(str(ref)))
        except (ValueError, TypeError):
            cred = None
    return dict(cred.values or {}) if cred else None


@credential_router.get("", response_model=list[CredentialOut])
def list_credentials(db: Session = Depends(get_db), _: Principal = Depends(get_current_principal)):
    rows = db.execute(
        select(Credential).where(Credential.deleted_at.is_(None)).order_by(Credential.name)
    ).scalars()
    return [_out(db, c) for c in rows]


@credential_router.post("", response_model=CredentialOut, status_code=201)
def create_credential(
    payload: CredentialCreate,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_write),
):
    cat = db.get(CredentialCategory, payload.category_id)
    if cat is None:
        raise HTTPException(status_code=422, detail="unknown credential category")
    repo = Repository(Credential, entity_type="credential", event_domain="credential")
    cred = repo.create(db, {
        "name": payload.name,
        "category_id": payload.category_id,
        "values": payload.values or {},
    })
    return _out(db, cred)


@credential_router.get("/{cred_id}", response_model=CredentialOut)
def get_credential(cred_id: uuid_lib.UUID, db: Session = Depends(get_db), _: Principal = Depends(get_current_principal)):
    cred = db.get(Credential, cred_id)
    if cred is None:
        raise HTTPException(status_code=404, detail="credential not found")
    return _out(db, cred)


@credential_router.patch("/{cred_id}", response_model=CredentialOut)
def update_credential(
    cred_id: uuid_lib.UUID,
    payload: CredentialUpdate,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_write),
):
    cred = db.get(Credential, cred_id)
    if cred is None:
        raise HTTPException(status_code=404, detail="credential not found")
    if payload.name is not None:
        cred.name = payload.name
    if payload.values is not None:
        cat = db.get(CredentialCategory, cred.category_id)
        sensitive = _sensitive_keys(cat)
        merged = dict(cred.values or {})
        for k, v in payload.values.items():
            # Preserve the stored secret when the client submits the mask unchanged.
            if k in sensitive and v == MASK:
                continue
            merged[k] = v
        cred.values = merged
    db.commit()
    db.refresh(cred)
    # Batch 11: invalidate any cached OAuth2 tokens after a credential edit.
    try:
        from app.services.cred_auth import clear_token_cache
        clear_token_cache()
    except Exception:  # noqa: BLE001
        pass
    return _out(db, cred)


@credential_router.delete("/{cred_id}")
def delete_credential(cred_id: uuid_lib.UUID, db: Session = Depends(get_db), _: Principal = Depends(require_write)):
    cred = db.get(Credential, cred_id)
    if cred is None:
        raise HTTPException(status_code=404, detail="credential not found")
    from sqlalchemy import func as _func
    cred.deleted_at = _func.now()
    db.commit()
    return {"deleted": True, "uuid": str(cred_id)}


ALL_ROUTERS = [category_router, credential_router]