"""Notification service: create in-app notifications and optionally email them.

Email is sent only when SMTP is enabled + configured; otherwise notifications
remain in-app (Decision #20).

Session 742, Bug 8: SMTP config is stored as **discrete app-config keys** (works
with any provider, e.g. Gmail/Yahoo/Outlook/self-hosted):
  - smtp.enabled   (bool)
  - smtp.host      (string)   e.g. smtp.mail.yahoo.com
  - smtp.port      (int)      e.g. 465 (SSL) or 587 (STARTTLS)
  - smtp.security  (string)   one of: none | starttls | ssl
  - smtp.username  (string)
  - smtp.password  (string)   provider app-password
  - smtp.from      (string)   sender address
  - smtp.to        (string)   default recipient (used for test / no explicit to)
"""

import smtplib
import ssl
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


def _cfg(db: Session, key: str, default=None):
    row = db.get(AppConfig, key)
    return row.value if (row is not None and row.value is not None) else default


def _as_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("1", "true", "t", "yes", "y")


def _smtp_config(db: Session) -> dict | None:
    """Return a normalized SMTP config dict, or None when disabled/incomplete.

    Session 815, Item 20: email settings now live in the **Credentials Store**
    (an "email" category credential). `app_config` keeps only `email.enabled` +
    `email.credentials_ref` (pointing at that credential). We still fall back to
    any legacy `smtp.*` keys for not-yet-migrated installs.
    """
    if not _as_bool(_cfg(db, "email.enabled", _cfg(db, "smtp.enabled", False))):
        return None

    # Preferred: resolve the referenced credential from the Credentials Store.
    ref = _cfg(db, "email.credentials_ref")
    if ref:
        from app.api.credentials import resolve_values

        vals = resolve_values(db, str(ref)) or {}
        host = vals.get("host")
        if host:
            return {
                "host": str(host),
                "port": int(vals.get("port") or 587),
                "security": str(vals.get("security") or "starttls").lower(),
                "username": vals.get("username"),
                "password": vals.get("password"),
                "from": vals.get("from") or vals.get("username") or "pfm@localhost",
                "to": vals.get("recipient"),
            }

    # Legacy fallback: discrete smtp.* keys (pre-migration).
    host = _cfg(db, "smtp.host")
    if not host:
        return None
    return {
        "host": str(host),
        "port": int(_cfg(db, "smtp.port", 587) or 587),
        "security": str(_cfg(db, "smtp.security", "starttls") or "starttls").lower(),
        "username": _cfg(db, "smtp.username"),
        "password": _cfg(db, "smtp.password"),
        "from": _cfg(db, "smtp.from") or _cfg(db, "smtp.username") or "pfm@localhost",
        "to": _cfg(db, "smtp.to"),
    }


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
    """Send one email honoring the `security` mode (none | starttls | ssl)."""
    msg = EmailMessage()
    msg["From"] = smtp.get("from", "pfm@localhost")
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body or subject)

    host = smtp.get("host", "localhost")
    port = int(smtp.get("port", 587))
    security = str(smtp.get("security", "starttls")).lower()

    if security == "ssl":
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, timeout=15, context=context) as server:
            if smtp.get("username"):
                server.login(smtp["username"], smtp.get("password", ""))
            server.send_message(msg)
        return

    with smtplib.SMTP(host, port, timeout=15) as server:
        if security == "starttls":
            server.starttls(context=ssl.create_default_context())
        if smtp.get("username"):
            server.login(smtp["username"], smtp.get("password", ""))
        server.send_message(msg)


def send_test_email(db: Session, to: str | None = None) -> dict:
    """Send a test email using the stored SMTP settings (Session 742, Bug 8).

    Raises RuntimeError with a friendly message when SMTP is disabled/incomplete
    or the send fails, so the API can surface a 422/400 with detail.
    """
    smtp = _smtp_config(db)
    if smtp is None:
        raise RuntimeError("SMTP is disabled or incomplete. Set smtp.enabled and smtp.host.")
    recipient = to or smtp.get("to") or smtp.get("from")
    if not recipient:
        raise RuntimeError("No recipient — set smtp.to or pass an address.")
    try:
        _send_email(
            smtp,
            recipient,
            "PFM test email",
            "This is a test email from your PFM instance. SMTP is configured correctly.",
        )
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Send failed: {exc}") from exc
    return {"sent": True, "to": recipient, "host": smtp["host"], "security": smtp["security"]}
