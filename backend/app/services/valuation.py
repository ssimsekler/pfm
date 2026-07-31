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


class ValuationError(Exception):
    """Raised when a valuation cannot be fetched, with a user-facing reason.

    `kind`:
      - "manual_only": asset type has no price source (generic asset) — enter manually.
      - "source": the configured source returned no price / was unreachable / symbol unknown.
    """

    def __init__(self, message: str, kind: str = "source") -> None:
        super().__init__(message)
        self.kind = kind


def refresh_holding(
    db: Session, holding: InvestmentHolding, on: date | None = None
) -> Decimal:
    """Fetch price for `on` (default today), upsert valuation history, update cache.

    Session 742 (valuation bug): accepts a target date and **overwrites** an existing
    row for that date (else inserts). Raises ``ValuationError`` with a clear reason
    instead of silently returning None, so the API can surface a helpful 422.
    """
    as_of = on or date.today()
    kind = _asset_kind(db, holding)
    vs = (holding.currency or "USD").lower()

    price: Decimal | None
    if kind == "crypto":
        price = connectors.fetch_crypto_price(db, holding.symbol.lower(), vs_currency=vs)
    elif kind in ("stock", "etf"):
        price = connectors.fetch_stock_price(db, holding.symbol)
    else:
        raise ValuationError(
            "This asset type has no automatic price source — add a valuation manually.",
            kind="manual_only",
        )

    if price is None:
        raise ValuationError(
            f"The price source returned no value for “{holding.symbol}”. "
            "Check the symbol / source, or add a valuation manually.",
            kind="source",
        )

    value = (Decimal(holding.quantity) * price) if holding.quantity else price

    existing = db.execute(
        select(ValuationHistory).where(
            ValuationHistory.holding_id == holding.uuid,
            ValuationHistory.as_of_date == as_of,
        )
    ).scalar_one_or_none()
    if existing:
        existing.value = value  # overwrite for the chosen date
    else:
        db.add(
            ValuationHistory(
                uuid=uuid_lib.uuid4(),
                holding_id=holding.uuid,
                as_of_date=as_of,
                value=value,
            )
        )

    # Keep the cache in sync with the latest-dated valuation.
    latest = db.execute(
        select(ValuationHistory)
        .where(ValuationHistory.holding_id == holding.uuid)
        .order_by(ValuationHistory.as_of_date.desc())
        .limit(1)
    ).scalar_one_or_none()
    holding.current_value_cache = value if (latest is None or as_of >= latest.as_of_date) else latest.value
    db.commit()
    return value
