"""Canonical connector framework for external data (Decision #18).

Each scenario (FX_RATES, STOCK_QUOTE, CRYPTO_QUOTE) resolves its endpoint from
the `integration_endpoint` registry at runtime; if none is configured, a sensible
public default is used. All connectors return simple dicts so sources are swappable.
"""

from datetime import date
from decimal import Decimal

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.automation import IntegrationEndpoint

# Public defaults (no API key required) when no endpoint is configured.
DEFAULTS = {
    "FX_RATES": "https://api.frankfurter.app",
    "CRYPTO_QUOTE": "https://api.coingecko.com/api/v3",
    "STOCK_QUOTE": "https://query1.finance.yahoo.com",
}


def _endpoint(db: Session, scenario_key: str) -> IntegrationEndpoint | None:
    stmt = (
        select(IntegrationEndpoint)
        .where(
            IntegrationEndpoint.scenario_key == scenario_key,
            IntegrationEndpoint.enabled.is_(True),
            IntegrationEndpoint.deleted_at.is_(None),
        )
        .order_by(IntegrationEndpoint.priority.asc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def _base_url(db: Session, scenario_key: str) -> str:
    ep = _endpoint(db, scenario_key)
    if ep and ep.base_url:
        return ep.base_url.rstrip("/")
    return DEFAULTS[scenario_key]


def fetch_fx_rate(db: Session, base_ccy: str, quote_ccy: str, on: date | None = None) -> Decimal | None:
    """Fetch FX rate (quote per 1 base) from the configured FX source (Frankfurter-style)."""
    base_url = _base_url(db, "FX_RATES")
    day = (on or date.today()).isoformat()
    try:
        resp = httpx.get(
            f"{base_url}/{day}",
            params={"from": base_ccy, "to": quote_ccy},
            timeout=8.0,
        )
        resp.raise_for_status()
        data = resp.json()
        rate = data.get("rates", {}).get(quote_ccy)
        return Decimal(str(rate)) if rate is not None else None
    except Exception:  # noqa: BLE001
        return None


def fetch_crypto_price(db: Session, coin_id: str, vs_currency: str = "usd") -> Decimal | None:
    """Fetch crypto spot price (CoinGecko-style)."""
    base_url = _base_url(db, "CRYPTO_QUOTE")
    try:
        resp = httpx.get(
            f"{base_url}/simple/price",
            params={"ids": coin_id, "vs_currencies": vs_currency},
            timeout=8.0,
        )
        resp.raise_for_status()
        data = resp.json()
        price = data.get(coin_id, {}).get(vs_currency)
        return Decimal(str(price)) if price is not None else None
    except Exception:  # noqa: BLE001
        return None


def fetch_stock_price(db: Session, symbol: str) -> Decimal | None:
    """Fetch latest stock/ETF price (Yahoo Finance chart endpoint)."""
    base_url = _base_url(db, "STOCK_QUOTE")
    try:
        resp = httpx.get(
            f"{base_url}/v8/finance/chart/{symbol}",
            params={"interval": "1d", "range": "1d"},
            timeout=8.0,
        )
        resp.raise_for_status()
        data = resp.json()
        result = data.get("chart", {}).get("result", [])
        if not result:
            return None
        meta = result[0].get("meta", {})
        price = meta.get("regularMarketPrice")
        return Decimal(str(price)) if price is not None else None
    except Exception:  # noqa: BLE001
        return None