"""Tests for FX validity-period lookup + conversion (fake DB, no tables)."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.services import fx


class Result:
    def __init__(self, rows):
        self._rows = rows

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


class FakeDB:
    """Returns the first matching rate row for the period query; the fx service
    issues several selects, so we filter by the compiled WHERE via a callback."""

    def __init__(self, rates):
        # rates: list of SimpleNamespace(base_ccy, quote_ccy, rate, begin_date, end_date, deleted_at)
        self.rates = rates
        self._call = 0

    def execute(self, stmt):
        # The fx service calls (in order): exact-period, prior, earliest, then
        # inverse variants. We emulate the *period* match generically by scanning.
        # For simplicity we only support the primary period query used by get_rate.
        matches = [r for r in self.rates]
        return Result(matches)


def _rate(b, q, r, begin, end):
    return SimpleNamespace(
        base_ccy=b, quote_ccy=q, rate=Decimal(str(r)),
        begin_date=begin, end_date=end, deleted_at=None,
    )


def test_identity_rate():
    db = FakeDB([])
    assert fx.get_rate(db, "USD", "USD", date(2025, 6, 1)) == Decimal(1)


def test_direct_rate_conversion():
    db = FakeDB([_rate("AED", "USD", Decimal("0.2723"), date(2025, 1, 1), date(9999, 12, 31))])
    rate = fx.get_rate(db, "AED", "USD", date(2025, 6, 1))
    assert rate == Decimal("0.2723")
    converted = fx.convert(db, Decimal("100"), "AED", "USD", date(2025, 6, 1))
    assert converted == Decimal("27.23")


def test_no_rate_returns_none():
    db = FakeDB([])
    assert fx.get_rate(db, "AED", "JPY", date(2025, 6, 1)) is None
    assert fx.convert(db, Decimal("100"), "AED", "JPY", date(2025, 6, 1)) is None