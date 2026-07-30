"""Map parsed import rows to existing config values (partners, categories).

Uses: (1) the categorization rules engine, (2) case-insensitive name matching
against existing partners. Rows are tagged matched / new / unmapped so the user
can confirm or override on the validation screen (spec 3.1). If no existing value
matches, it is flagged 'new' and created automatically on commit only if the user
leaves it as such.
"""

import hashlib
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.financial import ExpenseCategory, Partner
from app.services import rules


def dedup_hash(row_mapped: dict[str, Any]) -> str:
    key = f"{row_mapped.get('date')}|{row_mapped.get('amount')}|{row_mapped.get('partner','')}".lower()
    return hashlib.sha256(key.encode()).hexdigest()


def _find_partner(db: Session, name: str | None) -> Partner | None:
    if not name:
        return None
    return db.execute(
        select(Partner).where(
            func.lower(Partner.name) == name.lower(), Partner.deleted_at.is_(None)
        )
    ).scalar_one_or_none()


def _find_category(db: Session, name: str | None) -> ExpenseCategory | None:
    if not name:
        return None
    return db.execute(
        select(ExpenseCategory).where(
            func.lower(ExpenseCategory.name) == name.lower(),
            ExpenseCategory.deleted_at.is_(None),
        )
    ).scalar_one_or_none()


def map_row(db: Session, mapped: dict[str, Any]) -> dict[str, Any]:
    """Return proposed mapping + status for one parsed row."""
    proposal: dict[str, Any] = {}
    status = "unmapped"

    # 1) Rules engine (partner/category/beneficiary by conditions on description/amount).
    rule_actions = rules.evaluate(db, {
        "description": mapped.get("description", ""),
        "partner": mapped.get("partner", ""),
        "amount": mapped.get("amount"),
    })
    if rule_actions:
        proposal.update(rule_actions)
        status = "matched"

    # 2) Direct partner name match.
    partner = _find_partner(db, mapped.get("partner"))
    if partner is not None:
        proposal["partner_id"] = str(partner.uuid)
        proposal["partner_name"] = partner.name
        status = "matched"
    elif mapped.get("partner"):
        proposal["partner_name_new"] = mapped["partner"]  # will be created on commit if kept
        if status != "matched":
            status = "new"

    # 3) Category by name (rare in statements, but supported).
    category = _find_category(db, mapped.get("category"))
    if category is not None:
        proposal["expense_category_id"] = str(category.uuid)
        status = "matched"

    return {"proposal": proposal, "status": status}