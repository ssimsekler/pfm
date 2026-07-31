"""Map parsed import rows to existing config values (partners, categories, account).

Order of precedence when proposing a mapping for a row (Session 742, Bug 17/18):
  1. **Mapping memory** — the most-frequently-accepted partner/category for the row's
     statement text (learned from past commits; bank supplier text is stable).
  2. **Categorization rules** engine (conditions on description/partner/amount).
  3. **Direct name match** against existing partners (case-insensitive); unmatched
     partner text is flagged 'new' and created on commit if kept.
  4. **Per-row account** deduced from an account/iban/account_number column (Bug 18).
  5. **LLM-assisted** suggestion (only when `llm.master_enabled`) as a soft hint.

Rows are tagged matched / new / unmapped so the user can confirm/override on the
validation screen (spec 3.1).
"""

import hashlib
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.financial import Account, ExpenseCategory, Partner
from app.models.imports import ImportMappingMemory
from app.services import llm_gateway, rules


def dedup_hash(row_mapped: dict[str, Any]) -> str:
    key = f"{row_mapped.get('date')}|{row_mapped.get('amount')}|{row_mapped.get('partner','')}".lower()
    return hashlib.sha256(key.encode()).hexdigest()


def _source_text(mapped: dict[str, Any]) -> str:
    """The statement text we learn from — description first, else partner text."""
    return (mapped.get("description") or mapped.get("partner") or "").strip()


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


def _find_account(db: Session, mapped: dict[str, Any]) -> Account | None:
    """Deduce a per-row account from account/iban/account_number columns (Bug 18)."""
    iban = (mapped.get("iban") or mapped.get("account_iban") or "").strip()
    acc_no = (mapped.get("account_number") or mapped.get("account_no") or "").strip()
    acc_name = (mapped.get("account") or mapped.get("account_name") or "").strip()

    if iban:
        row = db.execute(
            select(Account).where(func.lower(Account.iban) == iban.lower(), Account.deleted_at.is_(None))
        ).scalar_one_or_none() if hasattr(Account, "iban") else None
        if row:
            return row
    if acc_no and hasattr(Account, "account_number"):
        row = db.execute(
            select(Account).where(
                func.lower(Account.account_number) == acc_no.lower(), Account.deleted_at.is_(None)
            )
        ).scalar_one_or_none()
        if row:
            return row
    if acc_name:
        row = db.execute(
            select(Account).where(func.lower(Account.name) == acc_name.lower(), Account.deleted_at.is_(None))
        ).scalar_one_or_none()
        if row:
            return row
    return None


def _memory_suggestion(db: Session, source_text: str) -> ImportMappingMemory | None:
    """Most-frequently-accepted memory row for this exact statement text."""
    if not source_text:
        return None
    return db.execute(
        select(ImportMappingMemory)
        .where(func.lower(ImportMappingMemory.source_text) == source_text.lower())
        .order_by(ImportMappingMemory.accept_count.desc())
        .limit(1)
    ).scalar_one_or_none()


def _llm_suggestion(db: Session, mapped: dict[str, Any]) -> dict[str, Any]:
    """Optional LLM hint for a category name (gated by llm.master_enabled).

    Returns {"suggested_category_name": str} when the model proposes one that
    matches an existing category; otherwise empty. Never blocks the import.
    """
    if not llm_gateway.is_enabled(db):
        return {}
    text = _source_text(mapped)
    if not text:
        return {}
    cats = [c.name for c in db.execute(
        select(ExpenseCategory).where(ExpenseCategory.deleted_at.is_(None))
    ).scalars()]
    if not cats:
        return {}
    prompt = (
        "You categorize bank transactions. Given the statement text and this list of "
        f"allowed categories {cats}, reply with ONLY the single best matching category "
        f"name from the list, or NONE.\nStatement: {text!r}"
    )
    try:
        reply = (llm_gateway.complete(db, "IMPORT_CATEGORIZE", prompt) or "").strip()
    except Exception:  # noqa: BLE001
        return {}
    for c in cats:
        if reply and c.lower() == reply.lower():
            return {"suggested_category_name": c}
    return {}


def map_row(db: Session, mapped: dict[str, Any]) -> dict[str, Any]:
    """Return proposed mapping + status for one parsed row."""
    proposal: dict[str, Any] = {}
    status = "unmapped"
    source_text = _source_text(mapped)

    # 1) Mapping memory — strongest signal (learned from prior accepted commits).
    mem = _memory_suggestion(db, source_text)
    if mem is not None:
        if mem.mapped_partner_id:
            p = db.get(Partner, mem.mapped_partner_id)
            if p is not None:
                proposal["partner_id"] = str(p.uuid)
                proposal["partner_name"] = p.name
                status = "matched"
        if mem.mapped_category_id:
            c = db.get(ExpenseCategory, mem.mapped_category_id)
            if c is not None:
                proposal["expense_category_id"] = str(c.uuid)
                proposal["expense_category_name"] = c.name
                status = "matched"
        proposal["from_memory"] = True

    # 2) Rules engine (partner/category/beneficiary by conditions).
    rule_actions = rules.evaluate(db, {
        "description": mapped.get("description", ""),
        "partner": mapped.get("partner", ""),
        "amount": mapped.get("amount"),
    })
    if rule_actions:
        for k, v in rule_actions.items():
            proposal.setdefault(k, v)
        status = "matched"

    # 3) Direct partner name match (unless memory already set one).
    if "partner_id" not in proposal:
        partner = _find_partner(db, mapped.get("partner"))
        if partner is not None:
            proposal["partner_id"] = str(partner.uuid)
            proposal["partner_name"] = partner.name
            status = "matched"
        elif mapped.get("partner"):
            proposal["partner_name_new"] = mapped["partner"]  # created on commit if kept
            if status != "matched":
                status = "new"

    # 4) Category by name (rare in statements, but supported).
    if "expense_category_id" not in proposal:
        category = _find_category(db, mapped.get("category"))
        if category is not None:
            proposal["expense_category_id"] = str(category.uuid)
            status = "matched"

    # 5) Per-row account (Bug 18) — deduce from account/iban/account_number.
    acct = _find_account(db, mapped)
    if acct is not None:
        proposal["account_id"] = str(acct.uuid)

    # 6) LLM soft hint (gated) — only a suggestion for the reviewer.
    proposal.update(_llm_suggestion(db, mapped))

    return {"proposal": proposal, "status": status}


def record_memory(
    db: Session,
    source_text: str,
    partner_id: Any | None,
    category_id: Any | None,
) -> None:
    """Upsert learned mapping memory on an accepted commit (Session 742, Bug 17).

    Increments `accept_count` for an existing (text, partner, category) triple,
    else inserts a new row. No-op when there's nothing to learn.
    """
    text = (source_text or "").strip()
    if not text or (partner_id is None and category_id is None):
        return
    from datetime import datetime, timezone

    existing = db.execute(
        select(ImportMappingMemory).where(
            func.lower(ImportMappingMemory.source_text) == text.lower(),
            ImportMappingMemory.mapped_partner_id == partner_id,
            ImportMappingMemory.mapped_category_id == category_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        existing.accept_count = (existing.accept_count or 0) + 1
        existing.updated_at = datetime.now(timezone.utc)
    else:
        db.add(
            ImportMappingMemory(
                source_text=text[:400],
                mapped_partner_id=partner_id,
                mapped_category_id=category_id,
                accept_count=1,
            )
        )
