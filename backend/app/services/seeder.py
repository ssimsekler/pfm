"""Idempotent seeding of system reference data (runs at startup)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.meta import AppConfig, CodeList, CodeValue
from app.models.reference import Country, Currency
from app.models.security import Role
from app.services import seed_data
from app.services.id_sequence import next_mnemonic


def seed_all(db: Session) -> None:
    _seed_currencies(db)
    _seed_code_lists(db)
    _seed_countries(db)
    _seed_roles(db)
    _seed_app_config(db)
    db.commit()


def _seed_currencies(db: Session) -> None:
    existing = {c.code for c in db.execute(select(Currency)).scalars()}
    for code, symbol, decimals, name in seed_data.CURRENCIES:
        if code not in existing:
            db.add(Currency(code=code, symbol=symbol, decimals=decimals, name=name))
    db.flush()


def _seed_code_lists(db: Session) -> None:
    for list_key, values in seed_data.SYSTEM_CODE_LISTS.items():
        cl = db.execute(
            select(CodeList).where(CodeList.list_key == list_key)
        ).scalar_one_or_none()
        if cl is None:
            cl = CodeList(
                mnemonic_id=next_mnemonic(db, "code_list"),
                name=list_key,
                list_key=list_key,
                is_system=True,
                allow_user_values=True,
            )
            db.add(cl)
            db.flush()
        existing_codes = {
            v.code for v in db.execute(
                select(CodeValue).where(CodeValue.code_list_id == cl.uuid)
            ).scalars()
        }
        for order, (code, label, is_default) in enumerate(values):
            if code not in existing_codes:
                db.add(
                    CodeValue(
                        mnemonic_id=next_mnemonic(db, "code_value"),
                        name=label,
                        code_list_id=cl.uuid,
                        code=code,
                        label=label,
                        sort_order=order,
                        is_default=is_default,
                        is_active=True,
                    )
                )
    db.flush()


def _seed_countries(db: Session) -> None:
    existing = {c.iso2 for c in db.execute(select(Country)).scalars()}
    for iso2, iso3, name, ccy in seed_data.COUNTRIES:
        if iso2 not in existing:
            db.add(
                Country(
                    mnemonic_id=next_mnemonic(db, "country"),
                    name=name,
                    iso2=iso2,
                    iso3=iso3,
                    default_currency=ccy,
                )
            )
    db.flush()


def _seed_roles(db: Session) -> None:
    existing = {r.name for r in db.execute(select(Role)).scalars()}
    for name, desc in seed_data.ROLES:
        if name not in existing:
            db.add(Role(mnemonic_id=next_mnemonic(db, "role"), name=name, description=desc))
    db.flush()


def _seed_app_config(db: Session) -> None:
    existing = {c.key for c in db.execute(select(AppConfig)).scalars()}
    for key, value, value_type, desc in seed_data.APP_CONFIG:
        if key not in existing:
            db.add(
                AppConfig(key=key, value=value, value_type=value_type, description=desc)
            )
    db.flush()