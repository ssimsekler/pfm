"""Phase 4 models: LLM providers/bindings, integration endpoints,
categorization rules, investment holdings + valuation history."""

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
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, BaseEntity

AMOUNT = Numeric(18, 4)


class LlmProvider(BaseEntity):
    __tablename__ = "llm_provider"

    kind_cv_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("code_value.uuid"), nullable=True
    )
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    credentials_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class FeatureLlmBinding(BaseEntity):
    __tablename__ = "feature_llm_binding"

    feature_key: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    primary_provider_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("llm_provider.uuid"), nullable=True
    )
    secondary_provider_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("llm_provider.uuid"), nullable=True
    )


class IntegrationEndpoint(BaseEntity):
    __tablename__ = "integration_endpoint"

    scenario_key: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    provider_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    auth_type_cv_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("code_value.uuid"), nullable=True
    )
    credentials_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    timeout_ms: Mapped[int] = mapped_column(Integer, default=8000, nullable=False)
    priority: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class CategorizationRule(BaseEntity):
    __tablename__ = "categorization_rule"

    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    conditions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    actions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class InvestmentHolding(BaseEntity):
    __tablename__ = "investment_holding"

    account_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("account.uuid"), nullable=True
    )
    symbol: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    asset_type_cv_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("code_value.uuid"), nullable=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), default=0, nullable=False)
    entry_value: Mapped[Decimal | None] = mapped_column(AMOUNT, nullable=True)
    entry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    current_value_cache: Mapped[Decimal | None] = mapped_column(AMOUNT, nullable=True)
    currency: Mapped[str | None] = mapped_column(ForeignKey("currency.code"), nullable=True)


class ValuationHistory(Base):
    __tablename__ = "valuation_history"
    __table_args__ = (
        UniqueConstraint("holding_id", "as_of_date", name="uq_valuation_holding_date"),
    )

    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4
    )
    holding_id: Mapped[uuid_lib.UUID] = mapped_column(
        ForeignKey("investment_holding.uuid"), nullable=False, index=True
    )
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[Decimal] = mapped_column(AMOUNT, nullable=False)
    source_cv_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("code_value.uuid"), nullable=True
    )
    created_by: Mapped[uuid_lib.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )