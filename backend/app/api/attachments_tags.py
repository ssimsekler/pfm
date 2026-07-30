"""Attachment upload/download and entity-tag assignment endpoints (Phase 2)."""

import uuid as uuid_lib

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import Principal, get_current_principal, require_write
from app.models.financial import Attachment, EntityTag, Tag
from app.services import storage

# ---------------------------------------------------------------------------
# Attachments (polymorphic; stored in MinIO)
# ---------------------------------------------------------------------------
attachment_router = APIRouter(prefix="/api/v1/attachments", tags=["attachments"])


class AttachmentOut(BaseModel):
    uuid: uuid_lib.UUID
    entity_type: str
    entity_uuid: uuid_lib.UUID
    filename: str
    mime: str | None = None

    class Config:
        from_attributes = True


@attachment_router.post("", response_model=AttachmentOut, status_code=201)
async def upload_attachment(
    entity_type: str = Form(...),
    entity_uuid: uuid_lib.UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_write),
):
    content = await file.read()
    key = f"attachments/{entity_type}/{entity_uuid}/{uuid_lib.uuid4()}_{file.filename}"
    storage.put_object(key, content, content_type=file.content_type or "application/octet-stream")
    att = Attachment(
        entity_type=entity_type,
        entity_uuid=entity_uuid,
        storage_key=key,
        filename=file.filename or "upload",
        mime=file.content_type,
    )
    db.add(att)
    db.commit()
    db.refresh(att)
    return att


@attachment_router.get("/for/{entity_type}/{entity_uuid}", response_model=list[AttachmentOut])
def list_attachments(
    entity_type: str,
    entity_uuid: uuid_lib.UUID,
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
):
    stmt = select(Attachment).where(
        Attachment.entity_type == entity_type, Attachment.entity_uuid == entity_uuid
    )
    return list(db.execute(stmt).scalars())


@attachment_router.get("/{attachment_uuid}/download")
def download_attachment(
    attachment_uuid: uuid_lib.UUID,
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
):
    att = db.get(Attachment, attachment_uuid)
    if att is None:
        raise HTTPException(status_code=404, detail="attachment not found")
    data = storage.get_object(att.storage_key)
    return Response(
        content=data,
        media_type=att.mime or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{att.filename}"'},
    )


# ---------------------------------------------------------------------------
# Entity-tag assignment (polymorphic tagging)
# ---------------------------------------------------------------------------
entity_tag_router = APIRouter(prefix="/api/v1/entity-tags", tags=["tags"])


class EntityTagIn(BaseModel):
    tag_id: uuid_lib.UUID
    entity_type: str
    entity_uuid: uuid_lib.UUID


class EntityTagOut(EntityTagIn):
    uuid: uuid_lib.UUID

    class Config:
        from_attributes = True


@entity_tag_router.post("", response_model=EntityTagOut, status_code=201)
def assign_tag(
    payload: EntityTagIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_write),
):
    if db.get(Tag, payload.tag_id) is None:
        raise HTTPException(status_code=422, detail="tag not found")
    existing = db.execute(
        select(EntityTag).where(
            EntityTag.tag_id == payload.tag_id,
            EntityTag.entity_type == payload.entity_type,
            EntityTag.entity_uuid == payload.entity_uuid,
        )
    ).scalar_one_or_none()
    if existing:
        return existing
    link = EntityTag(**payload.model_dump())
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


@entity_tag_router.get("/for/{entity_type}/{entity_uuid}", response_model=list[EntityTagOut])
def list_entity_tags(
    entity_type: str,
    entity_uuid: uuid_lib.UUID,
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
):
    stmt = select(EntityTag).where(
        EntityTag.entity_type == entity_type, EntityTag.entity_uuid == entity_uuid
    )
    return list(db.execute(stmt).scalars())


@entity_tag_router.delete("/{link_uuid}")
def remove_tag(
    link_uuid: uuid_lib.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_write),
):
    link = db.get(EntityTag, link_uuid)
    if link is None:
        raise HTTPException(status_code=404, detail="tag assignment not found")
    db.delete(link)
    db.commit()
    return {"deleted": True, "uuid": str(link_uuid)}


ALL_ROUTERS = [attachment_router, entity_tag_router]