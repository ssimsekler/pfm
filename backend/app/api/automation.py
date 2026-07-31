"""Phase 4 API: LLM providers/bindings, integration endpoints, categorization
rules, investments (+ valuation refresh/history), FX refresh from source."""

import uuid as uuid_lib
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.crud_router import build_crud_router
from app.api.schemas import EntityOut, ORMModel
from app.core.database import get_db
from app.core.security import Principal, get_current_principal, require_write
from app.models import automation as auto
from app.models import financial as fin
from app.services import connectors, valuation
from app.services.valuation import ValuationError
from app.services.auto_account import ensure_backing_account
from app.services.repository import Repository

# ---------------------------------------------------------------------------
# LLM providers
# ---------------------------------------------------------------------------
class LlmProviderOut(EntityOut):
    kind_cv_id: uuid_lib.UUID | None = None
    base_url: str | None = None
    model: str | None = None
    enabled: bool
    params: dict | None = None
    # Surfaced from params.priority for the UI (New-2 failover order).
    priority: int | None = None


class LlmProviderCreate(ORMModel):
    name: str
    description: str | None = None
    kind_cv_id: uuid_lib.UUID | None = None
    base_url: str | None = None
    model: str | None = None
    credentials_ref: str | None = None
    enabled: bool = True
    params: dict | None = None
    priority: int | None = None


class LlmProviderUpdate(ORMModel):
    name: str | None = None
    description: str | None = None
    kind_cv_id: uuid_lib.UUID | None = None
    base_url: str | None = None
    model: str | None = None
    credentials_ref: str | None = None
    enabled: bool | None = None
    params: dict | None = None
    priority: int | None = None


def _llm_pre_write(db: Session, data: dict, obj) -> None:
    """Fold a flat `priority` into `params.priority` (New-2 failover order)."""
    if "priority" in data:
        pr = data.pop("priority")
        if pr is not None:
            params = dict(data.get("params") or (getattr(obj, "params", None) or {}))
            params["priority"] = int(pr)
            data["params"] = params


llm_provider_router = build_crud_router(
    prefix="/api/v1/llm-providers", tag="llm-providers", model=auto.LlmProvider,
    entity_type="llm_provider", event_domain="llm_provider",
    out_schema=LlmProviderOut, create_schema=LlmProviderCreate, update_schema=LlmProviderUpdate,
    search_columns=["model", "base_url"],
    pre_write=_llm_pre_write,
)


# ---------------------------------------------------------------------------
# Feature ↔ LLM bindings
# ---------------------------------------------------------------------------
class FeatureBindingOut(EntityOut):
    feature_key: str
    primary_provider_id: uuid_lib.UUID | None = None
    secondary_provider_id: uuid_lib.UUID | None = None


class FeatureBindingCreate(ORMModel):
    name: str
    description: str | None = None
    feature_key: str
    primary_provider_id: uuid_lib.UUID | None = None
    secondary_provider_id: uuid_lib.UUID | None = None


class FeatureBindingUpdate(ORMModel):
    name: str | None = None
    description: str | None = None
    feature_key: str | None = None
    primary_provider_id: uuid_lib.UUID | None = None
    secondary_provider_id: uuid_lib.UUID | None = None


feature_binding_router = build_crud_router(
    prefix="/api/v1/feature-llm-bindings", tag="llm-bindings", model=auto.FeatureLlmBinding,
    entity_type="feature_llm_binding", event_domain="feature_llm_binding",
    out_schema=FeatureBindingOut, create_schema=FeatureBindingCreate,
    update_schema=FeatureBindingUpdate, search_columns=["feature_key"],
)


# ---------------------------------------------------------------------------
# Integration endpoints
# ---------------------------------------------------------------------------
class IntegrationEndpointOut(EntityOut):
    scenario_key: str
    provider_name: str | None = None
    base_url: str | None = None
    auth_type_cv_id: uuid_lib.UUID | None = None
    config: dict | None = None
    timeout_ms: int
    priority: int
    enabled: bool


class IntegrationEndpointCreate(ORMModel):
    name: str
    description: str | None = None
    scenario_key: str
    provider_name: str | None = None
    base_url: str | None = None
    auth_type_cv_id: uuid_lib.UUID | None = None
    credentials_ref: str | None = None
    config: dict | None = None
    timeout_ms: int = 8000
    priority: int = 1
    enabled: bool = True


class IntegrationEndpointUpdate(ORMModel):
    name: str | None = None
    description: str | None = None
    scenario_key: str | None = None
    provider_name: str | None = None
    base_url: str | None = None
    auth_type_cv_id: uuid_lib.UUID | None = None
    credentials_ref: str | None = None
    config: dict | None = None
    timeout_ms: int | None = None
    priority: int | None = None
    enabled: bool | None = None


integration_endpoint_router = build_crud_router(
    prefix="/api/v1/integration-endpoints", tag="integration-endpoints",
    model=auto.IntegrationEndpoint, entity_type="integration_endpoint",
    event_domain="integration_endpoint",
    out_schema=IntegrationEndpointOut, create_schema=IntegrationEndpointCreate,
    update_schema=IntegrationEndpointUpdate, search_columns=["scenario_key", "provider_name"],
)


# ---------------------------------------------------------------------------
# Categorization rules
# ---------------------------------------------------------------------------
class RuleOut(EntityOut):
    priority: int
    conditions: dict | None = None
    actions: dict | None = None
    enabled: bool


class RuleCreate(ORMModel):
    name: str
    description: str | None = None
    priority: int = 100
    conditions: dict | None = None
    actions: dict | None = None
    enabled: bool = True


class RuleUpdate(ORMModel):
    name: str | None = None
    description: str | None = None
    priority: int | None = None
    conditions: dict | None = None
    actions: dict | None = None
    enabled: bool | None = None


rule_router = build_crud_router(
    prefix="/api/v1/categorization-rules", tag="categorization-rules",
    model=auto.CategorizationRule, entity_type="categorization_rule",
    event_domain="categorization_rule",
    out_schema=RuleOut, create_schema=RuleCreate, update_schema=RuleUpdate,
)


# ---------------------------------------------------------------------------
# Investment holdings (+ valuation refresh & history)
# ---------------------------------------------------------------------------
class HoldingOut(EntityOut):
    account_id: uuid_lib.UUID | None = None
    symbol: str
    asset_type_cv_id: uuid_lib.UUID | None = None
    quantity: Decimal
    entry_value: Decimal | None = None
    entry_date: date | None = None
    current_value_cache: Decimal | None = None
    currency: str | None = None


class HoldingCreate(ORMModel):
    name: str
    description: str | None = None
    account_id: uuid_lib.UUID | None = None
    symbol: str
    asset_type_cv_id: uuid_lib.UUID | None = None
    quantity: Decimal = Decimal(0)
    entry_value: Decimal | None = None
    entry_date: date | None = None
    currency: str | None = None


class HoldingUpdate(ORMModel):
    name: str | None = None
    description: str | None = None
    account_id: uuid_lib.UUID | None = None
    symbol: str | None = None
    asset_type_cv_id: uuid_lib.UUID | None = None
    quantity: Decimal | None = None
    entry_value: Decimal | None = None
    entry_date: date | None = None
    currency: str | None = None


def _holding_pre_write(db: Session, data: dict, obj) -> None:
    # A.6: auto-create a backing account on create if none was supplied.
    if obj is None:
        ensure_backing_account(db, data, "Investment")


holding_router = build_crud_router(
    prefix="/api/v1/investments", tag="investments", model=auto.InvestmentHolding,
    entity_type="investment_holding", event_domain="investment_holding",
    out_schema=HoldingOut, create_schema=HoldingCreate, update_schema=HoldingUpdate,
    search_columns=["symbol"], pre_write=_holding_pre_write,
)


class ValuationOut(BaseModel):
    uuid: uuid_lib.UUID
    as_of_date: date
    value: Decimal
    source_cv_id: uuid_lib.UUID | None = None

    class Config:
        from_attributes = True


class ValuationIn(BaseModel):
    as_of_date: date
    value: Decimal


class RefreshValuationIn(BaseModel):
    on: date | None = None  # target date (default today); overwrites an existing row


@holding_router.post("/{holding_id}/refresh-valuation")
def refresh_valuation(
    holding_id: uuid_lib.UUID,
    payload: RefreshValuationIn | None = None,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_write),
):
    """Fetch a price for the target date (default today) and upsert it (Session 742).

    Overwrites the valuation for that date if one exists; clear errors distinguish a
    manual-only asset type from a source failure.
    """
    holding = db.get(auto.InvestmentHolding, holding_id)
    if holding is None:
        raise HTTPException(status_code=404, detail="holding not found")
    on = payload.on if payload else None
    try:
        value = valuation.refresh_holding(db, holding, on=on)
    except ValuationError as exc:
        # 422 with a helpful, reason-tagged message.
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "holding": str(holding_id),
        "value": str(value),
        "as_of": (on or date.today()).isoformat(),
    }


@holding_router.get("/{holding_id}/valuations", response_model=list[ValuationOut])
def list_valuations(
    holding_id: uuid_lib.UUID,
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
):
    stmt = select(auto.ValuationHistory).where(
        auto.ValuationHistory.holding_id == holding_id
    ).order_by(auto.ValuationHistory.as_of_date.desc())
    return list(db.execute(stmt).scalars())


@holding_router.post("/{holding_id}/valuations", response_model=ValuationOut, status_code=201)
def add_valuation(
    holding_id: uuid_lib.UUID,
    payload: ValuationIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_write),
):
    holding = db.get(auto.InvestmentHolding, holding_id)
    if holding is None:
        raise HTTPException(status_code=404, detail="holding not found")
    existing = db.execute(
        select(auto.ValuationHistory).where(
            auto.ValuationHistory.holding_id == holding_id,
            auto.ValuationHistory.as_of_date == payload.as_of_date,
        )
    ).scalar_one_or_none()
    if existing:
        existing.value = payload.value
        row = existing
    else:
        row = auto.ValuationHistory(
            holding_id=holding_id, as_of_date=payload.as_of_date, value=payload.value
        )
        db.add(row)
    # keep cache in sync with the latest date
    latest = db.execute(
        select(auto.ValuationHistory).where(auto.ValuationHistory.holding_id == holding_id)
        .order_by(auto.ValuationHistory.as_of_date.desc()).limit(1)
    ).scalar_one_or_none()
    holding.current_value_cache = (latest.value if latest else payload.value)
    db.commit()
    db.refresh(row)
    return row


# ---------------------------------------------------------------------------
# FX refresh from the configured source into currency_rate validity periods
# ---------------------------------------------------------------------------
fx_admin_router = APIRouter(prefix="/api/v1/fx", tags=["fx"])
_rate_repo = Repository(fin.CurrencyRate, entity_type="currency_rate", event_domain="currency_rate")

OPEN_END = date(9999, 12, 31)


class FxRefreshIn(BaseModel):
    base_ccy: str
    quote_ccy: str
    on: date | None = None


@fx_admin_router.post("/refresh", status_code=201)
def refresh_fx_rate(
    payload: FxRefreshIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_write),
):
    """Pull a rate from the configured FX source and store it as a validity period.

    Closes the current open-ended period (if any) at the new begin_date, then adds a
    new open-ended row so a valid rate always exists (Decision #26).
    """
    on = payload.on or date.today()
    base = (payload.base_ccy or "").upper()
    quote = (payload.quote_ccy or "").upper()
    rate = connectors.fetch_fx_rate(db, base, quote, on)
    if rate is None:
        raise HTTPException(
            status_code=422,
            detail=(
                f"No FX source could price {base}/{quote} on {on.isoformat()}. "
                "Check the currency codes, or add the rate manually below."
            ),
        )

    # Close any open-ended period for this pair.
    open_row = db.execute(
        select(fin.CurrencyRate).where(
            fin.CurrencyRate.base_ccy == payload.base_ccy,
            fin.CurrencyRate.quote_ccy == payload.quote_ccy,
            fin.CurrencyRate.end_date == OPEN_END,
            fin.CurrencyRate.deleted_at.is_(None),
        )
    ).scalar_one_or_none()
    if open_row and open_row.begin_date < on:
        _rate_repo.update(db, open_row, {"end_date": on})

    new_row = _rate_repo.create(
        db,
        {
            "name": f"{payload.base_ccy}/{payload.quote_ccy} @ {on.isoformat()}",
            "base_ccy": payload.base_ccy,
            "quote_ccy": payload.quote_ccy,
            "rate": rate,
            "begin_date": on,
            "end_date": OPEN_END,
        },
    )
    return {
        "currency_rate": str(new_row.uuid),
        "base_ccy": payload.base_ccy,
        "quote_ccy": payload.quote_ccy,
        "rate": str(rate),
        "begin_date": on.isoformat(),
    }


ALL_ROUTERS = [
    llm_provider_router,
    feature_binding_router,
    integration_endpoint_router,
    rule_router,
    holding_router,
    fx_admin_router,
]
