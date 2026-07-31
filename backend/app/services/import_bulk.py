"""Structured bulk transaction import (Session 815, Batch 12).

Direct bulk entry — NO mapping/LLM. The user provides complete transaction
details in a CSV/XLSX. Header names are the **lowercase DB field names** for
direct fields and **entity names** for related entities (values = the related
entity's mnemonic_id; currency/direction by code):

  Direct:   name, description, txn_date, amount, currency, direction, note,
            booking_date
  Related:  account (required), partner, beneficiary, expense_category, goal
            (values are mnemonic_id; partner/expense_category also accept a name)

Each row is resolved to concrete ids and validated. Rows with errors are flagged
so the user can fix them in the review grid before submitting.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import financial as fin
from app.models.meta import CodeList, CodeValue

# Recognized headers (lowercase). Related-entity columns resolve by mnemonic_id.
DIRECT_FIELDS = {"name", "description", "txn_date", "amount", "currency",
                 "direction", "note", "booking_date"}
ENTITY_FIELDS = {
    "account": (fin.Account, "account_id"),
    "partner": (fin.Partner, "partner_id"),
    "beneficiary": (fin.Beneficiary, "beneficiary_id"),
    "expense_category": (fin.ExpenseCategory, "expense_category_id"),
}

TEMPLATE_HEADERS = [
    "account", "txn_date", "amount", "currency", "direction",
    "name", "description", "partner", "beneficiary", "expense_category",
    "goal", "note", "booking_date",
]


def template_csv() -> str:
    """Return a CSV template (header row + one example comment row)."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(TEMPLATE_HEADERS)
    w.writerow([
        "ACC0001", "2026-01-31", "-125.50", "AED", "debit",
        "Groceries", "Weekly shop", "PRT0007", "", "CAT0003", "", "", "",
    ])
    return buf.getvalue()


def _read_rows(content: bytes, filename: str, mime: str | None) -> list[dict]:
    name = (filename or "").lower()
    if name.endswith((".xlsx", ".xls")) or (mime and "sheet" in (mime or "")):
        import openpyxl

        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        ws = wb.active
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
        rows = [r for r in rows if any(c is not None and str(c).strip() for c in r)]
        if not rows:
            return []
        headers = [str(c).strip().lower() if c is not None else "" for c in rows[0]]
        out = []
        for r in rows[1:]:
            out.append({headers[i]: (r[i] if i < len(r) else None) for i in range(len(headers))})
        return out
    # CSV / default
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    return [{(k or "").strip().lower(): v for k, v in row.items()} for row in reader]


def _by_mnemonic_or_name(db: Session, model, value: str, allow_name: bool):
    v = (value or "").strip()
    if not v:
        return None
    row = db.execute(
        select(model).where(model.mnemonic_id == v, model.deleted_at.is_(None))
    ).scalar_one_or_none()
    if row is None and allow_name and hasattr(model, "name"):
        row = db.execute(
            select(model).where(func.lower(model.name) == v.lower(), model.deleted_at.is_(None))
        ).scalar_one_or_none()
    return row


def _direction_cv(db: Session, code: str):
    code = (code or "").strip().lower()
    if not code:
        return None
    cl = db.execute(select(CodeList).where(CodeList.list_key == "txn_direction")).scalar_one_or_none()
    if cl is None:
        return None
    return db.execute(
        select(CodeValue).where(CodeValue.code_list_id == cl.uuid, func.lower(CodeValue.code) == code)
    ).scalar_one_or_none()


def _parse_amount(v: Any):
    if v is None or str(v).strip() == "":
        return None, "amount required"
    try:
        return float(str(v).replace(",", "").strip()), None
    except ValueError:
        return None, f"invalid amount '{v}'"


def _parse_date(v: Any):
    s = str(v or "").strip()
    if not s:
        return None, "txn_date required"
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat(), None
        except ValueError:
            continue
    return None, f"invalid date '{v}'"


def resolve_rows(db: Session, content: bytes, filename: str, mime: str | None) -> list[dict]:
    """Parse + resolve a structured bulk file. Returns rows:
      { raw, values: {field: id/value}, display: {label...}, errors: [str] }
    No DB writes — this is the preview for the review grid."""
    raw_rows = _read_rows(content, filename, mime)
    result: list[dict] = []
    for raw in raw_rows:
        values: dict[str, Any] = {}
        display: dict[str, Any] = {}
        errors: list[str] = []

        # Direct fields
        values["name"] = (raw.get("name") or "").strip() or None
        values["description"] = (raw.get("description") or "").strip() or None
        values["note"] = (raw.get("note") or "").strip() or None
        values["currency"] = (raw.get("currency") or "").strip().upper() or None

        amt, aerr = _parse_amount(raw.get("amount"))
        if aerr:
            errors.append(aerr)
        values["amount"] = amt

        d, derr = _parse_date(raw.get("txn_date"))
        if derr:
            errors.append(derr)
        values["txn_date"] = d

        if raw.get("booking_date"):
            bd, bderr = _parse_date(raw.get("booking_date"))
            if bderr:
                errors.append(bderr)
            values["booking_date"] = bd

        # Direction (code)
        dir_cv = _direction_cv(db, raw.get("direction"))
        if dir_cv is None:
            errors.append("direction must be a valid code (e.g. debit/credit)")
        else:
            values["direction_cv_id"] = str(dir_cv.uuid)
            display["direction"] = dir_cv.code

        # Account (required)
        acc = _by_mnemonic_or_name(db, fin.Account, raw.get("account") or "", allow_name=True)
        if acc is None:
            errors.append(f"account '{raw.get('account','')}' not found (use its mnemonic ID)")
        else:
            values["account_id"] = str(acc.uuid)
            display["account"] = acc.mnemonic_id

        # Optional related entities
        for col, (model, field) in ENTITY_FIELDS.items():
            if col == "account":
                continue
            v = raw.get(col)
            if v and str(v).strip():
                row = _by_mnemonic_or_name(db, model, str(v), allow_name=col in ("partner", "expense_category"))
                if row is None:
                    errors.append(f"{col} '{v}' not found")
                else:
                    values[field] = str(row.uuid)
                    display[col] = getattr(row, "mnemonic_id", None) or getattr(row, "name", None)

        # Goal (optional)
        gv = raw.get("goal")
        if gv and str(gv).strip():
            from app.models.scheduling import Goal  # local import (avoid cycle)

            grow = db.execute(
                select(Goal).where(Goal.mnemonic_id == str(gv).strip(), Goal.deleted_at.is_(None))
            ).scalar_one_or_none()
            if grow is None:
                errors.append(f"goal '{gv}' not found")
            else:
                values["goal_id"] = str(grow.uuid)
                display["goal"] = grow.mnemonic_id

        result.append({"raw": raw, "values": values, "display": display, "errors": errors})
    return result


def values_for_commit(values: dict) -> dict:
    """Map a resolved preview row's `values` → Transaction column values.

    `values` already holds resolved ids (account_id/partner_id/…), a
    `direction_cv_id`, ISO dates and a numeric amount, so this is a thin,
    NULL-dropping projection onto the Transaction columns. `name` falls back to
    the description (transactions require a name)."""
    out: dict[str, Any] = {}
    name = values.get("name") or values.get("description") or "Imported transaction"
    out["name"] = name
    for key in (
        "description", "note", "currency", "amount", "txn_date", "booking_date",
        "direction_cv_id", "account_id", "partner_id", "beneficiary_id",
        "expense_category_id", "goal_id",
    ):
        v = values.get(key)
        if v is not None:
            out[key] = v
    return out
