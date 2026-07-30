"""FX conversion using validity-period rates (Decision #26/#27).

Lookup rule: pick the rate where begin_date <= as_of < end_date for the
(base_ccy, quote_ccy) pair. Falls back to the closest period if none matches.
Supports direct, inverse, and identity conversions.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.financial import CurrencyRate


def _period_rate(
    db: Session, base_ccy: str, quote_ccy: str, as_of: date
) -> Decimal | None:
    stmt = (
        select(CurrencyRate)
        .where(
            CurrencyRate.base_ccy == base_ccy,
            CurrencyRate.quote_ccy == quote_ccy,
            CurrencyRate.begin_date <= as_of,
            CurrencyRate.end_date > as_of,
            CurrencyRate.deleted_at.is_(None),
        )
        .limit(1)
    )
    row = db.execute(stmt).scalar_one_or_none()
    if row is not None:
        return Decimal(row.rate)

    # Fallback 1: latest period beginning on/before as_of.
    prior = db.execute(
        select(CurrencyRate)
        .where(
            CurrencyRate.base_ccy == base_ccy,
            CurrencyRate.quote_ccy == quote_ccy,
            CurrencyRate.begin_date <= as_of,
            CurrencyRate.deleted_at.is_(None),
        )
        .order_by(CurrencyRate.begin_date.desc())
        .limit(1)
    ).scalar_one_or_none()
    if prior is not None:
        return Decimal(prior.rate)

    # Fallback 2: earliest available period.
    earliest = db.execute(
        select(CurrencyRate)
        .where(
            CurrencyRate.base_ccy == base_ccy,
            CurrencyRate.quote_ccy == quote_ccy,
            CurrencyRate.deleted_at.is_(None),
        )
        .order_by(CurrencyRate.begin_date.asc())
        .limit(1)
    ).scalar_one_or_none()
    return Decimal(earliest.rate) if earliest is not None else None


def get_rate(db: Session, base_ccy: str, quote_ccy: str, as_of: date) -> Decimal | None:
    """Return units of quote_ccy per 1 base_ccy at as_of, or None if unknown."""
    if base_ccy == quote_ccy:
        return Decimal(1)
    direct = _period_rate(db, base_ccy, quote_ccy, as_of)
    if direct is not None:
        return direct
    inverse = _period_rate(db, quote_ccy, base_ccy, as_of)
    if inverse is not None and inverse != 0:
        return Decimal(1) / inverse
    return None


def convert(
    db: Session, amount: Decimal, base_ccy: str, quote_ccy: str, as_of: date
) -> Decimal | None:
    """Convert amount from base_ccy to quote_ccy at as_of."""
    rate = get_rate(db, base_ccy, quote_ccy, as_of)
    if rate is None:
        return None
    return Decimal(amount) * rate