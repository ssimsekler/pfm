"""Config/meta models: app_config, id_sequence, code_list/value, outbox, audit."""

import uuid as uuid_lib
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseEntity


class AppConfig(Base):
    """Global key/value configuration. See docs/ERD.md app_config."""

    __tablename__ = "app_config"

    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    value_type: Mapped[str] = mapped_column(String(20), default="string", nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )
    updated_by: Mapped[uuid_lib.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)


class IdSequence(Base):
    """Per-prefix mnemonic sequence (Decision #6/#7)."""

    __tablename__ = "id_sequence"

    prefix: Mapped[str] = mapped_column(String(3), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False)
    pad_width: Mapped[int] = mapped_column(SmallInteger, default=5, nullable=False)
    current_seq: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )


class CodeList(BaseEntity):
    """A configurable enumerated value set (Decision #23)."""

    __tablename__ = "code_list"

    list_key: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allow_user_values: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    values: Mapped[list["CodeValue"]] = relationship(
        back_populates="code_list", cascade="all, delete-orphan"
    )


class CodeValue(BaseEntity):
    """A single value within a code list."""

    __tablename__ = "code_value"
    __table_args__ = (UniqueConstraint("code_list_id", "code", name="uq_code_value_list_code"),)

    code_list_id: Mapped[uuid_lib.UUID] = mapped_column(
        ForeignKey("code_list.uuid"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    parent_code_value_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("code_value.uuid"), nullable=True
    )
    extra: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    code_list: Mapped["CodeList"] = relationship(back_populates="values")


class EventOutbox(Base):
    """Transactional outbox for CloudEvents 1.0 (Decision #5/#12)."""

    __tablename__ = "event_outbox"

    id: Mapped[uuid_lib.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4
    )
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(200), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(200), nullable=True)
    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    datacontenttype: Mapped[str] = mapped_column(String(80), default="application/json")
    dataschema: Mapped[str | None] = mapped_column(String(300), nullable=True)
    data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    traceparent: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    """Field-level audit trail (Decision #21)."""

    __tablename__ = "audit_log"

    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4
    )
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    entity_uuid: Mapped[uuid_lib.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    entity_mnemonic: Mapped[str | None] = mapped_column(String(20), nullable=True)
    operation: Mapped[str] = mapped_column(String(20), nullable=False)
    before: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    changed_by: Mapped[uuid_lib.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    correlation_id: Mapped[uuid_lib.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    source_channel: Mapped[str] = mapped_column(String(20), default="api", nullable=False)