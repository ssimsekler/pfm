"""Phase 3 API: recurrence, holidays, installments, loans, goals,
plus pending-recurring listing and materialize-to-transaction (spec 1.4.1)."""

import csv
import io
import uuid as uuid_lib
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.crud_router import build_crud_router
from app.api.schemas import EntityOut, ORMModel
from app.core.database import get_db
from app.core.security import Principal, get_current_principal, require_write
from app.models import financial as fin
from app.models import scheduling as sch
from app.models.meta import CodeList, CodeValue
from app.services import recurrence, schedules
from app.services.auto_account import ensure_backing_account
from app.services.repository import Repository


def _status_cv(db: Session, list_key: str, code: str) -> uuid_lib.UUID | None:
    """Resolve a code_value uuid by (list_key, code); None if not found."""
    cl = db.execute(select(CodeList).where(CodeList.list_key == list_key)).scalar_one_or_none()
    if cl is None:
        return None
    cv = db.execute(
        select(CodeValue).where(CodeValue.code_list_id == cl.uuid, CodeValue.code == code)
    ).scalar_one_or_none()
    return cv.uuid if cv else None


# --------------------------------------------------------------------------- #
# CSV schedule import helpers (Session 742, New-1)
# --------------------------------------------------------------------------- #
def _parse_csv_rows(content: bytes) -> list[dict]:
    """Parse a CSV upload into a list of lowercased-key dict rows."""
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows: list[dict] = []
    for raw in reader:
        rows.append({(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()})
    return rows


def _csv_date(value: str) -> date | None:
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def _csv_dec(value: str) -> Decimal:
    if value in (None, ""):
        return Decimal(0)
    try:
        return Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError):
        return Decimal(0)


def _csv_get(row: dict, *keys: str) -> str:
    for k in keys:
        if row.get(k):
            return row[k]
    return ""


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


@installment_plan_router.post("/{plan_id}/schedule/import", response_model=list[InstallmentScheduleOut])
def import_installment_schedule(
    plan_id: uuid_lib.UUID,
    file: UploadFile = File(...),
    mode: str = Form("replace"),  # "replace" | "append"
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_write),
):
    """Import an installment schedule from CSV (Session 742, New-1).

    Expected columns (case-insensitive): seq, due_date, amount.
    `mode=replace` clears existing rows first; `append` keeps them.
    """
    plan = db.get(sch.InstallmentPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="installment plan not found")
    content = file.file.read()
    rows = _parse_csv_rows(content)
    if not rows:
        raise HTTPException(status_code=422, detail="CSV is empty or unreadable")

    if mode == "replace":
        for existing in db.execute(
            select(sch.InstallmentSchedule).where(sch.InstallmentSchedule.plan_id == plan_id)
        ).scalars().all():
            db.delete(existing)

    created: list[sch.InstallmentSchedule] = []
    next_seq = 1
    for i, row in enumerate(rows, start=1):
        due = _csv_date(_csv_get(row, "due_date", "date", "due"))
        if due is None:
            continue
        seq_raw = _csv_get(row, "seq", "no", "number", "installment")
        try:
            seq = int(float(seq_raw)) if seq_raw else next_seq
        except ValueError:
            seq = next_seq
        next_seq = seq + 1
        r = sch.InstallmentSchedule(
            plan_id=plan_id,
            seq=seq,
            due_date=due,
            amount=_csv_dec(_csv_get(row, "amount", "value")),
            status_cv_id=_status_cv(db, "installment_status", "due"),
        )
        db.add(r)
        created.append(r)

    db.commit()
    for r in created:
        db.refresh(r)
    return sorted(created, key=lambda x: x.seq)


class PayInstallmentIn(BaseModel):
    account_id: uuid_lib.UUID | None = None
    txn_date: date | None = None


@installment_plan_router.post("/{plan_id}/schedule/{schedule_id}/pay", response_model=InstallmentScheduleOut)
def pay_installment(
    plan_id: uuid_lib.UUID,
    schedule_id: uuid_lib.UUID,
    payload: PayInstallmentIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_write),
):
    """Record a payment for an installment: create a linked transaction and mark paid (#15)."""
    plan = db.get(sch.InstallmentPlan, plan_id)
    row = db.get(sch.InstallmentSchedule, schedule_id)
    if plan is None or row is None or row.plan_id != plan_id:
        raise HTTPException(status_code=404, detail="installment schedule not found")
    account_id = payload.account_id or plan.account_id
    if account_id is None:
        raise HTTPException(status_code=422, detail="No account to book the payment against")
    txn = _txn_repo.create(
        db,
        {
            "name": f"Installment {row.seq} — {plan.name}",
            "account_id": account_id,
            "txn_date": payload.txn_date or row.due_date,
            "amount": row.amount,
            "currency": plan.currency or "USD",
            "installment_plan_id": plan.uuid,
            "note": f"Installment payment {row.seq}/{plan.installment_count} for {plan.mnemonic_id}",
        },
    )
    row.linked_txn_id = txn.uuid
    row.status_cv_id = _status_cv(db, "installment_status", "paid")
    db.commit()
    db.refresh(row)
    return row


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
    # A.6 / Bug 10: always auto-create a loan-type backing account on create
    # (the create form hides the Account field).
    if obj is None:
        ensure_backing_account(db, data, "Loan", type_code="loan")


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


@loan_router.post("/{loan_id}/schedule/import", response_model=list[AmortizationOut])
def import_loan_schedule(
    loan_id: uuid_lib.UUID,
    file: UploadFile = File(...),
    mode: str = Form("replace"),  # "replace" | "append"
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_write),
):
    """Import a loan amortization schedule from CSV (Session 742, New-1).

    Expected columns (case-insensitive): period, due_date, principal_portion,
    interest_portion, balance. `mode=replace` clears existing rows first.
    """
    loan = db.get(sch.Loan, loan_id)
    if loan is None:
        raise HTTPException(status_code=404, detail="loan not found")
    content = file.file.read()
    rows = _parse_csv_rows(content)
    if not rows:
        raise HTTPException(status_code=422, detail="CSV is empty or unreadable")

    if mode == "replace":
        for existing in db.execute(
            select(sch.AmortizationSchedule).where(sch.AmortizationSchedule.loan_id == loan_id)
        ).scalars().all():
            db.delete(existing)

    created: list[sch.AmortizationSchedule] = []
    next_period = 1
    for row in rows:
        due = _csv_date(_csv_get(row, "due_date", "date", "due"))
        if due is None:
            continue
        period_raw = _csv_get(row, "period", "no", "number", "seq")
        try:
            period = int(float(period_raw)) if period_raw else next_period
        except ValueError:
            period = next_period
        next_period = period + 1
        r = sch.AmortizationSchedule(
            loan_id=loan_id,
            period=period,
            due_date=due,
            principal_portion=_csv_dec(_csv_get(row, "principal_portion", "principal")),
            interest_portion=_csv_dec(_csv_get(row, "interest_portion", "interest")),
            balance=_csv_dec(_csv_get(row, "balance", "remaining")),
        )
        db.add(r)
        created.append(r)

    db.commit()
    for r in created:
        db.refresh(r)
    return sorted(created, key=lambda x: x.period)


class AmortizationOutLinked(AmortizationOut):
    linked_txn_id: uuid_lib.UUID | None = None


class PayLoanIn(BaseModel):
    account_id: uuid_lib.UUID | None = None
    txn_date: date | None = None


@loan_router.post("/{loan_id}/schedule/{schedule_id}/pay", response_model=AmortizationOutLinked)
def pay_loan_period(
    loan_id: uuid_lib.UUID,
    schedule_id: uuid_lib.UUID,
    payload: PayLoanIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_write),
):
    """Record a loan payment for an amortization period: create a linked transaction (#16)."""
    loan = db.get(sch.Loan, loan_id)
    row = db.get(sch.AmortizationSchedule, schedule_id)
    if loan is None or row is None or row.loan_id != loan_id:
        raise HTTPException(status_code=404, detail="loan schedule not found")
    account_id = payload.account_id or loan.account_id
    if account_id is None:
        raise HTTPException(status_code=422, detail="No account to book the payment against")
    amount = Decimal(row.principal_portion or 0) + Decimal(row.interest_portion or 0)
    txn = _txn_repo.create(
        db,
        {
            "name": f"Loan payment {row.period} — {loan.name}",
            "account_id": account_id,
            "txn_date": payload.txn_date or row.due_date,
            "amount": amount,
            "currency": loan.currency or "USD",
            "note": (
                f"Loan payment period {row.period}/{loan.term_months} for {loan.mnemonic_id} "
                f"(principal {row.principal_portion}, interest {row.interest_portion})"
            ),
        },
    )
    row.linked_txn_id = txn.uuid
    db.commit()
    db.refresh(row)
    return row


# ---------------------------------------------------------------------------
# Goal
# ---------------------------------------------------------------------------
class GoalOut(EntityOut):
    target_amount: Decimal
    currency: str | None = None
    target_date: date | None = None
    linked_account_id: uuid_lib.UUID | None = None
    goal_type_cv_id: uuid_lib.UUID | None = None
    expense_category_id: uuid_lib.UUID | None = None
    period: str | None = None
    limit_amount: Decimal | None = None


class GoalCreate(ORMModel):
    name: str
    description: str | None = None
    target_amount: Decimal
    currency: str | None = None
    target_date: date | None = None
    linked_account_id: uuid_lib.UUID | None = None
    goal_type_cv_id: uuid_lib.UUID | None = None
    expense_category_id: uuid_lib.UUID | None = None
    period: str | None = None
    limit_amount: Decimal | None = None


class GoalUpdate(ORMModel):
    name: str | None = None
    description: str | None = None
    target_amount: Decimal | None = None
    currency: str | None = None
    target_date: date | None = None
    linked_account_id: uuid_lib.UUID | None = None
    goal_type_cv_id: uuid_lib.UUID | None = None
    expense_category_id: uuid_lib.UUID | None = None
    period: str | None = None
    limit_amount: Decimal | None = None


goal_router = build_crud_router(
    prefix="/api/v1/goals", tag="goals", model=sch.Goal,
    entity_type="goal", event_domain="goal",
    out_schema=GoalOut, create_schema=GoalCreate, update_schema=GoalUpdate,
)


@goal_router.get("/{goal_id}/progress")
def goal_progress(
    goal_id: uuid_lib.UUID,
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
):
    """Evaluate a goal against transactions (Session 742, Bug 19).

    - save_to_target: sum of amounts on transactions tagged with this goal (goal_id),
      compared to target_amount.
    - cap_expense: sum of amounts on transactions in the goal's category over the
      current period (monthly/yearly/total), compared to limit_amount. Example:
      "Keep fuel expenses < 1000/month".
    """
    goal = db.get(sch.Goal, goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail="goal not found")

    goal_type = "save_to_target"
    if goal.goal_type_cv_id is not None:
        cv = db.get(CodeValue, goal.goal_type_cv_id)
        goal_type = (cv.code if cv else None) or "save_to_target"

    from decimal import Decimal as _D

    if goal_type == "cap_expense":
        period = (goal.period or "monthly").lower()
        today = date.today()
        if period == "monthly":
            start = today.replace(day=1)
        elif period == "yearly":
            start = today.replace(month=1, day=1)
        else:  # total
            start = None
        stmt = select(fin.Transaction).where(
            fin.Transaction.deleted_at.is_(None),
        )
        if goal.expense_category_id is not None:
            stmt = stmt.where(fin.Transaction.expense_category_id == goal.expense_category_id)
        if start is not None:
            stmt = stmt.where(fin.Transaction.txn_date >= start)
        spent = sum((_D(t.amount) for t in db.execute(stmt).scalars()), _D(0))
        limit = _D(goal.limit_amount or 0)
        return {
            "goal": str(goal.uuid),
            "type": "cap_expense",
            "period": period,
            "spent": str(spent),
            "limit": str(limit),
            "remaining": str(limit - spent),
            "within_limit": bool(spent <= limit) if limit else None,
        }

    # save_to_target: sum of goal-tagged transactions toward the target.
    stmt = select(fin.Transaction).where(
        fin.Transaction.goal_id == goal.uuid,
        fin.Transaction.deleted_at.is_(None),
    )
    saved = sum((_D(t.amount) for t in db.execute(stmt).scalars()), _D(0))
    target = _D(goal.target_amount or 0)
    pct = float(saved / target * 100) if target else None
    return {
        "goal": str(goal.uuid),
        "type": "save_to_target",
        "saved": str(saved),
        "target": str(target),
        "remaining": str(target - saved),
        "percent": pct,
    }


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
    # Session 742, Bug 14: beneficiary may be overridden on the dialog; when omitted
    # it is inherited from the cash-flow item.
    beneficiary_id: uuid_lib.UUID | None = None


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

    # Derive txn direction from the item's flow_type: income→credit, expense→debit.
    direction_cv_id = None
    if item.flow_type_cv_id is not None:
        flow_cv = db.get(CodeValue, item.flow_type_cv_id)
        if flow_cv is not None:
            direction_cv_id = _status_cv(
                db, "txn_direction", "credit" if flow_cv.code == "income" else "debit"
            )

    data = {
        "name": item.name,
        "account_id": payload.account_id,
        "txn_date": payload.due_date,
        "amount": payload.amount if payload.amount is not None else (item.expected_amount or 0),
        "currency": payload.currency or item.currency or "AED",
        "cash_flow_item_id": item.uuid,
        "expense_item_seq_no": next_seq,
        "expense_category_id": item.expense_category_id,  # Policy 1 inheritance
        # Bug 14: beneficiary inherited from the item unless explicitly overridden.
        "beneficiary_id": payload.beneficiary_id
        if payload.beneficiary_id is not None
        else item.beneficiary_id,
        "direction_cv_id": direction_cv_id,  # inherited from flow_type
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
