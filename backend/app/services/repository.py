"""Generic repository with search, filtering, sort, pagination, soft delete.

Reused by every entity's CRUD endpoints (Decision #25). Also assigns mnemonic
IDs, writes audit entries, and emits CloudEvents on state changes.
"""

import uuid as uuid_lib
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from sqlalchemy import String, asc, cast, desc, func, or_, select
from sqlalchemy.orm import Session

from app.models.base import BaseEntity
from app.services.audit import record_audit
from app.services.events import emit_event
from app.services.id_sequence import next_mnemonic

T = TypeVar("T", bound=BaseEntity)


@dataclass
class Page(Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class Repository(Generic[T]):
    def __init__(self, model: type[T], entity_type: str, event_domain: str):
        self.model = model
        self.entity_type = entity_type
        self.event_domain = event_domain  # e.g. "partner" -> com.pfm.partner.created

    # ---- read ----
    def get(self, db: Session, uuid: uuid_lib.UUID, include_deleted: bool = False) -> T | None:
        stmt = select(self.model).where(self.model.uuid == uuid)
        if not include_deleted:
            stmt = stmt.where(self.model.deleted_at.is_(None))
        return db.execute(stmt).scalar_one_or_none()

    def list(
        self,
        db: Session,
        *,
        search: str | None = None,
        filters: dict[str, Any] | None = None,
        sort: str | None = None,
        limit: int = 50,
        offset: int = 0,
        include_deleted: bool = False,
        search_columns: list[str] | None = None,
    ) -> Page[T]:
        stmt = select(self.model)
        count_stmt = select(func.count()).select_from(self.model)

        conditions = []
        if not include_deleted:
            conditions.append(self.model.deleted_at.is_(None))

        # Free-text search across name, mnemonic_id, description (+ extra columns).
        if search:
            cols = ["name", "mnemonic_id", "description"] + (search_columns or [])
            like = f"%{search.lower()}%"
            search_clauses = []
            for col in cols:
                attr = getattr(self.model, col, None)
                if attr is not None:
                    search_clauses.append(func.lower(cast(attr, String)).like(like))
            if search_clauses:
                conditions.append(or_(*search_clauses))

        # Structured equality/range filters.
        for key, value in (filters or {}).items():
            if value is None:
                continue
            if key.endswith("__gte"):
                attr = getattr(self.model, key[:-5], None)
                if attr is not None:
                    conditions.append(attr >= value)
            elif key.endswith("__lte"):
                attr = getattr(self.model, key[:-5], None)
                if attr is not None:
                    conditions.append(attr <= value)
            elif key.endswith("__in"):
                attr = getattr(self.model, key[:-4], None)
                if attr is not None:
                    conditions.append(attr.in_(value))
            else:
                attr = getattr(self.model, key, None)
                if attr is not None:
                    conditions.append(attr == value)

        for cond in conditions:
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        total = db.execute(count_stmt).scalar_one()

        # Sort: "field" asc, "-field" desc.
        if sort:
            field_name = sort.lstrip("-")
            attr = getattr(self.model, field_name, None)
            if attr is not None:
                stmt = stmt.order_by(desc(attr) if sort.startswith("-") else asc(attr))
        else:
            stmt = stmt.order_by(self.model.created_at.desc())

        stmt = stmt.limit(limit).offset(offset)
        items = list(db.execute(stmt).scalars())
        return Page(items=items, total=total, limit=limit, offset=offset)

    # ---- write ----
    def create(
        self, db: Session, data: dict, *, actor: uuid_lib.UUID | None = None,
        household_id: uuid_lib.UUID | None = None, source_channel: str = "api",
    ) -> T:
        obj = self.model(**data)
        obj.mnemonic_id = next_mnemonic(db, self.entity_type)
        if household_id is not None and getattr(obj, "household_id", None) is None:
            obj.household_id = household_id
        obj.created_by = actor
        db.add(obj)
        db.flush()
        record_audit(
            db, entity_type=self.entity_type, entity_uuid=obj.uuid,
            entity_mnemonic=obj.mnemonic_id, operation="create",
            after=_snapshot(obj), changed_by=actor, source_channel=source_channel,
        )
        emit_event(
            db, event_type=f"com.pfm.{self.event_domain}.created",
            subject=obj.mnemonic_id, data={"uuid": str(obj.uuid)},
        )
        db.commit()
        db.refresh(obj)
        return obj

    def update(
        self, db: Session, obj: T, data: dict, *, actor: uuid_lib.UUID | None = None,
        source_channel: str = "api",
    ) -> T:
        before = _snapshot(obj)
        for key, value in data.items():
            if hasattr(obj, key) and key not in {"uuid", "mnemonic_id", "created_at", "created_by"}:
                setattr(obj, key, value)
        obj.updated_by = actor
        db.flush()
        record_audit(
            db, entity_type=self.entity_type, entity_uuid=obj.uuid,
            entity_mnemonic=obj.mnemonic_id, operation="update",
            before=before, after=_snapshot(obj), changed_by=actor,
            source_channel=source_channel,
        )
        emit_event(
            db, event_type=f"com.pfm.{self.event_domain}.updated",
            subject=obj.mnemonic_id, data={"uuid": str(obj.uuid)},
        )
        db.commit()
        db.refresh(obj)
        return obj

    def soft_delete(
        self, db: Session, obj: T, *, actor: uuid_lib.UUID | None = None,
        source_channel: str = "api",
    ) -> None:
        before = _snapshot(obj)
        obj.deleted_at = func.now()
        obj.updated_by = actor
        db.flush()
        record_audit(
            db, entity_type=self.entity_type, entity_uuid=obj.uuid,
            entity_mnemonic=obj.mnemonic_id, operation="delete",
            before=before, changed_by=actor, source_channel=source_channel,
        )
        emit_event(
            db, event_type=f"com.pfm.{self.event_domain}.deleted",
            subject=obj.mnemonic_id, data={"uuid": str(obj.uuid)},
        )
        db.commit()


def _snapshot(obj: Any) -> dict:
    """JSON-serialisable snapshot of a model's column values."""
    result: dict[str, Any] = {}
    for column in obj.__table__.columns:
        value = getattr(obj, column.name)
        if isinstance(value, uuid_lib.UUID):
            value = str(value)
        elif hasattr(value, "isoformat"):
            value = value.isoformat()
        result[column.name] = value
    return result