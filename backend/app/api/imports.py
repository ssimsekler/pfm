"""Import pipeline API (spec 3.1–3.3), two modes (Session 815, Batch 12):

  POST /api/v1/imports  (mode=statement|bulk)  upload → (statement) LLM-extract or
                                               (bulk) deterministic resolve → rows
  GET  /api/v1/imports                          list imports
  GET  /api/v1/imports/bulk/template            download the bulk CSV template
  GET  /api/v1/imports/{id}                     import summary
  GET  /api/v1/imports/{id}/rows                parsed+mapped rows for review
  PATCH/api/v1/imports/{id}/rows/{rid}          amend a row's mapped values
  POST /api/v1/imports/{id}/commit              create transactions from rows

Both modes always land on the validation screen; the user confirms/edits before
commit (Decision #27). **Statement** files are messy/real-world so they are read
by the LLM (needs the LLM master switch on + a provider — Batch 11). **Bulk**
files are clean/structured (mnemonic-ID columns), resolved deterministically with
no LLM. Committed transactions carry a note referencing the original filename
(spec 3.3) and (statement) a dedup hash.
"""

import uuid as uuid_lib
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.schemas import EntityOut, PageOut
from app.core.database import get_db
from app.core.security import Principal, get_current_principal, require_write
from app.models import financial as fin
from app.models import imports as imp
from app.models.meta import CodeList, CodeValue
from app.services import import_bulk, import_llm, import_mapper, storage
from app.services.repository import Repository

router = APIRouter(prefix="/api/v1/imports", tags=["imports"])

_import_repo = Repository(imp.DocumentImport, entity_type="document_import", event_domain="document_import")
_txn_repo = Repository(fin.Transaction, entity_type="transaction", event_domain="transaction")
_partner_repo = Repository(fin.Partner, entity_type="partner", event_domain="partner")


def _cv(db: Session, list_key: str, code: str) -> uuid_lib.UUID | None:
    cl = db.execute(select(CodeList).where(CodeList.list_key == list_key)).scalar_one_or_none()
    if cl is None:
        return None
    cv = db.execute(
        select(CodeValue).where(CodeValue.code_list_id == cl.uuid, CodeValue.code == code)
    ).scalar_one_or_none()
    return cv.uuid if cv else None


def _resolve_account_hint(db: Session, hint) -> uuid_lib.UUID | None:
    """Statement rows may carry an `account_hint` (masked no / IBAN / name).
    Resolve it to an account UUID; return None when it can't be matched."""
    token = (str(hint) if hint is not None else "").strip()
    if not token:
        return None
    conds = [fin.Account.name == token]
    for col in ("iban", "bank_account_number", "card_number"):
        if hasattr(fin.Account, col):
            conds.append(getattr(fin.Account, col) == token)
    acc = db.execute(
        select(fin.Account).where(or_(*conds), fin.Account.deleted_at.is_(None))
    ).scalar_one_or_none()
    if acc is not None:
        return acc.uuid
    # Masked numbers (e.g. "****1234"): match by trailing 4 digits.
    digits = "".join(ch for ch in token if ch.isdigit())
    if len(digits) >= 4:
        for col in ("iban", "bank_account_number", "card_number"):
            if not hasattr(fin.Account, col):
                continue
            acc = db.execute(
                select(fin.Account).where(
                    getattr(fin.Account, col).ilike(f"%{digits[-4:]}"),
                    fin.Account.deleted_at.is_(None),
                )
            ).scalar_one_or_none()
            if acc is not None:
                return acc.uuid
    return None


def _to_date(value) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)).date()
    except ValueError:
        try:
            return datetime.strptime(str(value), "%Y-%m-%d").date()
        except ValueError:
            return None


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class ImportOut(EntityOut):
    original_filename: str
    mime: str | None = None
    status_cv_id: uuid_lib.UUID | None = None
    parse_summary: dict | None = None


class ImportRowOut(BaseModel):
    uuid: uuid_lib.UUID
    raw_data: dict | None = None
    mapped_values: dict | None = None
    mapping_status_cv_id: uuid_lib.UUID | None = None
    dedup_hash: str | None = None
    target_txn_id: uuid_lib.UUID | None = None

    class Config:
        from_attributes = True


class RowAmend(BaseModel):
    mapped_values: dict


class CommitIn(BaseModel):
    account_id: uuid_lib.UUID
    default_currency: str | None = None
    skip_duplicates: bool = True


# --------------------------------------------------------------------------- #
# Bulk template
# --------------------------------------------------------------------------- #
@router.get("/bulk/template")
def bulk_template(_: Principal = Depends(get_current_principal)):
    """Download the structured-bulk CSV template (headers + one example row)."""
    return Response(
        content=import_bulk.template_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="pfm_bulk_import_template.csv"'},
    )


# --------------------------------------------------------------------------- #
# Upload → parse/extract → rows
# --------------------------------------------------------------------------- #
@router.post("", response_model=ImportOut, status_code=201)
async def upload_import(
    file: UploadFile = File(...),
    country: str | None = Form(None),
    mode: str = Form("statement"),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_write),
):
    mode = (mode or "statement").strip().lower()
    if mode not in ("statement", "bulk"):
        raise HTTPException(status_code=422, detail="mode must be 'statement' or 'bulk'")

    content = await file.read()
    key = f"imports/{uuid_lib.uuid4()}_{file.filename}"
    storage.put_object(key, content, content_type=file.content_type or "application/octet-stream")

    doc = _import_repo.create(
        db,
        {
            "name": file.filename or "import",
            "original_filename": file.filename or "import",
            "storage_key": key,
            "mime": file.content_type,
            "status_cv_id": _cv(db, "import_status", "uploaded"),
        },
    )

    if mode == "bulk":
        return _ingest_bulk(db, doc, content, file.filename or "", file.content_type)
    return _ingest_statement(db, doc, content, file.filename or "", file.content_type)


def _ingest_statement(db: Session, doc, content: bytes, filename: str, mime: str | None):
    """Statement mode: LLM extraction → map → rows for the review screen."""
    try:
        parsed = import_llm.extract_transactions(db, content, filename, mime)
    except Exception as exc:  # noqa: BLE001 — friendly 422 (LLM off / unreadable / bad JSON)
        _import_repo.update(db, doc, {
            "status_cv_id": _cv(db, "import_status", "failed"),
            "parse_summary": {"error": str(exc)},
        })
        db.commit()
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    matched = new = unmapped = 0
    for entry in parsed:
        mapped = entry.get("mapped", {})
        mapping = import_mapper.map_row(db, mapped)
        status = mapping["status"]
        matched += status == "matched"
        new += status == "new"
        unmapped += status == "unmapped"
        row = imp.DocumentImportRow(
            import_id=doc.uuid,
            raw_data=entry.get("raw", {}),
            mapped_values={**mapped, **mapping["proposal"]},
            mapping_status_cv_id=_cv(db, "mapping_status", status),
            dedup_hash=import_mapper.dedup_hash(mapped),
        )
        db.add(row)

    _import_repo.update(db, doc, {
        "status_cv_id": _cv(db, "import_status", "parsed"),
        "parse_summary": {
            "mode": "statement", "rows": len(parsed),
            "matched": matched, "new": new, "unmapped": unmapped,
        },
    })
    db.commit()
    db.refresh(doc)
    return doc


def _ingest_bulk(db: Session, doc, content: bytes, filename: str, mime: str | None):
    """Bulk mode: deterministic resolve (mnemonic-ID columns) → rows w/ errors."""
    try:
        resolved = import_bulk.resolve_rows(db, content, filename, mime)
    except Exception as exc:  # noqa: BLE001
        _import_repo.update(db, doc, {
            "status_cv_id": _cv(db, "import_status", "failed"),
            "parse_summary": {"error": str(exc)},
        })
        db.commit()
        raise HTTPException(status_code=422, detail=f"Bulk parse failed: {exc}") from exc

    ok = 0
    errored = 0
    for entry in resolved:
        errors = entry.get("errors") or []
        if errors:
            errored += 1
        else:
            ok += 1
        # Store resolved ids in mapped_values; keep display + errors alongside so
        # the review grid can show labels and flag bad rows. Bulk rows are
        # deterministic → no dedup hash / no mapping-memory learning.
        mv = dict(entry.get("values") or {})
        mv["_display"] = entry.get("display") or {}
        mv["_errors"] = errors
        mv["_bulk"] = True
        db.add(imp.DocumentImportRow(
            import_id=doc.uuid,
            raw_data=entry.get("raw", {}),
            mapped_values=mv,
            mapping_status_cv_id=_cv(db, "mapping_status", "unmapped" if errors else "matched"),
        ))

    _import_repo.update(db, doc, {
        "status_cv_id": _cv(db, "import_status", "parsed"),
        "parse_summary": {"mode": "bulk", "rows": len(resolved), "ok": ok, "errored": errored},
    })
    db.commit()
    db.refresh(doc)
    return doc


@router.get("", response_model=PageOut[ImportOut])
def list_imports(
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
    limit: int = 50,
    offset: int = 0,
):
    page = _import_repo.list(db, limit=limit, offset=offset, search_columns=["original_filename"])
    return PageOut(
        items=[ImportOut.model_validate(i) for i in page.items],
        total=page.total, limit=page.limit, offset=page.offset,
    )


@router.get("/{import_id}", response_model=ImportOut)
def get_import(
    import_id: uuid_lib.UUID,
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
):
    doc = _import_repo.get(db, import_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="import not found")
    return doc


@router.get("/{import_id}/rows", response_model=list[ImportRowOut])
def list_rows(
    import_id: uuid_lib.UUID,
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
):
    stmt = select(imp.DocumentImportRow).where(imp.DocumentImportRow.import_id == import_id)
    return list(db.execute(stmt).scalars())


@router.patch("/{import_id}/rows/{row_id}", response_model=ImportRowOut)
def amend_row(
    import_id: uuid_lib.UUID,
    row_id: uuid_lib.UUID,
    payload: RowAmend,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_write),
):
    row = db.get(imp.DocumentImportRow, row_id)
    if row is None or row.import_id != import_id:
        raise HTTPException(status_code=404, detail="import row not found")
    row.mapped_values = {**(row.mapped_values or {}), **payload.mapped_values}
    db.commit()
    db.refresh(row)
    return row


# --------------------------------------------------------------------------- #
# Commit → create transactions
# --------------------------------------------------------------------------- #
@router.post("/{import_id}/commit")
def commit_import(
    import_id: uuid_lib.UUID,
    payload: CommitIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_write),
):
    doc = _import_repo.get(db, import_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="import not found")

    rows = list(db.execute(
        select(imp.DocumentImportRow).where(imp.DocumentImportRow.import_id == import_id)
    ).scalars())

    created = 0
    skipped = 0
    for row in rows:
        if row.target_txn_id is not None:
            skipped += 1
            continue
        mv = row.mapped_values or {}

        # Bulk rows are pre-resolved; write them directly (skip errored rows).
        if mv.get("_bulk"):
            if mv.get("_errors"):
                skipped += 1
                continue
            values = import_bulk.values_for_commit(mv)
            account_id = values.get("account_id") or str(payload.account_id)
            values["account_id"] = (
                uuid_lib.UUID(account_id) if isinstance(account_id, str) else account_id
            )
            if not values.get("currency"):
                values["currency"] = payload.default_currency or "AED"
            values.setdefault("txn_date", date.today())
            values["source_document_id"] = doc.uuid
            values["note"] = (
                (values.get("note") + " · " if values.get("note") else "")
                + f"Imported from {doc.original_filename} (import {doc.mnemonic_id})"
            )
            txn = _txn_repo.create(db, values)
            row.target_txn_id = txn.uuid
            created += 1
            continue

        # --- Statement rows (LLM-extracted + mapped) ---
        # Dedup: same hash already committed in this DB?
        if payload.skip_duplicates and row.dedup_hash:
            dup = db.execute(
                select(imp.DocumentImportRow).where(
                    imp.DocumentImportRow.dedup_hash == row.dedup_hash,
                    imp.DocumentImportRow.target_txn_id.isnot(None),
                )
            ).scalar_one_or_none()
            if dup is not None:
                skipped += 1
                continue

        # Resolve amount / date / currency.
        try:
            amount = Decimal(str(mv.get("amount"))) if mv.get("amount") is not None else None
        except (InvalidOperation, TypeError):
            amount = None
        if amount is None:
            skipped += 1
            continue
        txn_date = _to_date(mv.get("date")) or date.today()
        currency = mv.get("currency") or payload.default_currency or "AED"

        # Resolve/auto-create partner.
        partner_id = mv.get("partner_id")
        if not partner_id and mv.get("partner_name_new"):
            partner = _partner_repo.create(db, {"name": mv["partner_name_new"]})
            partner_id = str(partner.uuid)

        # Per-row account: explicit mapped id → resolved account_hint → default.
        account_id = mv.get("account_id")
        if not account_id and mv.get("account_hint"):
            resolved = _resolve_account_hint(db, mv.get("account_hint"))
            if resolved is not None:
                account_id = str(resolved)
        account_id = account_id or str(payload.account_id)

        category_id = mv.get("expense_category_id")

        note = f"Imported from {doc.original_filename} (import {doc.mnemonic_id})"
        txn = _txn_repo.create(
            db,
            {
                "name": mv.get("description") or mv.get("partner_name") or doc.original_filename,
                "account_id": uuid_lib.UUID(account_id) if isinstance(account_id, str) else account_id,
                "txn_date": txn_date,
                "amount": amount,
                "currency": currency,
                "partner_id": uuid_lib.UUID(partner_id) if partner_id else None,
                "expense_category_id": (
                    uuid_lib.UUID(category_id) if category_id else None
                ),
                "source_document_id": doc.uuid,
                "note": note,
            },
        )
        row.target_txn_id = txn.uuid
        created += 1

        # Bug 17: learn from the accepted mapping (statement text → partner/category).
        source_text = (mv.get("description") or mv.get("partner") or "").strip()
        import_mapper.record_memory(
            db,
            source_text,
            uuid_lib.UUID(partner_id) if partner_id else None,
            uuid_lib.UUID(category_id) if category_id else None,
        )

    _import_repo.update(db, doc, {"status_cv_id": _cv(db, "import_status", "committed")})
    db.commit()
    return {"import": str(import_id), "created": created, "skipped": skipped}


ALL_ROUTERS = [router]
