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

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.schemas import DeleteResult, PageOut
from app.core.database import get_db
from app.core.security import Principal, get_current_principal, require_write
from app.models.base import BaseEntity
from app.services.repository import Repository


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
) -> APIRouter:
    repo = Repository(model, entity_type=entity_type, event_domain=event_domain)
    router = APIRouter(prefix=prefix, tags=[tag])
    filter_fields = filter_fields or []

    @router.get("", response_model=PageOut[out_schema])
    def list_items(
        db: Session = Depends(get_db),
        _: Principal = Depends(get_current_principal),
        search: str | None = Query(None, description="Free-text search"),
        sort: str | None = Query(None, description="Sort field; prefix '-' for desc"),
        limit: int = Query(50, ge=1, le=500),
        offset: int = Query(0, ge=0),
        include_deleted: bool = Query(False),
    ):
        # Entity-specific structured filters are added per-router when needed.
        active_filters: dict[str, Any] = {}
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
        obj = repo.create(db, payload.model_dump(exclude_unset=True))
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
        obj = repo.update(db, obj, payload.model_dump(exclude_unset=True))
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
        repo.soft_delete(db, obj)
        return DeleteResult(uuid=item_uuid)

    return router