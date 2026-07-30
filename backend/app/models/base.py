"""Base declarative model and shared mixins (per docs/ERD.md base columns)."""

import uuid as uuid_lib
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

__all__ = ["Base", "TimestampMixin", "BaseEntity"]


class TimestampMixin:
    """created/updated/deleted audit timestamps + actor columns + soft delete."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[uuid_lib.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
    updated_by: Mapped[uuid_lib.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )


class BaseEntity(TimestampMixin, Base):
    """Abstract base for every business entity.

    Provides: uuid PK, mnemonic_id, name, description, audit/soft-delete,
    and household (tenant) scope. See docs/ERD.md "Base columns".
    """

    __abstract__ = True

    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4
    )
    mnemonic_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    household_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True
    )