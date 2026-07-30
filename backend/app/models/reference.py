"""Reference data: currency, country, institution (Decision #28)."""

import uuid as uuid_lib

from sqlalchemy import ForeignKey, SmallInteger, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseEntity


class Currency(Base):
    """ISO 4217 currency. PK is the 3-letter code."""

    __tablename__ = "currency"

    code: Mapped[str] = mapped_column(String(3), primary_key=True)
    symbol: Mapped[str | None] = mapped_column(String(8), nullable=True)
    decimals: Mapped[int] = mapped_column(SmallInteger, default=2, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)


class Country(BaseEntity):
    """Configurable ISO 3166 country reference entity."""

    __tablename__ = "country"

    iso2: Mapped[str] = mapped_column(String(2), unique=True, nullable=False, index=True)
    iso3: Mapped[str] = mapped_column(String(3), unique=True, nullable=False, index=True)
    default_currency: Mapped[str | None] = mapped_column(
        ForeignKey("currency.code"), nullable=True
    )


class Institution(BaseEntity):
    """Configurable financial institution (bank/broker/issuer) with a country."""

    __tablename__ = "institution"

    country_id: Mapped[uuid_lib.UUID] = mapped_column(
        ForeignKey("country.uuid"), nullable=False, index=True
    )
    institution_type_cv_id: Mapped[uuid_lib.UUID | None] = mapped_column(
        ForeignKey("code_value.uuid"), nullable=True
    )
    swift_bic: Mapped[str | None] = mapped_column(String(11), nullable=True)
    website: Mapped[str | None] = mapped_column(String(300), nullable=True)

    country: Mapped["Country"] = relationship()