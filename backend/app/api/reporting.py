"""Phase 6 API: budgets (+ lines + variance + recommendations), prebuilt reports,
projection, and the read-only SQL console."""

import uuid as uuid_lib
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.crud_router import build_crud_router
from app.api.schemas import EntityOut, ORMModel
from app.core.database import get_db
from app.core.security import Principal, get_current_principal, require_write
from app.models import budgeting as bud
from app.models import financial as fin
from app.services import llm_gateway, reporting, sql_console


# ---------------------------------------------------------------------------
# Budget CRUD
# ---------------------------------------------------------------------------
class BudgetOut(EntityOut):
    period_start: date
    period_end: date
    base_currency: str | None = None


class BudgetCreate(ORMModel):
    name: str
    description: str | None = None
    period_start: date
    period_end: date
    base_currency: str | None = None


class BudgetUpdate(ORMModel):
    name: str | None = None
    description: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    base_currency: str | None = None


budget_router = build_crud_router(
    prefix="/api/v1/budgets", tag="budgets", model=bud.Budget,
    entity_type="budget", event_domain="budget",
    out_schema=BudgetOut, create_schema=BudgetCreate, update_schema=BudgetUpdate,
)


class BudgetLineIn(BaseModel):
    cash_flow_item_id: uuid_lib.UUID | None = None
    expense_category_id: uuid_lib.UUID | None = None
    direction_cv_id: uuid_lib.UUID | None = None
    expected_amount: Decimal = Decimal(0)


class BudgetLineOut(BudgetLineIn):
    uuid: uuid_lib.UUID
    budget_id: uuid_lib.UUID

    class Config:
        from_attributes = True


@budget_router.post("/{budget_id}/lines", response_model=BudgetLineOut, status_code=201)
def add_budget_line(
    budget_id: uuid_lib.UUID,
    payload: BudgetLineIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_write),
):
    """Add a budget line. A line is **either** driven by a cash-flow item (its
    category + direction are inherited) **or** a category+direction pair — exactly
    one mode (Session 742, Bug 12)."""
    if db.get(bud.Budget, budget_id) is None:
        raise HTTPException(status_code=404, detail="budget not found")

    data = payload.model_dump()
    if data.get("cash_flow_item_id"):
        # Item-driven: inherit category + direction from the item; ignore any
        # explicitly-passed category/direction to avoid conflicts.
        item = db.get(fin.CashFlowItem, data["cash_flow_item_id"])
        if item is None:
            raise HTTPException(status_code=422, detail="cash_flow_item not found")
        data["expense_category_id"] = item.expense_category_id
        data["direction_cv_id"] = item.flow_type_cv_id
    else:
        # Category+direction mode: both are required when no item is chosen.
        if not data.get("expense_category_id") or not data.get("direction_cv_id"):
            raise HTTPException(
                status_code=422,
                detail="Provide a Cash Flow Item, or both a Category and a Direction.",
            )

    line = bud.BudgetLine(budget_id=budget_id, **data)
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


@budget_router.get("/{budget_id}/lines", response_model=list[BudgetLineOut])
def list_budget_lines(
    budget_id: uuid_lib.UUID,
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
):
    stmt = select(bud.BudgetLine).where(bud.BudgetLine.budget_id == budget_id)
    return list(db.execute(stmt).scalars())


@budget_router.delete("/{budget_id}/lines/{line_id}")
def delete_budget_line(
    budget_id: uuid_lib.UUID,
    line_id: uuid_lib.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_write),
):
    line = db.get(bud.BudgetLine, line_id)
    if line is None or line.budget_id != budget_id:
        raise HTTPException(status_code=404, detail="budget line not found")
    db.delete(line)
    db.commit()
    return {"deleted": True, "uuid": str(line_id)}


@budget_router.get("/{budget_id}/variance")
def budget_variance(
    budget_id: uuid_lib.UUID,
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
):
    """Budget vs. actual per line over the budget period (actuals in reporting ccy)."""
    budget = db.get(bud.Budget, budget_id)
    if budget is None:
        raise HTTPException(status_code=404, detail="budget not found")
    lines = list(db.execute(
        select(bud.BudgetLine).where(bud.BudgetLine.budget_id == budget_id)
    ).scalars())

    results = []
    total_budget = Decimal(0)
    total_actual = Decimal(0)
    for line in lines:
        actual = Decimal(0)
        if line.expense_category_id:
            txns = db.execute(
                select(fin.Transaction).where(
                    fin.Transaction.expense_category_id == line.expense_category_id,
                    fin.Transaction.txn_date >= budget.period_start,
                    fin.Transaction.txn_date <= budget.period_end,
                    fin.Transaction.deleted_at.is_(None),
                )
            ).scalars()
            for t in txns:
                actual += reporting._to_reporting(db, Decimal(t.amount), t.currency, t.txn_date)
        expected = Decimal(line.expected_amount or 0)
        total_budget += expected
        total_actual += actual
        results.append({
            "line": str(line.uuid),
            "expense_category_id": str(line.expense_category_id) if line.expense_category_id else None,
            "expected": str(expected),
            "actual": str(actual),
            "variance": str(expected - actual),
        })

    return {
        "budget": budget.mnemonic_id,
        "period": [budget.period_start.isoformat(), budget.period_end.isoformat()],
        "reporting_currency": reporting._reporting_ccy(),
        "lines": results,
        "total_expected": str(total_budget),
        "total_actual": str(total_actual),
        "total_variance": str(total_budget - total_actual),
    }


@budget_router.get("/{budget_id}/recommendations")
def budget_recommendations(
    budget_id: uuid_lib.UUID,
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
):
    """Recommend budget lines from recent spend per category (+ optional LLM commentary)."""
    budget = db.get(bud.Budget, budget_id)
    if budget is None:
        raise HTTPException(status_code=404, detail="budget not found")
    recent = reporting.volume_by_category(db, budget.period_start, budget.period_end)
    commentary = llm_gateway.complete(
        db, "BUDGET_RECO",
        prompt=f"Suggest a monthly budget given these category totals: {recent}",
    )
    return {"suggested_lines": recent, "commentary": commentary}


# ---------------------------------------------------------------------------
# Prebuilt reports
# ---------------------------------------------------------------------------
report_router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@report_router.get("/volume-by-category")
def report_volume_by_category(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
):
    return {"items": reporting.volume_by_category(db, date_from, date_to)}


@report_router.get("/volume-by-partner")
def report_volume_by_partner(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
):
    return {"items": reporting.volume_by_field(db, "partner_id", date_from, date_to)}


@report_router.get("/volume-by-beneficiary")
def report_volume_by_beneficiary(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
):
    return {"items": reporting.volume_by_field(db, "beneficiary_id", date_from, date_to)}


@report_router.get("/monthly-trend")
def report_monthly_trend(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
):
    """Income vs. expense per month (reporting ccy) for a trend line chart."""
    return reporting.monthly_trend(db, date_from, date_to)


@report_router.get("/cash-position")
def report_cash_position(
    as_of: date | None = Query(None),
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
):
    return reporting.cash_position(db, as_of)


@report_router.get("/net-worth")
def report_net_worth(
    as_of: date | None = Query(None),
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
):
    return reporting.net_worth(db, as_of)


@report_router.get("/projection")
def report_projection(
    budget_id: uuid_lib.UUID,
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
):
    """Future projection: current net worth + net of a budget's income/expense lines."""
    budget = db.get(bud.Budget, budget_id)
    if budget is None:
        raise HTTPException(status_code=404, detail="budget not found")
    current = reporting.net_worth(db)
    lines = list(db.execute(
        select(bud.BudgetLine).where(bud.BudgetLine.budget_id == budget_id)
    ).scalars())
    net_flow = sum((Decimal(ln.expected_amount or 0) for ln in lines), Decimal(0))
    projected = Decimal(current["net_worth"]) + net_flow
    return {
        "as_of_start": current["as_of"],
        "budget": budget.mnemonic_id,
        "current_net_worth": current["net_worth"],
        "budget_net_flow": str(net_flow),
        "projected_net_worth": str(projected),
        "reporting_currency": reporting._reporting_ccy(),
    }


# ---------------------------------------------------------------------------
# Read-only SQL console (Decision #10 / spec 6.2)
# ---------------------------------------------------------------------------
class SqlIn(BaseModel):
    sql: str


@report_router.post("/sql")
def run_sql(
    payload: SqlIn,
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
):
    try:
        return sql_console.run_query(payload.sql)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Query error: {exc}") from exc


ALL_ROUTERS = [budget_router, report_router]