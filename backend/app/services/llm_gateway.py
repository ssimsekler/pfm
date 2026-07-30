"""Categorization rules engine.

Evaluates enabled rules (lowest `priority` first) against a transaction-like dict
and returns proposed actions (set_category / set_partner / set_beneficiary).
Condition operators: eq, contains (case-insensitive), amount_lt, amount_gt.
"""

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.automation import CategorizationRule


def _match(conditions: dict[str, Any], txn: dict[str, Any]) -> bool:
    for key, expected in (conditions or {}).items():
        if key == "amount_lt":
            if not (txn.get("amount") is not None and Decimal(str(txn["amount"])) < Decimal(str(expected))):
                return False
        elif key == "amount_gt":
            if not (txn.get("amount") is not None and Decimal(str(txn["amount"])) > Decimal(str(expected))):
                return False
        elif key.endswith("_contains"):
            field = key[: -len("_contains")]
            val = str(txn.get(field, "") or "").lower()
            if str(expected).lower() not in val:
                return False
        else:
            if str(txn.get(key, "")) != str(expected):
                return False
    return True


def evaluate(db: Session, txn: dict[str, Any]) -> dict[str, Any]:
    """Return merged actions from the first matching rules (by priority)."""
    rules = db.execute(
        select(CategorizationRule)
        .where(CategorizationRule.enabled.is_(True), CategorizationRule.deleted_at.is_(None))
        .order_by(CategorizationRule.priority.asc())
    ).scalars()

    actions: dict[str, Any] = {}
    for rule in rules:
        if _match(rule.conditions or {}, txn):
            for k, v in (rule.actions or {}).items():
                actions.setdefault(k, v)
    return actions