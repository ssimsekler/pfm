"""Notifications API (Phase 7, Decision #20):

  GET  /api/v1/notifications            list (newest first, optional unread filter)
  POST /api/v1/notifications            create an in-app notification (emails if SMTP on)
  POST /api/v1/notifications/{uuid}/read  mark a notification as read
"""

import uuid as uuid_lib
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import Principal, get_current_principal, require_write
from app.models.meta import CodeList, CodeValue
from app.models.notifications import Notification
from app.services import notifications as notification_service

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


class NotificationOut(BaseModel):
    uuid: uuid_lib.UUID
    user_id: uuid_lib.UUID | None = None
    subject: str
    body: str | None = None
    type_cv_id: uuid_lib.UUID | None = None
    channel_cv_id: uuid_lib.UUID | None = None
    status_cv_id: uuid_lib.UUID | None = None
    related_entity_type: str | None = None
    related_entity_uuid: uuid_lib.UUID | None = None
    scheduled_for: datetime | None = None
    sent_at: datetime | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class NotificationIn(BaseModel):
    subject: str
    body: str = ""
    type_code: str | None = None
    user_id: uuid_lib.UUID | None = None
    related_entity_type: str | None = None
    related_entity_uuid: uuid_lib.UUID | None = None
    email_to: str | None = None


def _status_cv_id(db: Session, code: str) -> uuid_lib.UUID | None:
    cl = db.execute(
        select(CodeList).where(CodeList.list_key == "notification_status")
    ).scalar_one_or_none()
    if cl is None:
        return None
    cv = db.execute(
        select(CodeValue).where(CodeValue.code_list_id == cl.uuid, CodeValue.code == code)
    ).scalar_one_or_none()
    return cv.uuid if cv else None


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
):
    stmt = select(Notification).order_by(Notification.created_at.desc())
    if unread_only:
        read_id = _status_cv_id(db, "read")
        if read_id is not None:
            stmt = stmt.where(Notification.status_cv_id != read_id)
    stmt = stmt.offset(offset).limit(limit)
    return list(db.execute(stmt).scalars())


@router.post("", response_model=NotificationOut, status_code=201)
def create_notification(
    payload: NotificationIn,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_write),
):
    return notification_service.create_notification(
        db,
        subject=payload.subject,
        body=payload.body,
        type_code=payload.type_code,
        user_id=payload.user_id,
        related_entity_type=payload.related_entity_type,
        related_entity_uuid=payload.related_entity_uuid,
        email_to=payload.email_to,
    )


@router.post("/{notification_uuid}/read", response_model=NotificationOut)
def mark_read(
    notification_uuid: uuid_lib.UUID,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_write),
):
    note = db.get(Notification, notification_uuid)
    if note is None:
        raise HTTPException(status_code=404, detail="notification not found")
    read_id = _status_cv_id(db, "read")
    if read_id is not None:
        note.status_cv_id = read_id
    db.commit()
    db.refresh(note)
    return note


ALL_ROUTERS = [router]