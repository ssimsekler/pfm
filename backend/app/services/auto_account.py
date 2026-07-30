"""Auto-create a backing Account for loans/investments (A.6).

When a loan or investment is created without an explicit `account_id`, we spin up
a dedicated backing account so balances/transactions have somewhere to live. This
is wired via the CRUD `pre_write` hook so it runs inside the same request/session.
"""

from sqlalchemy.orm import Session

from app.models import financial as fin
from app.services.repository import Repository

_account_repo = Repository(fin.Account, entity_type="account", event_domain="account")


def ensure_backing_account(db: Session, data: dict, kind: str) -> None:
    """If `data` has no account_id, create a backing account and set it.

    `kind` is a short label ("Loan"/"Investment") used in the account name.
    `data` is the pending create payload for the loan/investment; it is mutated
    in place. Uses the entity name/currency when available.
    """
    if data.get("account_id"):
        return
    name = data.get("name") or kind
    currency = data.get("currency") or "USD"
    account = _account_repo.create(
        db,
        {
            "name": f"{name} ({kind} account)",
            "currency": currency,
            "opening_balance": 0,
            "is_active": True,
            "description": f"Auto-created backing account for {kind.lower()} “{name}”.",
        },
    )
    data["account_id"] = account.uuid