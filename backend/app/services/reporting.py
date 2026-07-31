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
from app.models.financial import (
    Account,
    Beneficiary,
    CashFlowItem,
    ExpenseCategory,
    Partner,
    Transaction,
)
from app.models.meta import CodeValue
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
    """Generic volume by a transaction FK id field (partner_id/beneficiary_id).

    Session 742, Bug 5: resolve the FK to a human **label** (partner/beneficiary
    name; null → "Unassigned") so charts show names, not UUIDs.
    """
    model = {"partner_id": Partner, "beneficiary_id": Beneficiary}.get(field)

    stmt = select(Transaction).where(Transaction.deleted_at.is_(None))
    if date_from:
        stmt = stmt.where(Transaction.txn_date >= date_from)
    if date_to:
        stmt = stmt.where(Transaction.txn_date <= date_to)
    txns = db.execute(stmt).scalars()

    totals: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
    label_cache: dict[str, str] = {}
    for t in txns:
        fk = getattr(t, field)
        key = str(fk) if fk else "none"
        if key not in label_cache:
            if fk and model is not None:
                obj = db.get(model, fk)
                label_cache[key] = (obj.name if obj else None) or "Unassigned"
            else:
                label_cache[key] = "Unassigned"
        totals[key] += _to_reporting(db, Decimal(t.amount), t.currency, t.txn_date)
    return [
        {"key": k, "label": label_cache.get(k, "Unassigned"), "amount": str(v), "currency": _reporting_ccy()}
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


def monthly_trend(db: Session, date_from: date | None, date_to: date | None) -> dict:
    """Income vs. expense per calendar month (YYYY-MM) in reporting ccy.

    Direction is inferred from the linked cash-flow item's flow_type when present,
    otherwise from the sign of the amount (>=0 income, <0 expense).
    """
    stmt = select(Transaction).where(Transaction.deleted_at.is_(None))
    if date_from:
        stmt = stmt.where(Transaction.txn_date >= date_from)
    if date_to:
        stmt = stmt.where(Transaction.txn_date <= date_to)
    txns = db.execute(stmt).scalars()

    # Cache flow_type code → "income"/"expense".
    flow_code_cache: dict[str, str] = {}

    def _flow_for(item_id) -> str | None:
        if not item_id:
            return None
        item = db.get(CashFlowItem, item_id)
        if item is None or item.flow_type_cv_id is None:
            return None
        key = str(item.flow_type_cv_id)
        if key not in flow_code_cache:
            cv = db.get(CodeValue, item.flow_type_cv_id)
            flow_code_cache[key] = (cv.code if cv else "") or ""
        return flow_code_cache[key] or None

    income: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
    expense: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
    for t in txns:
        month = t.txn_date.strftime("%Y-%m")
        val = _to_reporting(db, Decimal(t.amount), t.currency, t.txn_date)
        flow = _flow_for(t.cash_flow_item_id)
        is_income = flow == "income" if flow else (val >= 0)
        if is_income:
            income[month] += abs(val)
        else:
            expense[month] += abs(val)

    months = sorted(set(income) | set(expense))
    series = [
        {
            "month": m,
            "income": str(income.get(m, Decimal(0))),
            "expense": str(expense.get(m, Decimal(0))),
            "net": str(income.get(m, Decimal(0)) - expense.get(m, Decimal(0))),
        }
        for m in months
    ]
    return {"reporting_currency": _reporting_ccy(), "series": series}


def _add_months(d: date, n: int) -> date:
    """Return the last day of the month `n` months after `d`'s month."""
    import calendar

    y = d.year + (d.month - 1 + n) // 12
    m = (d.month - 1 + n) % 12 + 1
    last = calendar.monthrange(y, m)[1]
    return date(y, m, last)


def cash_projection(db: Session, budget_id, months: int) -> dict:
    """Month-end cash / investments / loans / net projection for N months (Bug 23).

    Starting point = current cash position + investments + outstanding loan balances.
    Each future month applies the selected budget's net flow (income − expense from
    its lines) to cash, and reduces the outstanding loan balance by that month's
    scheduled principal (from generated amortization schedules).
    """
    from app.models import budgeting as bud
    from app.models import scheduling as sch

    months = max(1, min(int(months or 12), 120))
    today = date.today()

    # --- Starting balances (reporting ccy) ---
    cash0 = Decimal(cash_position(db, today)["total_reporting"])
    nw = net_worth(db, today)
    inv0 = Decimal(nw["investments"])

    # Outstanding loan balances = sum of the latest amortization balance per loan.
    loans = db.execute(select(sch.Loan).where(sch.Loan.deleted_at.is_(None))).scalars()
    loan_balance0 = Decimal(0)
    principal_by_month: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
    for loan in loans:
        rows = list(
            db.execute(
                select(sch.AmortizationSchedule)
                .where(sch.AmortizationSchedule.loan_id == loan.uuid)
                .order_by(sch.AmortizationSchedule.period)
            ).scalars()
        )
        if not rows:
            continue
        # Current outstanding = balance of the last period whose due_date <= today,
        # else the loan principal if none due yet.
        past = [r for r in rows if r.due_date <= today]
        current_bal = Decimal(past[-1].balance) if past else Decimal(loan.principal or 0)
        loan_balance0 += _to_reporting(db, current_bal, loan.currency or _reporting_ccy(), today)
        # Future principal payments bucketed by YYYY-MM.
        for r in rows:
            if r.due_date > today:
                key = r.due_date.strftime("%Y-%m")
                principal_by_month[key] += _to_reporting(
                    db, Decimal(r.principal_portion or 0), loan.currency or _reporting_ccy(), r.due_date
                )

    # --- Budget monthly net flow ---
    monthly_net = Decimal(0)
    if budget_id is not None:
        budget = db.get(bud.Budget, budget_id)
        if budget is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="budget not found")
        lines = list(
            db.execute(select(bud.BudgetLine).where(bud.BudgetLine.budget_id == budget_id)).scalars()
        )
        # Determine direction sign per line (credit/income = +, debit/expense = −).
        for ln in lines:
            amt = Decimal(ln.expected_amount or 0)
            sign = Decimal(1)
            if ln.direction_cv_id is not None:
                cv = db.get(CodeValue, ln.direction_cv_id)
                code = (cv.code if cv else "") or ""
                sign = Decimal(1) if code in ("credit", "income") else Decimal(-1)
            monthly_net += sign * amt

    # --- Project forward ---
    cash = cash0
    inv = inv0
    loan_bal = loan_balance0
    series = []
    for i in range(1, months + 1):
        me = _add_months(today, i)
        key = me.strftime("%Y-%m")
        cash += monthly_net
        loan_bal -= principal_by_month.get(key, Decimal(0))
        if loan_bal < 0:
            loan_bal = Decimal(0)
        net = cash + inv - loan_bal
        series.append({
            "month": key,
            "cash": str(cash.quantize(Decimal("0.01"))),
            "investments": str(inv.quantize(Decimal("0.01"))),
            "loans": str(loan_bal.quantize(Decimal("0.01"))),
            "net": str(net.quantize(Decimal("0.01"))),
        })

    return {
        "reporting_currency": _reporting_ccy(),
        "months": months,
        "monthly_net_flow": str(monthly_net.quantize(Decimal("0.01"))),
        "start": {
            "cash": str(cash0.quantize(Decimal("0.01"))),
            "investments": str(inv0.quantize(Decimal("0.01"))),
            "loans": str(loan_balance0.quantize(Decimal("0.01"))),
        },
        "series": series,
    }
