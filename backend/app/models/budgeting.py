"""Phase 6 models: budgets and budget lines.

A Budget is a business entity (uuid, mnemonic_id, name, description, audit,
household scope) with a period and optional base currency. BudgetLine is a
child row linking a budget to an expected amount per expense category /
cash-flow item / direction.
"""

import uuid as uuid_lib
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, BaseEntity

AMOUNT = Numeric(18, 4)


class Budget(BaseEntity):
    __tablename__ = "budget"

    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    base_currency: Mapped[str | None] = mapped_column(
        ForeignKey("currency.code"), nullable=True
    )


class BudgetLine(Base):
    __tablename__ = "budget_line"

    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4
    )
    budget_id: Mapped[uuid_lib.UUID] = mapped_column(
        ForeignKey("budget.uuid"), nullable=False, index=True
    )
    cash_flow_item_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("cash_flow_item.uuid"), nullable=True
    )
    expense_category_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("expense_category.uuid"), nullable=True
    )
    direction_cv_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("code_value.uuid"), nullable=True
    )
    expected_amount: Mapped[Decimal] = mapped_column(AMOUNT, nullable=False, default=Decimal(0))