"""Credentials Store models (Session 815, Item 19).

A category-driven, dynamic credential store:
  - `credential_category` defines a **parameter schema** (an ordered list of
    parameter specs) for a class of credentials (e.g. "Email"). Each parameter
    has a `key`, `label`, `type` (string|number|password|enum|bool), an optional
    fixed value set (`options`) for `enum`, a `required` flag, and a `sensitive`
    flag (rendered masked, never returned in clear).
  - `credential` is a named value-set for a category. Its `values` JSONB holds
    the entered parameters; sensitive parameter values are masked on read.

`credentials_ref` fields elsewhere (LLM providers, integration endpoints, email)
store a `credential.mnemonic_id` (or uuid) pointing here.
"""

import uuid as uuid_lib

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseEntity


class CredentialCategory(BaseEntity):
    """Defines the parameter schema for a class of credentials.

    `params` is a JSON list of specs, each like:
      {"key": "host", "label": "Host", "type": "string", "required": true,
       "sensitive": false}
      {"key": "security", "label": "Security", "type": "enum",
       "options": ["none", "starttls", "ssl"], "required": true}
      {"key": "password", "label": "Password", "type": "password",
       "sensitive": true}
    """

    __tablename__ = "credential_category"

    category_key: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    params: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    is_system: Mapped[bool] = mapped_column(default=False, nullable=False)

    credentials: Mapped[list["Credential"]] = relationship(
        back_populates="category", cascade="all, delete-orphan"
    )


class Credential(BaseEntity):
    """A named set of values for a credential category. Sensitive values are
    stored in `values` but masked when read back through the API."""

    __tablename__ = "credential"

    category_id: Mapped[uuid_lib.UUID] = mapped_column(
        ForeignKey("credential_category.uuid"), nullable=False, index=True
    )
    values: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    category: Mapped["CredentialCategory"] = relationship(back_populates="credentials")