"""Consolidated unit tests: FX lookup, SQL-console guard, rules matcher,
import dedup hash. (Kept in one module to minimise file churn.)"""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services import fx, import_mapper, rules, sql_console


# --------------------------------------------------------------------------- #
# FX validity-period lookup + conversion
# --------------------------------------------------------------------------- #
class _FxResult:
    def __init__(self, rows):
        self._rows = rows

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


class _FxDB:
    def __init__(self, rates):
        self.rates = rates

    def execute(self, _stmt):
        return _FxResult(list(self.rates))


def _rate(b, q, r):
    return SimpleNamespace(
        base_ccy=b, quote_ccy=q, rate=Decimal(str(r)),
        begin_date=date(2025, 1, 1), end_date=date(9999, 12, 31), deleted_at=None,
    )


def test_fx_identity():
    assert fx.get_rate(_FxDB([]), "USD", "USD", date(2025, 6, 1)) == Decimal(1)


def test_fx_direct_and_convert():
    db = _FxDB([_rate("AED", "USD", "0.2723")])
    assert fx.get_rate(db, "AED", "USD", date(2025, 6, 1)) == Decimal("0.2723")
    assert fx.convert(db, Decimal("100"), "AED", "USD", date(2025, 6, 1)) == Decimal("27.23")


def test_fx_missing_returns_none():
    db = _FxDB([])
    assert fx.get_rate(db, "AED", "JPY", date(2025, 6, 1)) is None
    assert fx.convert(db, Decimal("100"), "AED", "JPY", date(2025, 6, 1)) is None


# --------------------------------------------------------------------------- #
# SQL console guard
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO pfm.account VALUES (1)",
        "UPDATE pfm.account SET name='x'",
        "DELETE FROM pfm.account",
        "DROP TABLE pfm.account",
        "SELECT 1; SELECT 2",
        "TRUNCATE pfm.account",
        "EXPLAIN SELECT 1",
    ],
)
def test_sql_console_rejects(sql):
    with pytest.raises(ValueError):
        sql_console.run_query(sql)


# --------------------------------------------------------------------------- #
# Categorization rules matcher
# --------------------------------------------------------------------------- #
def test_rules_eq():
    assert rules._match({"currency": "AED"}, {"currency": "AED"}) is True
    assert rules._match({"currency": "USD"}, {"currency": "AED"}) is False


def test_rules_contains_and_amount():
    txn = {"description": "STARBUCKS", "amount": 30}
    assert rules._match({"description_contains": "starbucks", "amount_lt": 50}, txn) is True
    assert rules._match({"description_contains": "tesco"}, txn) is False
    assert rules._match({"amount_gt": 100}, txn) is False


# --------------------------------------------------------------------------- #
# Import dedup hash
# --------------------------------------------------------------------------- #
def test_dedup_hash_stable_and_case_insensitive():
    a = import_mapper.dedup_hash({"date": "2025-01-01", "amount": -50, "partner": "TESCO"})
    b = import_mapper.dedup_hash({"date": "2025-01-01", "amount": -50, "partner": "tesco"})
    c = import_mapper.dedup_hash({"date": "2025-01-01", "amount": -51, "partner": "tesco"})
    assert a == b
    assert a != c
    assert len(a) == 64