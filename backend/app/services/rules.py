"""Categorization rules engine.

Evaluates user-defined `CategorizationRule` rows against a transaction-like
context (description / partner / amount) and returns the proposed actions of
the first matching rule (rules are tried in ascending `priority`).

Condition schema (JSONB `conditions`), keys map to context fields:
  - Text fields ("description", "partner"):
        "value"                      -> case-insensitive substring match
        {"contains": "value"}        -> case-insensitive substring match
        {"equals": "value"}          -> case-insensitive equality
        {"regex": "pattern"}         -> regular-expression search (case-insensitive)
  - Numeric field ("amount"):
        number                       -> exact match
        {"min": n}                   -> amount >= n
        {"max": n}                   -> amount <= n
        {"min": a, "max": b}         -> a <= amount <= b

An empty/absent `conditions` matches nothing (to avoid accidental catch-all).
`actions` (JSONB) is returned verbatim, e.g. {"expense_category_id": "...", "partner_id": "..."}.
"""

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.automation import CategorizationRule


def _as_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _match_text(criterion: Any, actual: str) -> bool:
    actual_l = (actual or "").lower()
    if isinstance(criterion, str):
        return criterion.lower() in actual_l
    if isinstance(criterion, dict):
        if "equals" in criterion:
            return actual_l == str(criterion["equals"]).lower()
        if "contains" in criterion:
            return str(criterion["contains"]).lower() in actual_l
        if "regex" in criterion:
            try:
                return re.search(str(criterion["regex"]), actual or "", re.IGNORECASE) is not None
            except re.error:
                return False
    return False


def _match_amount(criterion: Any, actual: Decimal | None) -> bool:
    if actual is None:
        return False
    if isinstance(criterion, (int, float, str)):
        target = _as_decimal(criterion)
        return target is not None and actual == target
    if isinstance(criterion, dict):
        lo = _as_decimal(criterion.get("min"))
        hi = _as_decimal(criterion.get("max"))
        if lo is not None and actual < lo:
            return False
        if hi is not None and actual > hi:
            return False
        return lo is not None or hi is not None
    return False


def _rule_matches(conditions: dict | None, context: dict[str, Any]) -> bool:
    if not conditions:
        return False
    for field, criterion in conditions.items():
        if field == "amount":
            if not _match_amount(criterion, _as_decimal(context.get("amount"))):
                return False
        else:
            if not _match_text(criterion, str(context.get(field, "") or "")):
                return False
    return True


def evaluate(db: Session, context: dict[str, Any]) -> dict[str, Any]:
    """Return the actions of the first enabled rule matching `context`, else {}."""
    rules = db.execute(
        select(CategorizationRule)
        .where(
            CategorizationRule.enabled.is_(True),
            CategorizationRule.deleted_at.is_(None),
        )
        .order_by(CategorizationRule.priority.asc())
    ).scalars()

    for rule in rules:
        if _rule_matches(rule.conditions, context):
            return dict(rule.actions or {})
    return {}