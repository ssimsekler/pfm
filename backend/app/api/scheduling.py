"""Phase 3 API: recurrence, holidays, installments, loans, goals,
plus pending-recurring listing and materialize-to-transaction (spec 1.4.1)."""

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
from app.models import financial as fin
from app.models import scheduling as sch
from app.services import recurrence, schedules
from app.services.auto_account import ensure_backing_account
from app.services.repository import Repository

# ---------------------------------------------------------------------------
# Holiday calendar (+ days)
# ---------------------------------------------------------------------------
class HolidayCalendarOut(EntityOut):
    weekend_days: list[int] | None = None
    week_start: int | None = None


class HolidayCalendarCreate(ORMModel):
    name: str
    description: str | None = None
    weekend_days: list[int] | None = None
    week_start: int | None = None


class HolidayCalendarUpdate(ORMModel):
    name: str | None = None
    description: str | None = None
    weekend_days: list[int] | None = None
    week_start: int | None = None


holiday_calendar_router = build_crud_router(
    prefix="/api/v1/holiday-calendars", tag="holiday-calendars", model=sch.HolidayCalendar,
    entity_type="holiday_calendar", event_domain="holiday_calendar",
    out_schema=HolidayCalendarOut, create_schema=HolidayCalendarCreate,
    update_schema=HolidayCalendarUpdate,
)


class HolidayDayIn(BaseModel):
    holiday_date: date
    label: str | None = None


class HolidayDayOut(HolidayDayIn):
    uuid: uuid_lib.UUID
    calendar_id: uuid_lib.UUID

    class Config:
        from_attributes = True


@holiday_calendar_router.post("/{calendar_id}/days", response_model=HolidayDayOut, status_code=201)
def add_holiday_day(
    calendar_id: uuid_lib.UUID,
    payload: HolidayDayIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_write),
):
    if db.get(sch.HolidayCalendar, calendar_id) is None:
        raise HTTPException(status_code=404, detail="holiday calendar not found")
    row = sch.HolidayCalendarDay(
        calendar_id=calendar_id, holiday_date=payload.holiday_date, label=payload.label
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@holiday_calendar_router.get("/{calendar_id}/days", response_model=list[HolidayDayOut])
def list_holiday_days(
    calendar_id: uuid_lib.UUID,
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
):
    stmt = select(sch.HolidayCalendarDay).where(
        sch.HolidayCalendarDay.calendar_id == calendar_id
    ).order_by(sch.HolidayCalendarDay.holiday_date)
    return list(db.execute(stmt).scalars())


@holiday_calendar_router.delete("/{calendar_id}/days/{day_id}", status_code=204)
def delete_holiday_day(
    calendar_id: uuid_lib.UUID,
    day_id: uuid_lib.UUID,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_write),
):
    row = db.get(sch.HolidayCalendarDay, day_id)
    if row is None or row.calendar_id != calendar_id:
        raise HTTPException(status_code=404, detail="holiday day not found")
    db.delete(row)
    db.commit()
    return None


# ---------------------------------------------------------------------------
# Recurrence profile (+ preview occurrences)
# ---------------------------------------------------------------------------
class RecurrenceProfileOut(EntityOut):
    frequency_type_cv_id: uuid_lib.UUID | None = None
    config: dict | None = None
    start_date: date
    end_date: date | None = None
    business_day_rule_cv_id: uuid_lib.UUID | None = None
    holiday_calendar_id: uuid_lib.UUID | None = None


class RecurrenceProfileCreate(ORMModel):
    name: str
    description: str | None = None
    frequency_type_cv_id: uuid_lib.UUID | None = None
    config: dict | None = None
    start_date: date
    end_date: date | None = None
    business_day_rule_cv_id: uuid_lib.UUID | None = None
    holiday_calendar_id: uuid_lib.UUID | None = None


class RecurrenceProfileUpdate(ORMModel):
    name: str | None = None
    description: str | None = None
    frequency_type_cv_id: uuid_lib.UUID | None = None
    config: dict | None = None
    start_date: date | None = None
    end_date: date | None = None
    business_day_rule_cv_id: uuid_lib.UUID | None = None
    holiday_calendar_id: uuid_lib.UUID | None = None


recurrence_profile_router = build_crud_router(
    prefix="/api/v1/recurrence-profiles", tag="recurrence-profiles", model=sch.RecurrenceProfile,
    entity_type="recurrence_profile", event_domain="recurrence_profile",
    out_schema=RecurrenceProfileOut, create_schema=RecurrenceProfileCreate,
    update_schema=RecurrenceProfileUpdate,
)


@recurrence_profile_router.get("/{profile_id}/occurrences")
def preview_occurrences(
    profile_id: uuid_lib.UUID,
    until: date = Query(...),
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
):
    profile = db.get(sch.RecurrenceProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="recurrence profile not found")
    dates = recurrence.occurrences(db, profile, until=until)
    return {"profile": str(profile_id), "until": until.isoformat(),
            "occurrences": [d.isoformat() for d in dates]}


# ---------------------------------------------------------------------------
# Installment plan (+ generate schedule + view)
# ---------------------------------------------------------------------------
class InstallmentPlanOut(EntityOut):
    account_id: uuid_lib.UUID | None = None
    total_amount: Decimal
    installment_count: int
    start_date: date
    frequency_cv_id: uuid_lib.UUID | None = None
    interest_rate: Decimal | None = None
    currency: str | None = None


class InstallmentPlanCreate(ORMModel):
    name: str
    description: str | None = None
    account_id: uuid_lib.UUID | None = None
    total_amount: Decimal
    installment_count: int
    start_date: date
    frequency_cv_id: uuid_lib.UUID | None = None
    interest_rate: Decimal | None = None
    currency: str | None = None


class InstallmentPlanUpdate(ORMModel):
    name: str | None = None
    description: str | None = None
    account_id: uuid_lib.UUID | None = None
    total_amount: Decimal | None = None
    installment_count: int | None = None
    start_date: date | None = None
    frequency_cv_id: uuid_lib.UUID | None = None
    interest_rate: Decimal | None = None
    currency: str | None = None


installment_plan_router = build_crud_router(
    prefix="/api/v1/installment-plans", tag="installment-plans", model=sch.InstallmentPlan,
    entity_type="installment_plan", event_domain="installment_plan",
    out_schema=InstallmentPlanOut, create_schema=InstallmentPlanCreate,
    update_schema=InstallmentPlanUpdate,
)


class InstallmentScheduleOut(BaseModel):
    uuid: uuid_lib.UUID
    seq: int
    due_date: date
    amount: Decimal
    status_cv_id: uuid_lib.UUID | None = None
    linked_txn_id: uuid_lib.UUID | None = None

    class Config:
        from_attributes = True


@installment_plan_router.post("/{plan_id}/generate", response_model=list[InstallmentScheduleOut])
def generate_installment_schedule(
    plan_id: uuid_lib.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_write),
):
    plan = db.get(sch.InstallmentPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="installment plan not found")
    rows = schedules.generate_installments(db, plan)
    db.commit()
    return rows


@installment_plan_router.get("/{plan_id}/schedule", response_model=list[InstallmentScheduleOut])
def get_installment_schedule(
    plan_id: uuid_lib.UUID,
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
):
    stmt = select(sch.InstallmentSchedule).where(
        sch.InstallmentSchedule.plan_id == plan_id
    ).order_by(sch.InstallmentSchedule.seq)
    return list(db.execute(stmt).scalars())


# ---------------------------------------------------------------------------
# Loan (+ amortization)
# ---------------------------------------------------------------------------
class LoanOut(EntityOut):
    account_id: uuid_lib.UUID | None = None
    loan_category_cv_id: uuid_lib.UUID | None = None
    principal: Decimal
    interest_rate: Decimal
    term_months: int
    start_date: date
    currency: str | None = None


class LoanCreate(ORMModel):
    name: str
    description: str | None = None
    account_id: uuid_lib.UUID | None = None
    loan_category_cv_id: uuid_lib.UUID | None = None
    principal: Decimal
    interest_rate: Decimal
    term_months: int
    start_date: date
    currency: str | None = None


class LoanUpdate(ORMModel):
    name: str | None = None
    description: str | None = None
    account_id: uuid_lib.UUID | None = None
    loan_category_cv_id: uuid_lib.UUID | None = None
    principal: Decimal | None = None
    interest_rate: Decimal | None = None
    term_months: int | None = None
    start_date: date | None = None
    currency: str | None = None


def _loan_pre_write(db: Session, data: dict, obj) -> None:
    # A.6: auto-create a backing account on create if none was supplied.
    if obj is None:
        ensure_backing_account(db, data, "Loan")


loan_router = build_crud_router(
    prefix="/api/v1/loans", tag="loans", model=sch.Loan,
    entity_type="loan", event_domain="loan",
    out_schema=LoanOut, create_schema=LoanCreate, update_schema=LoanUpdate,
    pre_write=_loan_pre_write,
)


class AmortizationOut(BaseModel):
    uuid: uuid_lib.UUID
    period: int
    due_date: date
    principal_portion: Decimal
    interest_portion: Decimal
    balance: Decimal

    class Config:
        from_attributes = True


@loan_router.post("/{loan_id}/generate", response_model=list[AmortizationOut])
def generate_loan_schedule(
    loan_id: uuid_lib.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_write),
):
    loan = db.get(sch.Loan, loan_id)
    if loan is None:
        raise HTTPException(status_code=404, detail="loan not found")
    rows = schedules.generate_amortization(db, loan)
    db.commit()
    return rows


@loan_router.get("/{loan_id}/schedule", response_model=list[AmortizationOut])
def get_loan_schedule(
    loan_id: uuid_lib.UUID,
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
):
    stmt = select(sch.AmortizationSchedule).where(
        sch.AmortizationSchedule.loan_id == loan_id
    ).order_by(sch.AmortizationSchedule.period)
    return list(db.execute(stmt).scalars())


# ---------------------------------------------------------------------------
# Goal
# ---------------------------------------------------------------------------
class GoalOut(EntityOut):
    target_amount: Decimal
    currency: str | None = None
    target_date: date | None = None
    linked_account_id: uuid_lib.UUID | None = None


class GoalCreate(ORMModel):
    name: str
    description: str | None = None
    target_amount: Decimal
    currency: str | None = None
    target_date: date | None = None
    linked_account_id: uuid_lib.UUID | None = None


class GoalUpdate(ORMModel):
    name: str | None = None
    description: str | None = None
    target_amount: Decimal | None = None
    currency: str | None = None
    target_date: date | None = None
    linked_account_id: uuid_lib.UUID | None = None


goal_router = build_crud_router(
    prefix="/api/v1/goals", tag="goals", model=sch.Goal,
    entity_type="goal", event_domain="goal",
    out_schema=GoalOut, create_schema=GoalCreate, update_schema=GoalUpdate,
)


# ---------------------------------------------------------------------------
# Pending recurring cash-flow items → materialize to transaction (spec 1.4.1)
# ---------------------------------------------------------------------------
recurring_router = APIRouter(prefix="/api/v1/recurring", tags=["recurring"])
_txn_repo = Repository(fin.Transaction, entity_type="transaction", event_domain="transaction")


class PendingOccurrence(BaseModel):
    cash_flow_item_id: uuid_lib.UUID
    cash_flow_item_name: str
    due_date: date
    expected_amount: Decimal | None = None
    currency: str | None = None


@recurring_router.get("/pending", response_model=list[PendingOccurrence])
def list_pending(
    until: date = Query(...),
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
):
    """Recurring cash-flow items whose occurrence dates have no transaction yet."""
    items = db.execute(
        select(fin.CashFlowItem).where(
            fin.CashFlowItem.recurrence_profile_id.isnot(None),
            fin.CashFlowItem.deleted_at.is_(None),
        )
    ).scalars()

    pending: list[PendingOccurrence] = []
    for item in items:
        profile = db.get(sch.RecurrenceProfile, item.recurrence_profile_id)
        if profile is None:
            continue
        occ_dates = recurrence.occurrences(db, profile, until=until)
        # Existing transaction dates already linked to this item.
        existing = set(
            db.execute(
                select(fin.Transaction.txn_date).where(
                    fin.Transaction.cash_flow_item_id == item.uuid,
                    fin.Transaction.deleted_at.is_(None),
                )
            ).scalars()
        )
        for d in occ_dates:
            if d not in existing:
                pending.append(
                    PendingOccurrence(
                        cash_flow_item_id=item.uuid,
                        cash_flow_item_name=item.name,
                        due_date=d,
                        expected_amount=item.expected_amount,
                        currency=item.currency,
                    )
                )
    return pending


class MaterializeIn(BaseModel):
    cash_flow_item_id: uuid_lib.UUID
    due_date: date
    account_id: uuid_lib.UUID
    amount: Decimal | None = None
    currency: str | None = None


@recurring_router.post("/materialize", status_code=201)
def materialize(
    payload: MaterializeIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_write),
):
    item = db.get(fin.CashFlowItem, payload.cash_flow_item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="cash_flow_item not found")
    # next sequence number for this item
    existing_seqs = db.execute(
        select(fin.Transaction.expense_item_seq_no).where(
            fin.Transaction.cash_flow_item_id == item.uuid
        )
    ).scalars()
    next_seq = (max([s for s in existing_seqs if s is not None], default=0)) + 1

    data = {
        "name": item.name,
        "account_id": payload.account_id,
        "txn_date": payload.due_date,
        "amount": payload.amount if payload.amount is not None else (item.expected_amount or 0),
        "currency": payload.currency or item.currency or "AED",
        "cash_flow_item_id": item.uuid,
        "expense_item_seq_no": next_seq,
        "expense_category_id": item.expense_category_id,  # Policy 1 inheritance
        "is_split": False,
        "note": f"Materialized from recurring item {item.mnemonic_id}",
    }
    obj = _txn_repo.create(db, data)
    return {"transaction": str(obj.uuid), "mnemonic_id": obj.mnemonic_id, "seq": next_seq}


ALL_ROUTERS = [
    holiday_calendar_router,
    recurrence_profile_router,
    installment_plan_router,
    loan_router,
    goal_router,
    recurring_router,
]
