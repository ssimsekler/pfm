"""Phase 3 models: recurrence, holidays, installments, loans, goals."""

import uuid as uuid_lib
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, SmallInteger, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, BaseEntity

AMOUNT = Numeric(18, 4)


class HolidayCalendar(BaseEntity):
    __tablename__ = "holiday_calendar"

    # A.1: recurring weekend config + week-start (0=Mon .. 6=Sun, ISO-ish).
    # weekend_days is a JSON list of weekday integers (e.g. [4, 5] for Fri/Sat).
    weekend_days: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    week_start: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)


class HolidayCalendarDay(Base):
    __tablename__ = "holiday_calendar_day"

    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4
    )
    calendar_id: Mapped[uuid_lib.UUID] = mapped_column(
        ForeignKey("holiday_calendar.uuid"), nullable=False, index=True
    )
    holiday_date: Mapped[date] = mapped_column(Date, nullable=False)
    label: Mapped[str | None] = mapped_column(String(120), nullable=True)


class RecurrenceProfile(BaseEntity):
    __tablename__ = "recurrence_profile"

    frequency_type_cv_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("code_value.uuid"), nullable=True
    )
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    business_day_rule_cv_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("code_value.uuid"), nullable=True
    )
    holiday_calendar_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("holiday_calendar.uuid"), nullable=True
    )


class InstallmentPlan(BaseEntity):
    __tablename__ = "installment_plan"

    account_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("account.uuid"), nullable=True
    )
    total_amount: Mapped[Decimal] = mapped_column(AMOUNT, nullable=False)
    installment_count: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    frequency_cv_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("code_value.uuid"), nullable=True
    )
    interest_rate: Mapped[Decimal | None] = mapped_column(Numeric(9, 4), nullable=True)
    currency: Mapped[str | None] = mapped_column(ForeignKey("currency.code"), nullable=True)


class InstallmentSchedule(Base):
    __tablename__ = "installment_schedule"

    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4
    )
    plan_id: Mapped[uuid_lib.UUID] = mapped_column(
        ForeignKey("installment_plan.uuid"), nullable=False, index=True
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(AMOUNT, nullable=False)
    status_cv_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("code_value.uuid"), nullable=True
    )
    linked_txn_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("transaction.uuid"), nullable=True
    )


class Loan(BaseEntity):
    __tablename__ = "loan"

    account_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("account.uuid"), nullable=True
    )
    loan_category_cv_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("code_value.uuid"), nullable=True
    )
    principal: Mapped[Decimal] = mapped_column(AMOUNT, nullable=False)
    interest_rate: Mapped[Decimal] = mapped_column(Numeric(9, 4), nullable=False)
    term_months: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str | None] = mapped_column(ForeignKey("currency.code"), nullable=True)


class AmortizationSchedule(Base):
    __tablename__ = "amortization_schedule"

    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4
    )
    loan_id: Mapped[uuid_lib.UUID] = mapped_column(
        ForeignKey("loan.uuid"), nullable=False, index=True
    )
    period: Mapped[int] = mapped_column(Integer, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    principal_portion: Mapped[Decimal] = mapped_column(AMOUNT, nullable=False)
    interest_portion: Mapped[Decimal] = mapped_column(AMOUNT, nullable=False)
    balance: Mapped[Decimal] = mapped_column(AMOUNT, nullable=False)
    linked_txn_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("transaction.uuid"), nullable=True
    )


class Goal(BaseEntity):
    __tablename__ = "goal"

    target_amount: Mapped[Decimal] = mapped_column(AMOUNT, nullable=False)
    currency: Mapped[str | None] = mapped_column(ForeignKey("currency.code"), nullable=True)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    linked_account_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("account.uuid"), nullable=True
    )