"""Shared Pydantic schemas for CRUD responses and list envelopes."""

import uuid as uuid_lib
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel

TItem = TypeVar("TItem")


class ORMModel(BaseModel):
    class Config:
        from_attributes = True


class EntityOut(ORMModel):
    uuid: uuid_lib.UUID
    mnemonic_id: str
    name: str
    description: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PageOut(BaseModel, Generic[TItem]):
    items: list[TItem]
    total: int
    limit: int
    offset: int


class DeleteResult(BaseModel):
    deleted: bool = True
    uuid: uuid_lib.UUID