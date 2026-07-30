"""Financial entity schemas + routers (Phase 2).

Simple entities use the generic CRUD factory. Transactions get a dedicated
router with rich filtering (account, partner, beneficiary, category, status,
currency, date/amount ranges) per Decision #25.
"""

import uuid as uuid_lib
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.crud_router import build_crud_router
from app.api.schemas import DeleteResult, EntityOut, ORMModel, PageOut
from app.core.database import get_db
from app.core.security import Principal, get_current_principal, require_write
from app.models import financial as fin
from app.services.repository import Repository

# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------
class AccountOut(EntityOut):
    account_type_cv_id: uuid_lib.UUID | None = None
    currency: str
    opening_balance: Decimal
    opening_balance_date: date | None = None
    institution_id: uuid_lib.UUID | None = None
    is_active: bool


class AccountCreate(ORMModel):
    name: str
    description: str | None = None
    account_type_cv_id: uuid_lib.UUID | None = None
    currency: str
    opening_balance: Decimal = Decimal(0)
    opening_balance_date: date | None = None
    institution_id: uuid_lib.UUID | None = None
    is_active: bool = True


class AccountUpdate(ORMModel):
    name: str | None = None
    description: str | None = None
    account_type_cv_id: uuid_lib.UUID | None = None
    currency: str | None = None
    opening_balance: Decimal | None = None
    opening_balance_date: date | None = None
    institution_id: uuid_lib.UUID | None = None
    is_active: bool | None = None


account_router = build_crud_router(
    prefix="/api/v1/accounts", tag="accounts", model=fin.Account,
    entity_type="account", event_domain="account",
    out_schema=AccountOut, create_schema=AccountCreate, update_schema=AccountUpdate,
    search_columns=["currency"],
    filter_fields=["currency", "account_type_cv_id", "institution_id", "is_active"],
)


# ---------------------------------------------------------------------------
# Partner
# ---------------------------------------------------------------------------
class PartnerOut(EntityOut):
    partner_type_cv_id: uuid_lib.UUID | None = None
    country_id: uuid_lib.UUID | None = None


class PartnerCreate(ORMModel):
    name: str
    description: str | None = None
    partner_type_cv_id: uuid_lib.UUID | None = None
    country_id: uuid_lib.UUID | None = None


class PartnerUpdate(ORMModel):
    name: str | None = None
    description: str | None = None
    partner_type_cv_id: uuid_lib.UUID | None = None
    country_id: uuid_lib.UUID | None = None


partner_router = build_crud_router(
    prefix="/api/v1/partners", tag="partners", model=fin.Partner,
    entity_type="partner", event_domain="partner",
    out_schema=PartnerOut, create_schema=PartnerCreate, update_schema=PartnerUpdate,
    filter_fields=["partner_type_cv_id", "country_id"],
)


# ---------------------------------------------------------------------------
# Beneficiary (2-level)
# ---------------------------------------------------------------------------
class BeneficiaryOut(EntityOut):
    parent_id: uuid_lib.UUID | None = None
    level: int


class BeneficiaryCreate(ORMModel):
    name: str
    description: str | None = None
    parent_id: uuid_lib.UUID | None = None
    level: int = 1


class BeneficiaryUpdate(ORMModel):
    name: str | None = None
    description: str | None = None
    parent_id: uuid_lib.UUID | None = None
    level: int | None = None


beneficiary_router = build_crud_router(
    prefix="/api/v1/beneficiaries", tag="beneficiaries", model=fin.Beneficiary,
    entity_type="beneficiary", event_domain="beneficiary",
    out_schema=BeneficiaryOut, create_schema=BeneficiaryCreate, update_schema=BeneficiaryUpdate,
    filter_fields=["parent_id", "level"],
)


# ---------------------------------------------------------------------------
# Expense category (3-level)
# ---------------------------------------------------------------------------
class ExpenseCategoryOut(EntityOut):
    parent_id: uuid_lib.UUID | None = None
    level: int


class ExpenseCategoryCreate(ORMModel):
    name: str
    description: str | None = None
    parent_id: uuid_lib.UUID | None = None
    level: int = 1


class ExpenseCategoryUpdate(ORMModel):
    name: str | None = None
    description: str | None = None
    parent_id: uuid_lib.UUID | None = None
    level: int | None = None


expense_category_router = build_crud_router(
    prefix="/api/v1/expense-categories", tag="expense-categories", model=fin.ExpenseCategory,
    entity_type="expense_category", event_domain="expense_category",
    out_schema=ExpenseCategoryOut, create_schema=ExpenseCategoryCreate,
    update_schema=ExpenseCategoryUpdate,
    filter_fields=["parent_id", "level"],
)


# ---------------------------------------------------------------------------
# Cash flow item
# ---------------------------------------------------------------------------
class CashFlowItemOut(EntityOut):
    flow_type_cv_id: uuid_lib.UUID | None = None
    expense_category_id: uuid_lib.UUID
    recurrence_profile_id: uuid_lib.UUID | None = None
    expected_amount: Decimal | None = None
    currency: str | None = None
    status_cv_id: uuid_lib.UUID | None = None


class CashFlowItemCreate(ORMModel):
    name: str
    description: str | None = None
    flow_type_cv_id: uuid_lib.UUID | None = None
    expense_category_id: uuid_lib.UUID
    recurrence_profile_id: uuid_lib.UUID | None = None
    expected_amount: Decimal | None = None
    currency: str | None = None
    status_cv_id: uuid_lib.UUID | None = None


class CashFlowItemUpdate(ORMModel):
    name: str | None = None
    description: str | None = None
    flow_type_cv_id: uuid_lib.UUID | None = None
    expense_category_id: uuid_lib.UUID | None = None
    recurrence_profile_id: uuid_lib.UUID | None = None
    expected_amount: Decimal | None = None
    currency: str | None = None
    status_cv_id: uuid_lib.UUID | None = None


cash_flow_item_router = build_crud_router(
    prefix="/api/v1/cash-flow-items", tag="cash-flow-items", model=fin.CashFlowItem,
    entity_type="cash_flow_item", event_domain="cash_flow_item",
    out_schema=CashFlowItemOut, create_schema=CashFlowItemCreate,
    update_schema=CashFlowItemUpdate,
    filter_fields=["flow_type_cv_id", "expense_category_id", "currency", "status_cv_id"],
)


# ---------------------------------------------------------------------------
# Tag
# ---------------------------------------------------------------------------
class TagOut(EntityOut):
    pass


class TagCreate(ORMModel):
    name: str
    description: str | None = None


class TagUpdate(ORMModel):
    name: str | None = None
    description: str | None = None


tag_router = build_crud_router(
    prefix="/api/v1/tags", tag="tags", model=fin.Tag,
    entity_type="tag", event_domain="tag",
    out_schema=TagOut, create_schema=TagCreate, update_schema=TagUpdate,
)


# ---------------------------------------------------------------------------
# Transaction (dedicated router with rich filtering + Policy 1 enforcement)
# ---------------------------------------------------------------------------
class TransactionOut(EntityOut):
    account_id: uuid_lib.UUID
    txn_date: date
    booking_date: date | None = None
    amount: Decimal
    currency: str
    direction_cv_id: uuid_lib.UUID | None = None
    partner_id: uuid_lib.UUID | None = None
    beneficiary_id: uuid_lib.UUID | None = None
    expense_category_id: uuid_lib.UUID | None = None
    cash_flow_item_id: uuid_lib.UUID | None = None
    expense_item_seq_no: int | None = None
    transfer_group_id: uuid_lib.UUID | None = None
    installment_plan_id: uuid_lib.UUID | None = None
    source_document_id: uuid_lib.UUID | None = None
    is_split: bool
    status_cv_id: uuid_lib.UUID | None = None
    note: str | None = None


class TransactionCreate(ORMModel):
    name: str
    description: str | None = None
    account_id: uuid_lib.UUID
    txn_date: date
    booking_date: date | None = None
    amount: Decimal
    currency: str
    direction_cv_id: uuid_lib.UUID | None = None
    partner_id: uuid_lib.UUID | None = None
    beneficiary_id: uuid_lib.UUID | None = None
    expense_category_id: uuid_lib.UUID | None = None
    cash_flow_item_id: uuid_lib.UUID | None = None
    expense_item_seq_no: int | None = None
    status_cv_id: uuid_lib.UUID | None = None
    note: str | None = None


class TransactionUpdate(ORMModel):
    name: str | None = None
    description: str | None = None
    account_id: uuid_lib.UUID | None = None
    txn_date: date | None = None
    booking_date: date | None = None
    amount: Decimal | None = None
    currency: str | None = None
    direction_cv_id: uuid_lib.UUID | None = None
    partner_id: uuid_lib.UUID | None = None
    beneficiary_id: uuid_lib.UUID | None = None
    expense_category_id: uuid_lib.UUID | None = None
    cash_flow_item_id: uuid_lib.UUID | None = None
    expense_item_seq_no: int | None = None
    status_cv_id: uuid_lib.UUID | None = None
    note: str | None = None


_txn_repo = Repository(fin.Transaction, entity_type="transaction", event_domain="transaction")
transaction_router = APIRouter(prefix="/api/v1/transactions", tags=["transactions"])


def _enforce_policy1(db: Session, data: dict) -> None:
    """If linked to a cash_flow_item, inherit its category and forbid split (Decision #16)."""
    cfi_id = data.get("cash_flow_item_id")
    if cfi_id:
        item = db.get(fin.CashFlowItem, cfi_id)
        if item is None:
            raise HTTPException(status_code=422, detail="cash_flow_item not found")
        data["expense_category_id"] = item.expense_category_id
        data["is_split"] = False


@transaction_router.get("", response_model=PageOut[TransactionOut])
def list_transactions(
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
    search: str | None = Query(None),
    sort: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    include_deleted: bool = Query(False),
    account_id: uuid_lib.UUID | None = Query(None),
    partner_id: uuid_lib.UUID | None = Query(None),
    beneficiary_id: uuid_lib.UUID | None = Query(None),
    expense_category_id: uuid_lib.UUID | None = Query(None),
    cash_flow_item_id: uuid_lib.UUID | None = Query(None),
    status_cv_id: uuid_lib.UUID | None = Query(None),
    currency: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    amount_min: Decimal | None = Query(None),
    amount_max: Decimal | None = Query(None),
):
    filters: dict = {
        "account_id": account_id,
        "partner_id": partner_id,
        "beneficiary_id": beneficiary_id,
        "expense_category_id": expense_category_id,
        "cash_flow_item_id": cash_flow_item_id,
        "status_cv_id": status_cv_id,
        "currency": currency,
        "txn_date__gte": date_from,
        "txn_date__lte": date_to,
        "amount__gte": amount_min,
        "amount__lte": amount_max,
    }
    page = _txn_repo.list(
        db, search=search, filters=filters, sort=sort, limit=limit, offset=offset,
        include_deleted=include_deleted, search_columns=["note", "currency"],
    )
    return PageOut(
        items=[TransactionOut.model_validate(i) for i in page.items],
        total=page.total, limit=page.limit, offset=page.offset,
    )


@transaction_router.post("", response_model=TransactionOut, status_code=201)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_write),
):
    data = payload.model_dump(exclude_unset=True)
    _enforce_policy1(db, data)
    obj = _txn_repo.create(db, data)
    return TransactionOut.model_validate(obj)


@transaction_router.get("/{item_uuid}", response_model=TransactionOut)
def get_transaction(
    item_uuid: uuid_lib.UUID,
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
):
    obj = _txn_repo.get(db, item_uuid)
    if obj is None:
        raise HTTPException(status_code=404, detail="transaction not found")
    return TransactionOut.model_validate(obj)


@transaction_router.patch("/{item_uuid}", response_model=TransactionOut)
def update_transaction(
    item_uuid: uuid_lib.UUID,
    payload: TransactionUpdate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_write),
):
    obj = _txn_repo.get(db, item_uuid)
    if obj is None:
        raise HTTPException(status_code=404, detail="transaction not found")
    data = payload.model_dump(exclude_unset=True)
    _enforce_policy1(db, data)
    obj = _txn_repo.update(db, obj, data)
    return TransactionOut.model_validate(obj)


@transaction_router.delete("/{item_uuid}")
def delete_transaction(
    item_uuid: uuid_lib.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_write),
):
    obj = _txn_repo.get(db, item_uuid)
    if obj is None:
        raise HTTPException(status_code=404, detail="transaction not found")
    _txn_repo.soft_delete(db, obj)
    return {"deleted": True, "uuid": str(item_uuid)}


# ---------------------------------------------------------------------------
# Transaction splits (ADR #33): a transaction can be split across multiple
# expense categories/beneficiaries. Split amounts must sum exactly to the
# transaction amount. Splitting is disallowed when the transaction is linked to
# a cash_flow_item (Policy 1, ADR #16).
# ---------------------------------------------------------------------------
class SplitIn(ORMModel):
    expense_category_id: uuid_lib.UUID
    beneficiary_id: uuid_lib.UUID | None = None
    amount: Decimal


class SplitOut(ORMModel):
    uuid: uuid_lib.UUID
    transaction_id: uuid_lib.UUID
    expense_category_id: uuid_lib.UUID
    beneficiary_id: uuid_lib.UUID | None = None
    amount: Decimal


class SplitReplaceIn(ORMModel):
    """Replace the full set of split lines for a transaction in one call."""
    splits: list[SplitIn]


def _require_txn(db: Session, txn_id: uuid_lib.UUID) -> fin.Transaction:
    txn = _txn_repo.get(db, txn_id)
    if txn is None:
        raise HTTPException(status_code=404, detail="transaction not found")
    if txn.cash_flow_item_id is not None:
        raise HTTPException(
            status_code=422,
            detail="Cannot split a transaction linked to a cash_flow_item (Policy 1).",
        )
    return txn


def _validate_sum(txn: fin.Transaction, splits: list[SplitIn]) -> None:
    total = sum((Decimal(s.amount) for s in splits), Decimal(0))
    if total != Decimal(txn.amount):
        raise HTTPException(
            status_code=422,
            detail=(
                f"Split amounts must sum to the transaction amount "
                f"({txn.amount}); got {total}."
            ),
        )


@transaction_router.get("/{txn_id}/splits", response_model=list[SplitOut])
def list_splits(
    txn_id: uuid_lib.UUID,
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
):
    if _txn_repo.get(db, txn_id) is None:
        raise HTTPException(status_code=404, detail="transaction not found")
    rows = db.execute(
        select(fin.TransactionSplit).where(fin.TransactionSplit.transaction_id == txn_id)
    ).scalars()
    return list(rows)


@transaction_router.put("/{txn_id}/splits", response_model=list[SplitOut])
def replace_splits(
    txn_id: uuid_lib.UUID,
    payload: SplitReplaceIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_write),
):
    """Replace all split lines for a transaction (empty list clears splits)."""
    txn = _require_txn(db, txn_id)
    if payload.splits:
        _validate_sum(txn, payload.splits)

    # Clear existing lines, then insert the new set.
    existing = db.execute(
        select(fin.TransactionSplit).where(fin.TransactionSplit.transaction_id == txn_id)
    ).scalars().all()
    for row in existing:
        db.delete(row)

    created: list[fin.TransactionSplit] = []
    for s in payload.splits:
        row = fin.TransactionSplit(transaction_id=txn_id, **s.model_dump())
        db.add(row)
        created.append(row)

    txn.is_split = bool(payload.splits)
    db.commit()
    for row in created:
        db.refresh(row)
    return created


@transaction_router.post("/{txn_id}/splits", response_model=SplitOut, status_code=201)
def add_split(
    txn_id: uuid_lib.UUID,
    payload: SplitIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_write),
):
    """Add a single split line. The running total must not exceed the amount;
    once it equals the transaction amount, the transaction is marked split."""
    txn = _require_txn(db, txn_id)
    existing = db.execute(
        select(fin.TransactionSplit).where(fin.TransactionSplit.transaction_id == txn_id)
    ).scalars().all()
    running = sum((Decimal(r.amount) for r in existing), Decimal(0)) + Decimal(payload.amount)
    if running > Decimal(txn.amount):
        raise HTTPException(
            status_code=422,
            detail=f"Split total {running} would exceed transaction amount {txn.amount}.",
        )
    row = fin.TransactionSplit(transaction_id=txn_id, **payload.model_dump())
    db.add(row)
    txn.is_split = running == Decimal(txn.amount)
    db.commit()
    db.refresh(row)
    return row


@transaction_router.patch("/{txn_id}/splits/{split_id}", response_model=SplitOut)
def update_split(
    txn_id: uuid_lib.UUID,
    split_id: uuid_lib.UUID,
    payload: SplitIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_write),
):
    _require_txn(db, txn_id)
    row = db.get(fin.TransactionSplit, split_id)
    if row is None or row.transaction_id != txn_id:
        raise HTTPException(status_code=404, detail="split not found")
    row.expense_category_id = payload.expense_category_id
    row.beneficiary_id = payload.beneficiary_id
    row.amount = payload.amount
    db.commit()
    db.refresh(row)
    return row


@transaction_router.delete("/{txn_id}/splits/{split_id}", response_model=DeleteResult)
def delete_split(
    txn_id: uuid_lib.UUID,
    split_id: uuid_lib.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_write),
):
    _require_txn(db, txn_id)
    row = db.get(fin.TransactionSplit, split_id)
    if row is None or row.transaction_id != txn_id:
        raise HTTPException(status_code=404, detail="split not found")
    db.delete(row)
    # Recompute is_split from remaining lines.
    remaining = db.execute(
        select(fin.TransactionSplit).where(
            fin.TransactionSplit.transaction_id == txn_id,
            fin.TransactionSplit.uuid != split_id,
        )
    ).scalars().all()
    txn = _txn_repo.get(db, txn_id)
    if txn is not None:
        txn.is_split = len(remaining) > 0
    db.commit()
    return DeleteResult(uuid=split_id)


# All financial routers, collected for main.py registration.
ALL_ROUTERS = [
    account_router,
    partner_router,
    beneficiary_router,
    expense_category_router,
    cash_flow_item_router,
    tag_router,
    transaction_router,
]
