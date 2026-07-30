"""Notification service: create in-app notifications and optionally email them.

Email is sent only when SMTP is configured (app_config['smtp.enabled'] + settings);
otherwise notifications remain in-app (Decision #20).
"""

import smtplib
import uuid as uuid_lib
from datetime import datetime, timezone
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.meta import AppConfig, CodeList, CodeValue
from app.models.notifications import Notification


def _cv(db: Session, list_key: str, code: str) -> uuid_lib.UUID | None:
    cl = db.execute(select(CodeList).where(CodeList.list_key == list_key)).scalar_one_or_none()
    if cl is None:
        return None
    cv = db.execute(
        select(CodeValue).where(CodeValue.code_list_id == cl.uuid, CodeValue.code == code)
    ).scalar_one_or_none()
    return cv.uuid if cv else None


def _smtp_config(db: Session) -> dict | None:
    enabled = db.get(AppConfig, "smtp.enabled")
    if enabled is None or not bool(enabled.value):
        return None
    cfg = db.get(AppConfig, "smtp.config")
    return cfg.value if cfg and isinstance(cfg.value, dict) else None


def create_notification(
    db: Session,
    *,
    subject: str,
    body: str = "",
    type_code: str | None = None,
    user_id: uuid_lib.UUID | None = None,
    related_entity_type: str | None = None,
    related_entity_uuid: uuid_lib.UUID | None = None,
    email_to: str | None = None,
) -> Notification:
    """Create an in-app notification; email it too if SMTP is configured."""
    channel_code = "in_app"
    smtp = _smtp_config(db)
    sent_at = None
    status_code = "pending"

    if smtp and email_to:
        try:
            _send_email(smtp, email_to, subject, body)
            channel_code = "email"
            status_code = "sent"
            sent_at = datetime.now(timezone.utc)
        except Exception:  # noqa: BLE001
            channel_code = "in_app"  # fall back to in-app on failure

    note = Notification(
        uuid=uuid_lib.uuid4(),
        user_id=user_id,
        type_cv_id=_cv(db, "notification_type", type_code) if type_code else None,
        subject=subject,
        body=body,
        channel_cv_id=_cv(db, "notification_channel", channel_code),
        status_cv_id=_cv(db, "notification_status", status_code),
        related_entity_type=related_entity_type,
        related_entity_uuid=related_entity_uuid,
        sent_at=sent_at,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def _send_email(smtp: dict, to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = smtp.get("from", "pfm@localhost")
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body or subject)

    host = smtp.get("host", "localhost")
    port = int(smtp.get("port", 587))
    with smtplib.SMTP(host, port, timeout=10) as server:
        if smtp.get("starttls", True):
            server.starttls()
        if smtp.get("username"):
            server.login(smtp["username"], smtp.get("password", ""))
        server.send_message(msg)