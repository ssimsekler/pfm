"""Investment valuation refresh: pull current price and record history.

Updates `investment_holding.current_value_cache` and appends a `valuation_history`
row (source of truth). Uses the configured connectors (Decision #18/#5.2).
"""

import uuid as uuid_lib
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.automation import InvestmentHolding, ValuationHistory
from app.models.meta import CodeValue
from app.services import connectors


def _asset_kind(db: Session, holding: InvestmentHolding) -> str | None:
    if holding.asset_type_cv_id is None:
        return None
    cv = db.get(CodeValue, holding.asset_type_cv_id)
    return cv.code if cv else None


def refresh_holding(db: Session, holding: InvestmentHolding) -> Decimal | None:
    """Fetch price, update cache + append valuation history. Returns the value or None."""
    kind = _asset_kind(db, holding)
    vs = (holding.currency or "USD").lower()

    price: Decimal | None
    if kind == "crypto":
        price = connectors.fetch_crypto_price(db, holding.symbol.lower(), vs_currency=vs)
    elif kind in ("stock", "etf"):
        price = connectors.fetch_stock_price(db, holding.symbol)
    else:
        price = None  # generic asset: manual only

    if price is None:
        return None

    value = (Decimal(holding.quantity) * price) if holding.quantity else price
    today = date.today()

    existing = db.execute(
        select(ValuationHistory).where(
            ValuationHistory.holding_id == holding.uuid,
            ValuationHistory.as_of_date == today,
        )
    ).scalar_one_or_none()
    if existing:
        existing.value = value
    else:
        db.add(
            ValuationHistory(
                uuid=uuid_lib.uuid4(),
                holding_id=holding.uuid,
                as_of_date=today,
                value=value,
            )
        )
    holding.current_value_cache = value
    db.commit()
    return value