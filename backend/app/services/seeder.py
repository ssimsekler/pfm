"""Idempotent seeding of system reference data (runs at startup)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.automation import IntegrationEndpoint, LlmProvider
from app.models.meta import AppConfig, CodeList, CodeValue
from app.models.reference import Country, Currency
from app.models.security import Role
from app.services import iso_data, seed_data
from app.services.id_sequence import next_mnemonic

_settings = get_settings()


def seed_all(db: Session) -> None:
    _seed_currencies(db)
    _seed_code_lists(db)
    _seed_countries(db)
    _seed_roles(db)
    _seed_app_config(db)
    _seed_ollama_provider(db)
    _seed_integration_endpoints(db)
    db.commit()


def _code_value(db: Session, list_key: str, code: str):
    cl = db.execute(select(CodeList).where(CodeList.list_key == list_key)).scalar_one_or_none()
    if cl is None:
        return None
    return db.execute(
        select(CodeValue).where(CodeValue.code_list_id == cl.uuid, CodeValue.code == code)
    ).scalar_one_or_none()


def _seed_ollama_provider(db: Session) -> None:
    """Seed a default local Ollama provider (Decision #24)."""
    existing = db.execute(
        select(LlmProvider).where(LlmProvider.name == "Local Ollama")
    ).scalar_one_or_none()
    if existing:
        return
    kind = _code_value(db, "llm_kind", "ollama")
    db.add(
        LlmProvider(
            mnemonic_id=next_mnemonic(db, "llm_provider"),
            name="Local Ollama",
            description="Bundled local LLM provider",
            kind_cv_id=kind.uuid if kind else None,
            base_url=_settings.ollama_base_url,
            model=_settings.ollama_default_model,
            enabled=True,
        )
    )
    db.flush()


def _seed_integration_endpoints(db: Session) -> None:
    """Seed default FX/stock/crypto endpoints (Decision #18)."""
    defaults = [
        ("FX_RATES", "Frankfurter", "https://api.frankfurter.app"),
        ("CRYPTO_QUOTE", "CoinGecko", "https://api.coingecko.com/api/v3"),
        ("STOCK_QUOTE", "Yahoo Finance", "https://query1.finance.yahoo.com"),
    ]
    for scenario_key, provider_name, base_url in defaults:
        existing = db.execute(
            select(IntegrationEndpoint).where(
                IntegrationEndpoint.scenario_key == scenario_key
            )
        ).scalar_one_or_none()
        if existing:
            continue
        none_auth = _code_value(db, "auth_type", "none")
        db.add(
            IntegrationEndpoint(
                mnemonic_id=next_mnemonic(db, "integration_endpoint"),
                name=f"{provider_name} ({scenario_key})",
                scenario_key=scenario_key,
                provider_name=provider_name,
                base_url=base_url,
                auth_type_cv_id=none_auth.uuid if none_auth else None,
                timeout_ms=8000,
                priority=1,
                enabled=True,
            )
        )
    db.flush()


def _seed_currencies(db: Session) -> None:
    existing = {c.code for c in db.execute(select(Currency)).scalars()}
    for code, symbol, decimals, name in iso_data.ISO_CURRENCIES:
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
    # Only reference currencies that were actually seeded, to avoid FK errors.
    known_ccy = {c.code for c in db.execute(select(Currency)).scalars()}
    for iso2, iso3, name, ccy in iso_data.ISO_COUNTRIES:
        if iso2 not in existing:
            if ccy is not None and ccy not in known_ccy:
                ccy = None
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