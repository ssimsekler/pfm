"""Value-help API: expose configurable code lists for comboboxes (Decision #23/#25)."""

import uuid as uuid_lib

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
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