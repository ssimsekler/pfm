"""Generic CRUD router factory built on the Repository (Decision #25).

Produces standard endpoints for an entity:
  GET    /{base}            list (search, filters, sort, pagination)
  POST   /{base}            create
  GET    /{base}/{uuid}     retrieve
  PATCH  /{base}/{uuid}     update
  DELETE /{base}/{uuid}     soft delete

Write endpoints require Owner/Editor (RBAC). All state changes emit CloudEvents
and write audit entries via the Repository.
"""

import uuid as uuid_lib
from typing import Any, Type

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import DeleteResult, PageOut
from app.core.database import get_db
from app.core.security import Principal, get_current_principal, require_write
from app.models.base import BaseEntity
from app.services.repository import Repository

# Server-managed audit columns — never accepted from the client payload (Item 7).
_AUDIT_FIELDS = {"created_at", "created_by", "updated_at", "updated_by", "deleted_at"}


def resolve_actor(db: Session, principal: Principal) -> uuid_lib.UUID | None:
    """Best-effort map the caller to an `app_user.uuid` for created_by/updated_by
    (Item 7). Resolves by keycloak_subject → uuid==sub → email. Returns None for
    the dev fallback identity or when no local mirror exists yet."""
    from app.models.security import AppUser

    subject = principal.subject if principal.subject not in (None, "dev-user") else None
    if subject:
        row = db.execute(
            select(AppUser.uuid).where(AppUser.keycloak_subject == subject)
        ).scalar_one_or_none()
        if row is not None:
            return row
        try:
            u = uuid_lib.UUID(subject)
            if db.get(AppUser, u) is not None:
                return u
        except (ValueError, TypeError):
            pass
    if principal.email:
        row = db.execute(
            select(AppUser.uuid).where(AppUser.email == principal.email)
        ).scalar_one_or_none()
        if row is not None:
            return row
    return None


def _strip_audit(data: dict) -> dict:
    """Drop any server-managed audit fields a client may have sent (Item 7)."""
    for f in _AUDIT_FIELDS:
        data.pop(f, None)
    return data


def build_crud_router(
    *,
    prefix: str,
    tag: str,
    model: Type[BaseEntity],
    entity_type: str,
    event_domain: str,
    out_schema: Type[BaseModel],
    create_schema: Type[BaseModel],
    update_schema: Type[BaseModel],
    search_columns: list[str] | None = None,
    filter_fields: list[str] | None = None,
    pre_write=None,
) -> APIRouter:
    """`pre_write(db, data, obj_or_None)` may mutate the payload dict before a
    create (obj is None) or update (obj is the existing row). Used e.g. to derive
    hierarchical `level` from a parent (Decision on structural level fields)."""
    repo = Repository(model, entity_type=entity_type, event_domain=event_domain)
    router = APIRouter(prefix=prefix, tags=[tag])
    filter_fields = filter_fields or []

    @router.get("", response_model=PageOut[out_schema])
    def list_items(
        request: Request,
        db: Session = Depends(get_db),
        _: Principal = Depends(get_current_principal),
        search: str | None = Query(None, description="Free-text search"),
        sort: str | None = Query(None, description="Sort field; prefix '-' for desc"),
        limit: int = Query(50, ge=1, le=500),
        offset: int = Query(0, ge=0),
        include_deleted: bool = Query(False),
    ):
        # Structured equality filters from declared filter_fields (query params),
        # each mapping to an exact-match on the model column (Decision #25).
        active_filters: dict[str, Any] = {}
        for _field in filter_fields:
            _val = request.query_params.get(_field)
            if _val not in (None, ""):
                active_filters[_field] = _val
        page = repo.list(
            db,
            search=search,
            filters=active_filters,
            sort=sort,
            limit=limit,
            offset=offset,
            include_deleted=include_deleted,
            search_columns=search_columns,
        )
        return PageOut(
            items=[out_schema.model_validate(i) for i in page.items],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )

    @router.post("", response_model=out_schema, status_code=201)
    def create_item(
        payload: create_schema,  # type: ignore[valid-type]
        db: Session = Depends(get_db),
        principal: Principal = Depends(require_write),
    ):
        data = _strip_audit(payload.model_dump(exclude_unset=True))
        if pre_write is not None:
            pre_write(db, data, None)
        actor = resolve_actor(db, principal)
        obj = repo.create(db, data, actor=actor)
        return out_schema.model_validate(obj)

    @router.get("/{item_uuid}", response_model=out_schema)
    def get_item(
        item_uuid: uuid_lib.UUID,
        db: Session = Depends(get_db),
        _: Principal = Depends(get_current_principal),
    ):
        obj = repo.get(db, item_uuid)
        if obj is None:
            raise HTTPException(status_code=404, detail=f"{tag} not found")
        return out_schema.model_validate(obj)

    @router.patch("/{item_uuid}", response_model=out_schema)
    def update_item(
        item_uuid: uuid_lib.UUID,
        payload: update_schema,  # type: ignore[valid-type]
        db: Session = Depends(get_db),
        principal: Principal = Depends(require_write),
    ):
        obj = repo.get(db, item_uuid)
        if obj is None:
            raise HTTPException(status_code=404, detail=f"{tag} not found")
        data = _strip_audit(payload.model_dump(exclude_unset=True))
        if pre_write is not None:
            pre_write(db, data, obj)
        actor = resolve_actor(db, principal)
        obj = repo.update(db, obj, data, actor=actor)
        return out_schema.model_validate(obj)

    @router.delete("/{item_uuid}", response_model=DeleteResult)
    def delete_item(
        item_uuid: uuid_lib.UUID,
        db: Session = Depends(get_db),
        principal: Principal = Depends(require_write),
    ):
        obj = repo.get(db, item_uuid)
        if obj is None:
            raise HTTPException(status_code=404, detail=f"{tag} not found")
        actor = resolve_actor(db, principal)
        repo.soft_delete(db, obj, actor=actor)
        return DeleteResult(uuid=item_uuid)

    return router