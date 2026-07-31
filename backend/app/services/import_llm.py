"""LLM-based bank-statement transaction extraction (Session 815, Batch 12).

Statement imports are extracted by the LLM (not brittle table heuristics). We:
  1. Flatten the uploaded file to text (PDF text / CSV / XLSX dump).
  2. Feed the LLM: the task prompt + the mapping context —
       - categorization rules (conditions/actions),
       - the list of existing partners (suppliers),
       - the list of existing expense categories,
       - historical mapping statistics (source_text → partner/category, accept_count).
  3. Ask for a strict JSON array of transactions; parse and normalize.

The extracted rows then flow through the existing `import_mapper.map_row` so
names resolve to IDs (and new partners are created on commit). Statements may
cover multiple accounts — each row may carry an `account_hint`
(masked no / IBAN / name) that commit resolves to an account, else the default.

Gated by `llm.master_enabled` + a working provider/credential (Batch 11).
"""

from __future__ import annotations

import io
import json
import re
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.financial import ExpenseCategory, Partner
from app.models.imports import ImportMappingMemory
from app.services import llm_gateway


# --------------------------------------------------------------------------- #
# Text extraction
# --------------------------------------------------------------------------- #
def extract_text(content: bytes, filename: str, mime: str | None = None) -> str:
    """Flatten an uploaded statement to plain text for the LLM."""
    name = (filename or "").lower()
    try:
        if name.endswith(".pdf") or (mime and "pdf" in mime):
            import pdfplumber

            out: list[str] = []
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages:
                    txt = page.extract_text() or ""
                    if txt.strip():
                        out.append(txt)
            return "\n\n".join(out)
        if name.endswith((".xlsx", ".xls")) or (mime and "sheet" in (mime or "")):
            import openpyxl

            wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
            lines: list[str] = []
            for ws in wb.worksheets:
                for row in ws.iter_rows(values_only=True):
                    cells = [("" if c is None else str(c)) for c in row]
                    if any(c.strip() for c in cells):
                        lines.append("\t".join(cells))
            return "\n".join(lines)
    except Exception:  # noqa: BLE001 — fall through to raw decode
        pass
    # CSV / text / fallback.
    return content.decode("utf-8-sig", errors="replace")


# --------------------------------------------------------------------------- #
# Mapping context
# --------------------------------------------------------------------------- #
def _partners(db: Session, limit: int = 400) -> list[str]:
    return [
        p.name for p in db.execute(
            select(Partner).where(Partner.deleted_at.is_(None)).order_by(Partner.name).limit(limit)
        ).scalars()
    ]


def _categories(db: Session, limit: int = 400) -> list[str]:
    return [
        c.name for c in db.execute(
            select(ExpenseCategory).where(ExpenseCategory.deleted_at.is_(None))
            .order_by(ExpenseCategory.name).limit(limit)
        ).scalars()
    ]


def _rules(db: Session) -> list[dict]:
    from app.models.automation import CategorizationRule

    rows = db.execute(
        select(CategorizationRule).where(
            CategorizationRule.enabled.is_(True), CategorizationRule.deleted_at.is_(None)
        ).order_by(CategorizationRule.priority.asc())
    ).scalars()
    out = []
    for r in rows:
        out.append({"conditions": r.conditions or {}, "actions": r.actions or {}})
    return out


def _memory_stats(db: Session, limit: int = 100) -> list[dict]:
    """Top learned mappings: source_text → partner/category with accept_count."""
    rows = db.execute(
        select(ImportMappingMemory).order_by(ImportMappingMemory.accept_count.desc()).limit(limit)
    ).scalars()
    stats = []
    for m in rows:
        partner = db.get(Partner, m.mapped_partner_id) if m.mapped_partner_id else None
        cat = db.get(ExpenseCategory, m.mapped_category_id) if m.mapped_category_id else None
        stats.append({
            "text": m.source_text,
            "partner": partner.name if partner else None,
            "category": cat.name if cat else None,
            "count": m.accept_count or 0,
        })
    return stats


# --------------------------------------------------------------------------- #
# LLM extraction
# --------------------------------------------------------------------------- #
def _build_prompt(text: str, partners: list[str], categories: list[str],
                 rules: list[dict], memory: list[dict]) -> str:
    # Keep the statement text bounded so we don't overflow the context window.
    snippet = text if len(text) <= 16000 else text[:16000]
    return (
        "You extract transactions from a BANK STATEMENT (it may cover multiple "
        "accounts). Read the statement text and return a STRICT JSON array only "
        "(no prose, no markdown). Each element:\n"
        '{"account_hint": string|null, "txn_date": "YYYY-MM-DD", "amount": number, '
        '"currency": string|null, "description": string, "partner": string|null, '
        '"category": string|null, "direction": "debit"|"credit"|null}\n\n'
        "Rules:\n"
        "- Keep amount, date and currency EXACTLY as printed (normalize date to "
        "ISO YYYY-MM-DD; amount as a number, negative for debits if the statement "
        "shows outflows as negative).\n"
        "- Put the full source line/row text in `description`.\n"
        "- Map `partner` to one of the allowed partners when it clearly matches, "
        "else use the merchant text as-is.\n"
        "- Map `category` to one of the allowed categories using the rules and "
        "history below; if unsure leave it null.\n"
        "- When the statement lists several accounts, set `account_hint` to the "
        "account's masked number / IBAN / name shown for that transaction.\n"
        "- Return ONLY transactions; skip headers, balances and summary lines.\n\n"
        f"Allowed partners: {partners}\n"
        f"Allowed categories: {categories}\n"
        f"Categorization rules (conditions→actions): {json.dumps(rules)[:4000]}\n"
        f"Historical mappings (text→partner/category, count): {json.dumps(memory)[:4000]}\n\n"
        f"STATEMENT TEXT:\n{snippet}\n"
    )


def _coerce_json_array(reply: str) -> list[dict]:
    """Extract a JSON array from the model reply (tolerant of code fences/prose)."""
    if not reply:
        return []
    s = reply.strip()
    # Strip markdown fences.
    s = re.sub(r"^```(?:json)?", "", s).strip()
    s = re.sub(r"```$", "", s).strip()
    # Find the first [...] block.
    start = s.find("[")
    end = s.rfind("]")
    if start != -1 and end != -1 and end > start:
        s = s[start : end + 1]
    try:
        data = json.loads(s)
        return data if isinstance(data, list) else []
    except Exception:  # noqa: BLE001
        return []


def extract_transactions(db: Session, content: bytes, filename: str,
                        mime: str | None = None) -> list[dict]:
    """Return normalized parsed rows [{raw, mapped}] using the LLM.

    Raises RuntimeError with a friendly message when the LLM is disabled or
    yields nothing, so the API can surface a clear 422.
    """
    if not llm_gateway.is_enabled(db):
        raise RuntimeError(
            "LLM is disabled. Enable the LLM master switch and configure a "
            "provider/credential to import statements."
        )
    text = extract_text(content, filename, mime)
    if not text.strip():
        raise RuntimeError("Could not read any text from the uploaded file.")

    prompt = _build_prompt(
        text, _partners(db), _categories(db), _rules(db), _memory_stats(db)
    )
    reply = llm_gateway.complete(db, "STATEMENT_EXTRACT", prompt)
    if not reply:
        raise RuntimeError(
            "The LLM did not return any transactions. Check the provider/model "
            "(local Ollama needs a capable model pulled) and try again."
        )

    items = _coerce_json_array(reply)
    if not items:
        raise RuntimeError("The LLM response could not be parsed into transactions.")

    rows: list[dict] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        mapped = {
            "date": it.get("txn_date") or it.get("date"),
            "amount": it.get("amount"),
            "currency": it.get("currency"),
            "description": it.get("description") or "",
            "partner": it.get("partner"),
            "category": it.get("category"),
            "direction": it.get("direction"),
            "account_hint": it.get("account_hint"),
        }
        rows.append({"raw": dict(it), "mapped": mapped})
    return rows