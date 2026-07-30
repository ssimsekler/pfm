"""Mnemonic ID generation service (Decision #6/#7).

- Each entity type has a prefix (up to 3 chars) with a configurable pad width.
- Numbers are allocated atomically per prefix using a row lock.
- Defining a NEW prefix starts its own sequence at 1; existing IDs are immutable
  and changing an entity's prefix only affects future records.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.meta import IdSequence

# Default prefixes & pad widths per entity type (seeded on first use).
DEFAULT_PREFIXES: dict[str, tuple[str, int]] = {
    "transaction": ("TRN", 10),
    "partner": ("PRT", 5),
    "beneficiary": ("BEN", 5),
    "expense_category": ("EC", 5),
    "cash_flow_item": ("CFI", 5),
    "account": ("ACC", 5),
    "installment_plan": ("INS", 5),
    "loan": ("LON", 5),
    "goal": ("GOL", 5),
    "investment_holding": ("INV", 5),
    "budget": ("BUD", 5),
    "document_import": ("DOC", 5),
    "categorization_rule": ("RUL", 5),
    "code_list": ("CDL", 5),
    "code_value": ("CDV", 6),
    "country": ("CTY", 5),
    "institution": ("INST"[:3], 5),  # 'INS' collides with installment; use 'IST'
    "household": ("HH", 5),
    "app_user": ("USR", 5),
    "role": ("ROL", 5),
    "user_role": ("URL", 5),
    "recurrence_profile": ("REC", 5),
    "holiday_calendar": ("HOL", 5),
    "amortization": ("AMT", 5),
    "tag": ("TAG", 5),
    "llm_provider": ("LLM", 5),
    "feature_llm_binding": ("FLB", 5),
    "integration_endpoint": ("IEP", 5),
}

# Resolve the institution prefix collision explicitly.
DEFAULT_PREFIXES["institution"] = ("IST", 5)


def _ensure_row(db: Session, entity_type: str) -> IdSequence:
    prefix, pad = DEFAULT_PREFIXES.get(entity_type, (entity_type[:3].upper(), 5))
    row = db.execute(
        select(IdSequence).where(IdSequence.prefix == prefix).with_for_update()
    ).scalar_one_or_none()
    if row is None:
        row = IdSequence(prefix=prefix, entity_type=entity_type, pad_width=pad, current_seq=0)
        db.add(row)
        db.flush()
        # re-lock the newly inserted row
        row = db.execute(
            select(IdSequence).where(IdSequence.prefix == prefix).with_for_update()
        ).scalar_one()
    return row


def next_mnemonic(db: Session, entity_type: str) -> str:
    """Allocate and return the next mnemonic ID (e.g. TRN-0000000001)."""
    row = _ensure_row(db, entity_type)
    row.current_seq += 1
    number = str(row.current_seq).zfill(row.pad_width)
    return f"{row.prefix}-{number}"