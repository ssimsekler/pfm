"""Phase 5 models: document_import (+ rows) for bulk statement import."""

import uuid as uuid_lib
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, BaseEntity


class DocumentImport(BaseEntity):
    __tablename__ = "document_import"

    original_filename: Mapped[str] = mapped_column(String(300), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(400), nullable=False)
    mime: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status_cv_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("code_value.uuid"), nullable=True
    )
    uploaded_by: Mapped[uuid_lib.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    parse_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class DocumentImportRow(Base):
    __tablename__ = "document_import_row"

    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4
    )
    import_id: Mapped[uuid_lib.UUID] = mapped_column(
        ForeignKey("document_import.uuid"), nullable=False, index=True
    )
    raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    mapped_values: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    mapping_status_cv_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("code_value.uuid"), nullable=True
    )
    dedup_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    target_txn_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("transaction.uuid"), nullable=True
    )