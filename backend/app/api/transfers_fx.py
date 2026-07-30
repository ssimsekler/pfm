"""Transfers (dual-leg) and currency-rate + FX conversion endpoints (Phase 2)."""

import uuid as uuid_lib
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.crud_router import build_crud_router
from app.api.schemas import EntityOut, ORMModel
from app.core.database import get_db
from app.core.security import Principal, get_current_principal, require_write
from app.models import financial as fin
from app.services import fx
from app.services.repository import Repository

# ---------------------------------------------------------------------------
# Currency rate (validity periods) — CRUD via factory
# ---------------------------------------------------------------------------
class CurrencyRateOut(EntityOut):
    base_ccy: str
    quote_ccy: str
    rate: Decimal
    begin_date: date
    end_date: date
    source_cv_id: uuid_lib.UUID | None = None


class CurrencyRateCreate(ORMModel):
    name: str
    description: str | None = None
    base_ccy: str
    quote_ccy: str
    rate: Decimal
    begin_date: date
    end_date: date
    source_cv_id: uuid_lib.UUID | None = None


class CurrencyRateUpdate(ORMModel):
    name: str | None = None
    description: str | None = None
    rate: Decimal | None = None
    begin_date: date | None = None
    end_date: date | None = None
    source_cv_id: uuid_lib.UUID | None = None


currency_rate_router = build_crud_router(
    prefix="/api/v1/currency-rates", tag="currency-rates", model=fin.CurrencyRate,
    entity_type="currency_rate", event_domain="currency_rate",
    out_schema=CurrencyRateOut, create_schema=CurrencyRateCreate,
    update_schema=CurrencyRateUpdate, search_columns=["base_ccy", "quote_ccy"],
)


# ---------------------------------------------------------------------------
# FX conversion helper endpoint
# ---------------------------------------------------------------------------
fx_router = APIRouter(prefix="/api/v1/fx", tags=["fx"])


@fx_router.get("/convert")
def fx_convert(
    amount: Decimal = Query(...),
    from_ccy: str = Query(..., min_length=3, max_length=3),
    to_ccy: str = Query(..., min_length=3, max_length=3),
    as_of: date | None = Query(None),
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
):
    on = as_of or date.today()
    rate = fx.get_rate(db, from_ccy.upper(), to_ccy.upper(), on)
    if rate is None:
        raise HTTPException(status_code=422, detail="No FX rate available for that pair/date")
    return {
        "amount": str(amount),
        "from": from_ccy.upper(),
        "to": to_ccy.upper(),
        "as_of": on.isoformat(),
        "rate": str(rate),
        "converted": str(Decimal(amount) * rate),
    }


# ---------------------------------------------------------------------------
# Transfers (dual-leg) — creates two transactions + a transfer_group
# ---------------------------------------------------------------------------
transfer_router = APIRouter(prefix="/api/v1/transfers", tags=["transfers"])
_txn_repo = Repository(fin.Transaction, entity_type="transaction", event_domain="transaction")
_tg_repo = Repository(fin.TransferGroup, entity_type="transfer_group", event_domain="transfer")


class TransferCreate(ORMModel):
    name: str
    description: str | None = None
    from_account_id: uuid_lib.UUID
    to_account_id: uuid_lib.UUID
    from_amount: Decimal
    to_amount: Decimal | None = None  # for cross-currency; defaults to from_amount
    from_currency: str
    to_currency: str
    txn_date: date
    note: str | None = None


@transfer_router.post("", status_code=201)
def create_transfer(
    payload: TransferCreate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_write),
):
    if payload.from_account_id == payload.to_account_id:
        raise HTTPException(status_code=422, detail="from and to accounts must differ")

    to_amount = payload.to_amount if payload.to_amount is not None else payload.from_amount
    fx_rate = None
    if payload.from_currency != payload.to_currency and payload.from_amount:
        try:
            fx_rate = (Decimal(to_amount) / Decimal(payload.from_amount))
        except Exception:  # noqa: BLE001
            fx_rate = None

    group = _tg_repo.create(
        db,
        {
            "name": payload.name,
            "description": payload.description,
            "from_amount": payload.from_amount,
            "to_amount": to_amount,
            "fx_rate": fx_rate,
        },
    )

    debit = _txn_repo.create(
        db,
        {
            "name": f"{payload.name} (out)",
            "account_id": payload.from_account_id,
            "txn_date": payload.txn_date,
            "amount": payload.from_amount,
            "currency": payload.from_currency,
            "transfer_group_id": group.uuid,
            "note": payload.note,
        },
    )
    credit = _txn_repo.create(
        db,
        {
            "name": f"{payload.name} (in)",
            "account_id": payload.to_account_id,
            "txn_date": payload.txn_date,
            "amount": to_amount,
            "currency": payload.to_currency,
            "transfer_group_id": group.uuid,
            "note": payload.note,
        },
    )

    # Link the group back to its legs.
    _tg_repo.update(db, group, {"from_txn_id": debit.uuid, "to_txn_id": credit.uuid})

    return {
        "transfer_group": str(group.uuid),
        "from_txn": str(debit.uuid),
        "to_txn": str(credit.uuid),
        "fx_rate": str(fx_rate) if fx_rate is not None else None,
    }


ALL_ROUTERS = [currency_rate_router, fx_router, transfer_router]