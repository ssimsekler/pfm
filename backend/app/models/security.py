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

    name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Keycloak subject (sub) — links the app_user to its Keycloak identity so the
    # profile row can be resolved/created for any signed-in user (Session 742, Bug 1).
    keycloak_subject: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    default_household_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("household.uuid"), nullable=True
    )
    base_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    # Display-format preferences (Phase 11 Batch 3, A.7 / profile).
    date_format: Mapped[str | None] = mapped_column(String(40), nullable=True)
    number_format: Mapped[str | None] = mapped_column(String(40), nullable=True)
    time_format: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # Item 8: time locale (e.g. "en-GB"; blank → browser default).
    time_locale: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Item 5: decimals for high-precision amounts (FX rates / investment
    # quantities / unit prices). Everything else uses the number format (2 dp).
    amount_decimals: Mapped[int | None] = mapped_column(nullable=True)
    # Keycloak username mirror (Session 815, Item 11/12) — kept in sync at login/create.
    username: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)


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