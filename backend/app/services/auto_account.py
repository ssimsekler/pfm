"""Auto-create a backing Account for loans/investments (A.6).

When a loan or investment is created, we always spin up a dedicated backing
account so balances/transactions have somewhere to live. This is wired via the
CRUD `pre_write` hook so it runs inside the same request/session.

Session 742, Bug 10: creation is now unconditional (the create forms hide the
Account field), and the backing account is tagged with the appropriate
`account_type` code (loan → "loan", investment → "investment") when that code
value exists.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import financial as fin
from app.models.meta import CodeList, CodeValue
from app.services.repository import Repository

_account_repo = Repository(fin.Account, entity_type="account", event_domain="account")


def _account_type_cv(db: Session, code: str) -> object | None:
    """Resolve an account_type code_value uuid by code (e.g. 'loan'/'investment')."""
    cl = db.execute(
        select(CodeList).where(CodeList.list_key == "account_type")
    ).scalar_one_or_none()
    if cl is None:
        return None
    cv = db.execute(
        select(CodeValue).where(CodeValue.code_list_id == cl.uuid, CodeValue.code == code)
    ).scalar_one_or_none()
    return cv.uuid if cv else None


def ensure_backing_account(db: Session, data: dict, kind: str, *, type_code: str | None = None) -> None:
    """If `data` has no account_id, create a backing account and set it.

    `kind` is a short label ("Loan"/"Investment") used in the account name.
    `type_code` is the `account_type` code to tag the account with (defaults to
    the lowercased kind, e.g. "loan"/"investment"). `data` is the pending create
    payload for the loan/investment; it is mutated in place.
    """
    if data.get("account_id"):
        return
    name = data.get("name") or kind
    currency = data.get("currency") or "USD"
    account_type_cv_id = _account_type_cv(db, (type_code or kind).lower())
    account = _account_repo.create(
        db,
        {
            "name": f"{name} ({kind} account)",
            "currency": currency,
            "opening_balance": 0,
            "is_active": True,
            "account_type_cv_id": account_type_cv_id,
            "description": f"Auto-created backing account for {kind.lower()} “{name}”.",
        },
    )
    data["account_id"] = account.uuid
