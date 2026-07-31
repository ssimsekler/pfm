"""Phase 5 models: document_import (+ rows) for bulk statement import."""

import uuid as uuid_lib
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
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


class ImportMappingMemory(Base):
    """Learned statement-text → partner/category mapping (Session 742, Bug 17).

    On each accepted commit we upsert by the row's source text and bump
    `accept_count`; when mapping a new row we recommend the most-frequently
    accepted partner/category for that text (bank supplier text is stable).
    """

    __tablename__ = "import_mapping_memory"

    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4
    )
    source_text: Mapped[str] = mapped_column(String(400), nullable=False, index=True)
    mapped_partner_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("partner.uuid"), nullable=True
    )
    mapped_category_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("expense_category.uuid"), nullable=True
    )
    accept_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
