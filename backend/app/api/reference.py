"""Reference-data endpoints: country, institution, currency (Phase 2 wrap-up)."""

import uuid as uuid_lib

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.crud_router import build_crud_router
from app.api.schemas import EntityOut, ORMModel
from app.core.database import get_db
from app.core.security import Principal, get_current_principal
from app.models import reference as ref

# ---------------------------------------------------------------------------
# Country (configurable ISO entity)
# ---------------------------------------------------------------------------
class CountryOut(EntityOut):
    iso2: str
    iso3: str
    default_currency: str | None = None


class CountryCreate(ORMModel):
    name: str
    description: str | None = None
    iso2: str
    iso3: str
    default_currency: str | None = None


class CountryUpdate(ORMModel):
    name: str | None = None
    description: str | None = None
    iso2: str | None = None
    iso3: str | None = None
    default_currency: str | None = None


country_router = build_crud_router(
    prefix="/api/v1/countries", tag="countries", model=ref.Country,
    entity_type="country", event_domain="country",
    out_schema=CountryOut, create_schema=CountryCreate, update_schema=CountryUpdate,
    search_columns=["iso2", "iso3"],
)


# ---------------------------------------------------------------------------
# Institution (configurable, with country)
# ---------------------------------------------------------------------------
class InstitutionOut(EntityOut):
    country_id: uuid_lib.UUID
    institution_type_cv_id: uuid_lib.UUID | None = None
    swift_bic: str | None = None
    website: str | None = None


class InstitutionCreate(ORMModel):
    name: str
    description: str | None = None
    country_id: uuid_lib.UUID
    institution_type_cv_id: uuid_lib.UUID | None = None
    swift_bic: str | None = None
    website: str | None = None


class InstitutionUpdate(ORMModel):
    name: str | None = None
    description: str | None = None
    country_id: uuid_lib.UUID | None = None
    institution_type_cv_id: uuid_lib.UUID | None = None
    swift_bic: str | None = None
    website: str | None = None


institution_router = build_crud_router(
    prefix="/api/v1/institutions", tag="institutions", model=ref.Institution,
    entity_type="institution", event_domain="institution",
    out_schema=InstitutionOut, create_schema=InstitutionCreate,
    update_schema=InstitutionUpdate, search_columns=["swift_bic"],
)


# ---------------------------------------------------------------------------
# Currency (read-only list; PK is code, not a BaseEntity)
# ---------------------------------------------------------------------------
currency_router = APIRouter(prefix="/api/v1/currencies", tags=["currencies"])


class CurrencyOut(ORMModel):
    code: str
    symbol: str | None = None
    decimals: int
    name: str


@currency_router.get("", response_model=list[CurrencyOut])
def list_currencies(
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
):
    return list(db.execute(select(ref.Currency).order_by(ref.Currency.code)).scalars())


ALL_ROUTERS = [country_router, institution_router, currency_router]