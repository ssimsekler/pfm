"""Value-help API: expose configurable code lists for comboboxes (Decision #23/#25).

Read endpoints power comboboxes. Admin endpoints (ADR #34) let users maintain
code *values*, honoring `code_list.is_system` / `allow_user_values` guards so
seeded system lists are protected.
"""

import uuid as uuid_lib

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import Principal, require_write
from app.models.meta import CodeList, CodeValue

router = APIRouter(prefix="/api/v1", tags=["value-help"])


class CodeValueOut(BaseModel):
    uuid: uuid_lib.UUID
    code: str
    label: str
    sort_order: int
    is_default: bool
    is_active: bool

    class Config:
        from_attributes = True


class CodeListOut(BaseModel):
    uuid: uuid_lib.UUID
    list_key: str
    name: str
    is_system: bool
    allow_user_values: bool

    class Config:
        from_attributes = True


@router.get("/code-lists", response_model=list[CodeListOut])
def list_code_lists(db: Session = Depends(get_db)) -> list[CodeList]:
    return list(db.execute(select(CodeList).order_by(CodeList.list_key)).scalars())


@router.get("/code-lists/{list_key}/values", response_model=list[CodeValueOut])
def list_code_values(
    list_key: str,
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
) -> list[CodeValue]:
    cl = db.execute(
        select(CodeList).where(CodeList.list_key == list_key)
    ).scalar_one_or_none()
    if cl is None:
        raise HTTPException(status_code=404, detail=f"Unknown code list '{list_key}'")
    stmt = select(CodeValue).where(CodeValue.code_list_id == cl.uuid)
    if active_only:
        stmt = stmt.where(CodeValue.is_active.is_(True))
    stmt = stmt.order_by(CodeValue.sort_order, CodeValue.label)
    return list(db.execute(stmt).scalars())


# ---------------------------------------------------------------------------
# Code-value admin (ADR #34) — create / update / deactivate values.
# System-locked lists (`is_system` and not `allow_user_values`) reject writes.
# ---------------------------------------------------------------------------
class CodeValueCreate(BaseModel):
    code: str
    label: str
    sort_order: int = 100
    is_default: bool = False
    is_active: bool = True


class CodeValuePatch(BaseModel):
    code: str | None = None
    label: str | None = None
    sort_order: int | None = None
    is_default: bool | None = None
    is_active: bool | None = None


def _get_list_or_404(db: Session, list_key: str) -> CodeList:
    cl = db.execute(
        select(CodeList).where(CodeList.list_key == list_key)
    ).scalar_one_or_none()
    if cl is None:
        raise HTTPException(status_code=404, detail=f"Unknown code list '{list_key}'")
    return cl


def _assert_editable(cl: CodeList) -> None:
    """System lists that don't allow user values are read-only."""
    if cl.is_system and not cl.allow_user_values:
        raise HTTPException(
            status_code=403,
            detail=f"Code list '{cl.list_key}' is system-managed and not editable.",
        )


@router.post("/code-lists/{list_key}/values", response_model=CodeValueOut, status_code=201)
def create_code_value(
    list_key: str,
    payload: CodeValueCreate,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_write),
) -> CodeValue:
    cl = _get_list_or_404(db, list_key)
    _assert_editable(cl)
    dup = db.execute(
        select(CodeValue).where(
            CodeValue.code_list_id == cl.uuid, CodeValue.code == payload.code
        )
    ).scalar_one_or_none()
    if dup is not None:
        raise HTTPException(status_code=409, detail=f"Code '{payload.code}' already exists.")
    cv = CodeValue(code_list_id=cl.uuid, **payload.model_dump())
    db.add(cv)
    db.commit()
    db.refresh(cv)
    return cv


@router.patch("/code-lists/{list_key}/values/{value_id}", response_model=CodeValueOut)
def update_code_value(
    list_key: str,
    value_id: uuid_lib.UUID,
    payload: CodeValuePatch,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_write),
) -> CodeValue:
    cl = _get_list_or_404(db, list_key)
    _assert_editable(cl)
    cv = db.get(CodeValue, value_id)
    if cv is None or cv.code_list_id != cl.uuid:
        raise HTTPException(status_code=404, detail="code value not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(cv, field, value)
    db.commit()
    db.refresh(cv)
    return cv


@router.delete("/code-lists/{list_key}/values/{value_id}")
def delete_code_value(
    list_key: str,
    value_id: uuid_lib.UUID,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_write),
):
    """Deactivate a value (soft) to preserve referential integrity with existing
    `*_cv_id` FKs; hard delete is intentionally avoided."""
    cl = _get_list_or_404(db, list_key)
    _assert_editable(cl)
    cv = db.get(CodeValue, value_id)
    if cv is None or cv.code_list_id != cl.uuid:
        raise HTTPException(status_code=404, detail="code value not found")
    cv.is_active = False
    db.commit()
    return {"deactivated": True, "uuid": str(value_id)}
