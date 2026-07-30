"""Generate installment and loan amortization schedules."""

import uuid as uuid_lib
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.models.scheduling import (
    AmortizationSchedule,
    InstallmentPlan,
    InstallmentSchedule,
    Loan,
)
from app.services.recurrence import _add_months

CENTS = Decimal("0.01")


def generate_installments(db: Session, plan: InstallmentPlan) -> list[InstallmentSchedule]:
    """Create equal installments (last one absorbs rounding). Idempotent-ish:
    clears any existing rows for the plan first."""
    db.execute(
        InstallmentSchedule.__table__.delete().where(
            InstallmentSchedule.plan_id == plan.uuid
        )
    )
    n = plan.installment_count
    base = (Decimal(plan.total_amount) / n).quantize(CENTS, rounding=ROUND_HALF_UP)
    rows: list[InstallmentSchedule] = []
    running = Decimal(0)
    for i in range(1, n + 1):
        amount = base if i < n else (Decimal(plan.total_amount) - running)
        running += amount
        due = _add_months(plan.start_date, i - 1)
        row = InstallmentSchedule(
            uuid=uuid_lib.uuid4(),
            plan_id=plan.uuid,
            seq=i,
            due_date=due,
            amount=amount,
        )
        db.add(row)
        rows.append(row)
    db.flush()
    return rows


def generate_amortization(db: Session, loan: Loan) -> list[AmortizationSchedule]:
    """Standard fixed-rate amortization (monthly). Clears existing rows first."""
    db.execute(
        AmortizationSchedule.__table__.delete().where(
            AmortizationSchedule.loan_id == loan.uuid
        )
    )
    principal = Decimal(loan.principal)
    n = loan.term_months
    monthly_rate = Decimal(loan.interest_rate) / Decimal(100) / Decimal(12)

    if monthly_rate == 0:
        payment = (principal / n).quantize(CENTS, rounding=ROUND_HALF_UP)
    else:
        factor = (Decimal(1) + monthly_rate) ** n
        payment = (principal * monthly_rate * factor / (factor - Decimal(1))).quantize(
            CENTS, rounding=ROUND_HALF_UP
        )

    rows: list[AmortizationSchedule] = []
    balance = principal
    for period in range(1, n + 1):
        interest = (balance * monthly_rate).quantize(CENTS, rounding=ROUND_HALF_UP)
        principal_portion = payment - interest
        if period == n:  # final period clears remaining balance
            principal_portion = balance
            payment_this = principal_portion + interest
        else:
            payment_this = payment
        balance = (balance - principal_portion).quantize(CENTS, rounding=ROUND_HALF_UP)
        due = _add_months(loan.start_date, period - 1)
        row = AmortizationSchedule(
            uuid=uuid_lib.uuid4(),
            loan_id=loan.uuid,
            period=period,
            due_date=due,
            principal_portion=principal_portion,
            interest_portion=interest,
            balance=balance if balance > 0 else Decimal(0),
        )
        db.add(row)
        rows.append(row)
        _ = payment_this  # documented; not persisted separately
    db.flush()
    return rows