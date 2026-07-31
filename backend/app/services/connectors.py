"""Canonical connector framework for external data (Decision #18).

Each scenario (FX_RATES, STOCK_QUOTE, CRYPTO_QUOTE) resolves its endpoint from
the `integration_endpoint` registry at runtime; if none is configured, a sensible
public default is used. All connectors return simple dicts/Decimals so sources
are swappable.

Session 815 (Items 3, 15):
  - FX now supports an **arbitrary base currency** (e.g. AED). Frankfurter only
    supports ECB base currencies, so for a base-agnostic result we prefer
    open.er-api.com / exchangerate.host, and fall back to a **EUR cross-rate**
    via Frankfurter when needed. `fetch_fx_rate` returns None only when no source
    can produce the pair.
  - Stock quotes send a browser **User-Agent** (Yahoo now rejects UA-less calls)
    and fall back to **Stooq** when Yahoo yields nothing.
"""

from datetime import date
from decimal import Decimal

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.automation import IntegrationEndpoint

# Public defaults (no API key required) when no endpoint is configured.
DEFAULTS = {
    # Base-agnostic FX (supports AED and most ISO currencies as base).
    "FX_RATES": "https://open.er-api.com/v6",
    "CRYPTO_QUOTE": "https://api.coingecko.com/api/v3",
    "STOCK_QUOTE": "https://query1.finance.yahoo.com",
}

# Frankfurter (ECB) supported currencies — used to decide whether we can call it
# directly or must compute a EUR cross-rate.
_FRANKFURTER_CCYS = {
    "EUR", "USD", "JPY", "BGN", "CZK", "DKK", "GBP", "HUF", "PLN", "RON", "SEK",
    "CHF", "ISK", "NOK", "HRK", "TRY", "AUD", "BRL", "CAD", "CNY", "HKD", "IDR",
    "ILS", "INR", "KRW", "MXN", "MYR", "NZD", "PHP", "SGD", "THB", "ZAR",
}

# A browser-like User-Agent so Yahoo/other sources don't reject the request.
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


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


# ---------------------------------------------------------------------------
# FX rates (Item 3): base-agnostic, with cross-rate fallback.
# ---------------------------------------------------------------------------
# open.er-api.com is the reliable, keyless base-agnostic default. We ALWAYS try
# it, even if a (possibly wrong) endpoint is configured in the DB (Batch 10 fix:
# a seeded FX_RATES row pointing at frankfurter.app was overriding this and
# breaking every refresh).
_ERAPI_DEFAULT = "https://open.er-api.com/v6"


def _fetch_erapi(base_url: str, base_ccy: str, quote_ccy: str) -> Decimal | None:
    """open.er-api.com style: /latest/{BASE} → {"rates": {...}} (or conversion_rates)."""
    for path in (f"{base_url}/latest/{base_ccy}", f"{base_url}/{base_ccy}"):
        try:
            resp = httpx.get(
                path, timeout=8.0, headers={"User-Agent": _UA}, follow_redirects=True
            )
            resp.raise_for_status()
            data = resp.json()
            # Only treat as er-api-shaped when a rates map is actually present
            # (a Frankfurter/other URL won't have this, so we skip it cleanly).
            rates = data.get("rates") or data.get("conversion_rates")
            if not isinstance(rates, dict):
                continue
            rate = rates.get(quote_ccy)
            if rate is not None:
                return Decimal(str(rate))
        except Exception:  # noqa: BLE001
            continue
    return None


def _fetch_exchangerate_host(base_ccy: str, quote_ccy: str, on: date | None) -> Decimal | None:
    """exchangerate.host supports an arbitrary base and historical dates."""
    day = (on or date.today()).isoformat()
    try:
        resp = httpx.get(
            f"https://api.exchangerate.host/{day}",
            params={"base": base_ccy, "symbols": quote_ccy},
            timeout=8.0,
            headers={"User-Agent": _UA},
        )
        resp.raise_for_status()
        rate = (resp.json().get("rates") or {}).get(quote_ccy)
        return Decimal(str(rate)) if rate is not None else None
    except Exception:  # noqa: BLE001
        return None


def _fetch_frankfurter_direct(base_ccy: str, quote_ccy: str, on: date | None) -> Decimal | None:
    day = (on or date.today()).isoformat()
    try:
        resp = httpx.get(
            f"https://api.frankfurter.app/{day}",
            params={"from": base_ccy, "to": quote_ccy},
            timeout=8.0,
            headers={"User-Agent": _UA},
        )
        resp.raise_for_status()
        rate = (resp.json().get("rates") or {}).get(quote_ccy)
        return Decimal(str(rate)) if rate is not None else None
    except Exception:  # noqa: BLE001
        return None


def _fetch_frankfurter_cross(base_ccy: str, quote_ccy: str, on: date | None) -> Decimal | None:
    """Compute base→quote via EUR when Frankfurter can't use `base_ccy` as base.

    rate(base→quote) = rate(EUR→quote) / rate(EUR→base).
    """
    day = (on or date.today()).isoformat()
    try:
        symbols = ",".join(sorted({base_ccy, quote_ccy} - {"EUR"}))
        resp = httpx.get(
            f"https://api.frankfurter.app/{day}",
            params={"from": "EUR", "to": symbols} if symbols else {"from": "EUR"},
            timeout=8.0,
            headers={"User-Agent": _UA},
        )
        resp.raise_for_status()
        rates = resp.json().get("rates") or {}
        eur_to_base = Decimal(1) if base_ccy == "EUR" else (
            Decimal(str(rates[base_ccy])) if base_ccy in rates else None
        )
        eur_to_quote = Decimal(1) if quote_ccy == "EUR" else (
            Decimal(str(rates[quote_ccy])) if quote_ccy in rates else None
        )
        if eur_to_base and eur_to_quote and eur_to_base != 0:
            return eur_to_quote / eur_to_base
    except Exception:  # noqa: BLE001
        return None
    return None


def fetch_fx_rate(db: Session, base_ccy: str, quote_ccy: str, on: date | None = None) -> Decimal | None:
    """Fetch FX rate (units of quote per 1 base) from the best available source.

    Order: configured/default base-agnostic source → exchangerate.host →
    Frankfurter (direct if base is ECB-supported, else EUR cross-rate). Returns
    None only when no source can produce the pair.
    """
    base_ccy = (base_ccy or "").upper()
    quote_ccy = (quote_ccy or "").upper()
    if not base_ccy or not quote_ccy:
        return None
    if base_ccy == quote_ccy:
        return Decimal(1)

    base_url = _base_url(db, "FX_RATES")

    # 1) Base-agnostic er-api source. Always try the reliable built-in default,
    #    plus any configured endpoint (in case it's a valid er-api mirror). This
    #    guarantees a wrong/legacy configured endpoint can't break the refresh.
    for url in dict.fromkeys([_ERAPI_DEFAULT, base_url]):  # de-dupe, keep order
        rate = _fetch_erapi(url, base_ccy, quote_ccy)
        if rate is not None:
            return rate

    # 2) exchangerate.host (arbitrary base, supports historical `on`).
    rate = _fetch_exchangerate_host(base_ccy, quote_ccy, on)
    if rate is not None:
        return rate

    # 3) Frankfurter — direct if it supports the base, else EUR cross-rate.
    if base_ccy in _FRANKFURTER_CCYS and quote_ccy in _FRANKFURTER_CCYS:
        rate = _fetch_frankfurter_direct(base_ccy, quote_ccy, on)
        if rate is not None:
            return rate
    if (base_ccy in _FRANKFURTER_CCYS or base_ccy == "EUR") and (
        quote_ccy in _FRANKFURTER_CCYS or quote_ccy == "EUR"
    ):
        rate = _fetch_frankfurter_cross(base_ccy, quote_ccy, on)
        if rate is not None:
            return rate

    return None


def fetch_crypto_price(db: Session, coin_id: str, vs_currency: str = "usd") -> Decimal | None:
    """Fetch crypto spot price (CoinGecko-style)."""
    base_url = _base_url(db, "CRYPTO_QUOTE")
    try:
        resp = httpx.get(
            f"{base_url}/simple/price",
            params={"ids": coin_id, "vs_currencies": vs_currency},
            timeout=8.0,
            headers={"User-Agent": _UA},
        )
        resp.raise_for_status()
        data = resp.json()
        price = data.get(coin_id, {}).get(vs_currency)
        return Decimal(str(price)) if price is not None else None
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# Stock quotes (Item 15): Yahoo with a UA + Stooq fallback.
# ---------------------------------------------------------------------------
def _fetch_yahoo(base_url: str, symbol: str) -> Decimal | None:
    try:
        resp = httpx.get(
            f"{base_url}/v8/finance/chart/{symbol}",
            params={"interval": "1d", "range": "1d"},
            timeout=8.0,
            headers={"User-Agent": _UA, "Accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
        result = (data.get("chart", {}) or {}).get("result") or []
        if not result:
            return None
        meta = result[0].get("meta", {}) or {}
        price = meta.get("regularMarketPrice")
        return Decimal(str(price)) if price is not None else None
    except Exception:  # noqa: BLE001
        return None


def _fetch_stooq(symbol: str) -> Decimal | None:
    """Stooq CSV fallback. Stooq uses lowercase symbols with a `.us` suffix for
    US tickers (e.g. `msft.us`); strip any exchange suffix like `MSFT:NASDAQ`."""
    sym = symbol.split(":")[0].strip().lower()
    candidates = [sym]
    if "." not in sym:
        candidates.append(f"{sym}.us")  # default US listing
    for s in candidates:
        try:
            resp = httpx.get(
                "https://stooq.com/q/l/",
                params={"s": s, "f": "sd2t2ohlcv", "h": "", "e": "csv"},
                timeout=8.0,
                headers={"User-Agent": _UA},
            )
            resp.raise_for_status()
            lines = resp.text.strip().splitlines()
            if len(lines) < 2:
                continue
            header = [h.strip().lower() for h in lines[0].split(",")]
            values = lines[1].split(",")
            row = dict(zip(header, values))
            close = row.get("close")
            if close and close not in ("N/D", ""):
                return Decimal(str(close))
        except Exception:  # noqa: BLE001
            continue
    return None


def fetch_stock_price(db: Session, symbol: str) -> Decimal | None:
    """Fetch latest stock/ETF price. Tries the configured/Yahoo source first
    (with a browser User-Agent), then falls back to Stooq. Returns None only when
    no source can price the symbol (the caller then surfaces a helpful 422)."""
    if not symbol:
        return None
    base_url = _base_url(db, "STOCK_QUOTE")
    price = _fetch_yahoo(base_url, symbol)
    if price is not None:
        return price
    # Yahoo sometimes needs the bare ticker (strip an exchange suffix like :NASDAQ).
    if ":" in symbol:
        price = _fetch_yahoo(base_url, symbol.split(":")[0])
        if price is not None:
            return price
    return _fetch_stooq(symbol)
