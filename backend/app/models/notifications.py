"""Notification model (see docs/ERD.md §Notifications, Decision #20).

Standalone entity (not BaseEntity) — mirrors the ERD's explicit column list:
uuid PK, user + code-value FKs (type/channel/status), subject/body, optional
related-entity pointer, scheduling/sent timestamps.
"""

import uuid as uuid_lib
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Notification(Base):
    __tablename__ = "notification"

    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4
    )
    user_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("app_user.uuid"), nullable=True, index=True
    )
    type_cv_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("code_value.uuid"), nullable=True
    )
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel_cv_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("code_value.uuid"), nullable=True
    )
    status_cv_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("code_value.uuid"), nullable=True
    )
    related_entity_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    related_entity_uuid: Mapped[uuid_lib.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )