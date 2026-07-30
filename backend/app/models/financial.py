"""Core financial models: account, partner, beneficiary, expense_category,
cash_flow_item, transaction (+split), transfer_group, tag/entity_tag, attachment.

Enum columns are `*_cv_id` FKs to code_value (Decision #23).
"""

import uuid as uuid_lib
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, BaseEntity

AMOUNT = Numeric(18, 4)


class Account(BaseEntity):
    __tablename__ = "account"

    account_type_cv_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("code_value.uuid"), nullable=True
    )
    currency: Mapped[str] = mapped_column(ForeignKey("currency.code"), nullable=False)
    opening_balance: Mapped[Decimal] = mapped_column(AMOUNT, default=0, nullable=False)
    opening_balance_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    institution_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("institution.uuid"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Partner(BaseEntity):
    __tablename__ = "partner"

    partner_type_cv_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("code_value.uuid"), nullable=True
    )


class Beneficiary(BaseEntity):
    """2-level hierarchy."""

    __tablename__ = "beneficiary"

    parent_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("beneficiary.uuid"), nullable=True
    )
    level: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)


class ExpenseCategory(BaseEntity):
    """3-level hierarchy."""

    __tablename__ = "expense_category"

    parent_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("expense_category.uuid"), nullable=True
    )
    level: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)


class CashFlowItem(BaseEntity):
    """Income/expense obligation (was 'expense_item'), fulfilled by transactions."""

    __tablename__ = "cash_flow_item"

    flow_type_cv_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("code_value.uuid"), nullable=True
    )
    expense_category_id: Mapped[uuid_lib.UUID] = mapped_column(
        ForeignKey("expense_category.uuid"), nullable=False
    )
    recurrence_profile_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    expected_amount: Mapped[Decimal | None] = mapped_column(AMOUNT, nullable=True)
    currency: Mapped[str | None] = mapped_column(ForeignKey("currency.code"), nullable=True)
    status_cv_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("code_value.uuid"), nullable=True
    )


class TransferGroup(BaseEntity):
    __tablename__ = "transfer_group"

    from_txn_id: Mapped[uuid_lib.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    to_txn_id: Mapped[uuid_lib.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    from_amount: Mapped[Decimal] = mapped_column(AMOUNT, nullable=False)
    to_amount: Mapped[Decimal] = mapped_column(AMOUNT, nullable=False)
    fx_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)


class Transaction(BaseEntity):
    __tablename__ = "transaction"
    __table_args__ = (
        UniqueConstraint(
            "cash_flow_item_id", "expense_item_seq_no", name="uq_transaction_cfi_seq"
        ),
    )

    account_id: Mapped[uuid_lib.UUID] = mapped_column(
        ForeignKey("account.uuid"), nullable=False, index=True
    )
    txn_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    booking_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    amount: Mapped[Decimal] = mapped_column(AMOUNT, nullable=False)
    currency: Mapped[str] = mapped_column(ForeignKey("currency.code"), nullable=False)
    direction_cv_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("code_value.uuid"), nullable=True
    )
    partner_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("partner.uuid"), nullable=True, index=True
    )
    beneficiary_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("beneficiary.uuid"), nullable=True, index=True
    )
    expense_category_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("expense_category.uuid"), nullable=True, index=True
    )
    cash_flow_item_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("cash_flow_item.uuid"), nullable=True, index=True
    )
    expense_item_seq_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    transfer_group_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("transfer_group.uuid"), nullable=True, index=True
    )
    installment_plan_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    source_document_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    is_split: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status_cv_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("code_value.uuid"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class TransactionSplit(Base):
    __tablename__ = "transaction_split"

    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4
    )
    transaction_id: Mapped[uuid_lib.UUID] = mapped_column(
        ForeignKey("transaction.uuid"), nullable=False, index=True
    )
    expense_category_id: Mapped[uuid_lib.UUID] = mapped_column(
        ForeignKey("expense_category.uuid"), nullable=False
    )
    beneficiary_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("beneficiary.uuid"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(AMOUNT, nullable=False)


class Tag(BaseEntity):
    __tablename__ = "tag"


class EntityTag(Base):
    __tablename__ = "entity_tag"
    __table_args__ = (
        UniqueConstraint("tag_id", "entity_type", "entity_uuid", name="uq_entity_tag"),
    )

    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4
    )
    tag_id: Mapped[uuid_lib.UUID] = mapped_column(ForeignKey("tag.uuid"), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    entity_uuid: Mapped[uuid_lib.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)


class Attachment(Base):
    __tablename__ = "attachment"

    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4
    )
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    entity_uuid: Mapped[uuid_lib.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    storage_key: Mapped[str] = mapped_column(String(400), nullable=False)
    filename: Mapped[str] = mapped_column(String(300), nullable=False)
    mime: Mapped[str | None] = mapped_column(String(120), nullable=True)
    uploaded_by: Mapped[uuid_lib.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CurrencyRate(BaseEntity):
    """FX rate with validity period (Decision #26)."""

    __tablename__ = "currency_rate"

    base_ccy: Mapped[str] = mapped_column(ForeignKey("currency.code"), nullable=False, index=True)
    quote_ccy: Mapped[str] = mapped_column(ForeignKey("currency.code"), nullable=False, index=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    begin_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_cv_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("code_value.uuid"), nullable=True
    )