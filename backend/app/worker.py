"""Phase 7 API: notifications (list, get, mark-read) + manual create (dev/test)."""

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
from app.services import notifications as notif_service

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


class NotificationOut(BaseModel):
    uuid: uuid_lib.UUID
    subject: str
    body: str | None = None
    type_cv_id: uuid_lib.UUID | None = None
    channel_cv_id: uuid_lib.UUID | None = None
    status_cv_id: uuid_lib.UUID | None = None
    related_entity_type: str | None = None
    related_entity_uuid: uuid_lib.UUID | None = None
    sent_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationCreate(BaseModel):
    subject: str
    body: str | None = None
    type_code: str | None = None
    email_to: str | None = None


def _status_cv_id(db: Session, code: str) -> uuid_lib.UUID | None:
    cl = db.execute(select(CodeList).where(CodeList.list_key == "notification_status")).scalar_one_or_none()
    if cl is None:
        return None
    cv = db.execute(
        select(CodeValue).where(CodeValue.code_list_id == cl.uuid, CodeValue.code == code)
    ).scalar_one_or_none()
    return cv.uuid if cv else None


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    stmt = (
        select(Notification)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.execute(stmt).scalars())


@router.post("", response_model=NotificationOut, status_code=201)
def create_notification(
    payload: NotificationCreate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_write),
):
    return notif_service.create_notification(
        db,
        subject=payload.subject,
        body=payload.body or "",
        type_code=payload.type_code,
        email_to=payload.email_to,
    )


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(
    notification_id: uuid_lib.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_write),
):
    note = db.get(Notification, notification_id)
    if note is None:
        raise HTTPException(status_code=404, detail="notification not found")
    note.status_cv_id = _status_cv_id(db, "read")
    db.commit()
    db.refresh(note)
    return note


ALL_ROUTERS = [router]