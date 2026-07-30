"""Security & tenancy models: household, app_user, role, user_role."""

import uuid as uuid_lib

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseEntity


class Household(BaseEntity):
    """A workspace / family unit (tenant scope)."""

    __tablename__ = "household"


class AppUser(BaseEntity):
    """Application user; uuid equals the Keycloak subject (sub)."""

    __tablename__ = "app_user"

    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    default_household_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("household.uuid"), nullable=True
    )
    base_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)


class Role(BaseEntity):
    """RBAC role (seeded: Owner, Editor, Viewer)."""

    __tablename__ = "role"


class UserRole(BaseEntity):
    """Grant of a role to a user within a household."""

    __tablename__ = "user_role"

    user_id: Mapped[uuid_lib.UUID] = mapped_column(ForeignKey("app_user.uuid"), nullable=False)
    role_id: Mapped[uuid_lib.UUID] = mapped_column(ForeignKey("role.uuid"), nullable=False)
    grant_household_id: Mapped[uuid_lib.UUID] = mapped_column(
        ForeignKey("household.uuid"), nullable=False
    )