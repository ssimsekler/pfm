"""Reporting service: prebuilt analytics computed in the reporting currency (USD).

All monetary aggregates are converted to the reporting currency using the
validity-period FX service (Decision #26/#27). Also provides per-currency
subtotals where useful.
"""

from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.automation import InvestmentHolding
from app.models.financial import Account, ExpenseCategory, Transaction
from app.services import fx

settings = get_settings()


def _reporting_ccy() -> str:
    return settings.app_reporting_currency or "USD"


def _to_reporting(db: Session, amount: Decimal, ccy: str, on: date) -> Decimal:
    converted = fx.convert(db, amount, ccy, _reporting_ccy(), on)
    return converted if converted is not None else Decimal(amount)


def volume_by_category(db: Session, date_from: date | None, date_to: date | None) -> list[dict]:
    """Transaction volume grouped by expense category, in reporting ccy."""
    stmt = select(Transaction).where(Transaction.deleted_at.is_(None))
    if date_from:
        stmt = stmt.where(Transaction.txn_date >= date_from)
    if date_to:
        stmt = stmt.where(Transaction.txn_date <= date_to)
    txns = db.execute(stmt).scalars()

    totals: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
    for t in txns:
        cat_name = "Uncategorized"
        if t.expense_category_id:
            cat = db.get(ExpenseCategory, t.expense_category_id)
            cat_name = cat.name if cat else cat_name
        totals[cat_name] += _to_reporting(db, Decimal(t.amount), t.currency, t.txn_date)

    return [
        {"category": k, "amount": str(v), "currency": _reporting_ccy()}
        for k, v in sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    ]


def volume_by_field(db: Session, field: str, date_from: date | None, date_to: date | None) -> list[dict]:
    """Generic volume by a transaction FK id field (partner_id/beneficiary_id)."""
    stmt = select(Transaction).where(Transaction.deleted_at.is_(None))
    if date_from:
        stmt = stmt.where(Transaction.txn_date >= date_from)
    if date_to:
        stmt = stmt.where(Transaction.txn_date <= date_to)
    txns = db.execute(stmt).scalars()

    totals: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
    for t in txns:
        key = str(getattr(t, field) or "none")
        totals[key] += _to_reporting(db, Decimal(t.amount), t.currency, t.txn_date)
    return [
        {"key": k, "amount": str(v), "currency": _reporting_ccy()}
        for k, v in sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    ]


def cash_position(db: Session, as_of: date | None = None) -> dict:
    """Cash position per account + per-currency subtotals + reporting-ccy total."""
    on = as_of or date.today()
    accounts = db.execute(select(Account).where(Account.deleted_at.is_(None))).scalars()

    per_account = []
    per_currency: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
    total_reporting = Decimal(0)

    for acc in accounts:
        txns = db.execute(
            select(Transaction).where(
                Transaction.account_id == acc.uuid,
                Transaction.deleted_at.is_(None),
                Transaction.txn_date <= on,
            )
        ).scalars()
        balance = Decimal(acc.opening_balance or 0) + sum(
            (Decimal(t.amount) for t in txns), Decimal(0)
        )
        per_currency[acc.currency] += balance
        reporting_val = _to_reporting(db, balance, acc.currency, on)
        total_reporting += reporting_val
        per_account.append({
            "account": acc.name,
            "mnemonic_id": acc.mnemonic_id,
            "currency": acc.currency,
            "balance": str(balance),
            "reporting_amount": str(reporting_val),
        })

    return {
        "as_of": on.isoformat(),
        "reporting_currency": _reporting_ccy(),
        "accounts": per_account,
        "per_currency": {k: str(v) for k, v in per_currency.items()},
        "total_reporting": str(total_reporting),
    }


def net_worth(db: Session, as_of: date | None = None) -> dict:
    """Net worth in reporting ccy = account balances (incl. negative liabilities) + investments.

    Credit-card/loan accounts carry negative balances via their transactions, so
    liabilities are already netted into the account balances.
    """
    on = as_of or date.today()
    cash = cash_position(db, on)
    assets = Decimal(cash["total_reporting"])

    holdings = db.execute(
        select(InvestmentHolding).where(InvestmentHolding.deleted_at.is_(None))
    ).scalars()
    investments = Decimal(0)
    for h in holdings:
        if h.current_value_cache is not None:
            investments += _to_reporting(
                db, Decimal(h.current_value_cache), h.currency or _reporting_ccy(), on
            )

    return {
        "as_of": on.isoformat(),
        "reporting_currency": _reporting_ccy(),
        "cash_and_accounts": cash["total_reporting"],
        "investments": str(investments),
        "net_worth": str(assets + investments),
    }