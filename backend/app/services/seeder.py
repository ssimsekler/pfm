"""Idempotent seeding of system reference data (runs at startup)."""

import csv
import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.automation import IntegrationEndpoint, LlmProvider
from app.models.credentials import Credential, CredentialCategory
from app.models.financial import ExpenseCategory
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
    _seed_expense_categories(db)
    _seed_credentials(db)
    # Session 815, Batch 9: seed the Keycloak-independent local admin credential
    # (hashed) so there's always a login that works without Keycloak.
    try:
        from app.services import local_auth
        local_auth.ensure_seeded(db)
    except Exception as exc:  # noqa: BLE001
        print(f"[seeder] local admin seed skipped: {exc}", flush=True)
    db.commit()


# Email credential category parameter schema (Session 815, Item 19/20).
_EMAIL_CATEGORY_PARAMS = [
    {"key": "host", "label": "Host", "type": "string", "required": True,
     "placeholder": "smtp.mail.yahoo.com"},
    {"key": "port", "label": "Port", "type": "number", "required": True,
     "placeholder": "465 or 587"},
    {"key": "security", "label": "Security", "type": "enum",
     "options": ["none", "starttls", "ssl"], "required": True},
    {"key": "username", "label": "Username", "type": "string"},
    {"key": "password", "label": "Password / app-password", "type": "password",
     "sensitive": True},
    {"key": "from", "label": "From", "type": "string"},
    {"key": "recipient", "label": "Default recipient", "type": "string"},
]


def _seed_credentials(db: Session) -> None:
    """Seed the Email credential category and migrate any legacy `smtp.*`
    app_config keys into an Email credential (Session 815, Item 19/20).

    After migration the `smtp.*` keys are deleted (they leaked the password in
    clear text in the key/value list) and `email.enabled`/`email.credentials_ref`
    are set to point at the new credential.
    """
    email_cat = db.execute(
        select(CredentialCategory).where(CredentialCategory.category_key == "email")
    ).scalar_one_or_none()
    if email_cat is None:
        email_cat = CredentialCategory(
            mnemonic_id=next_mnemonic(db, "credential_category"),
            name="Email (SMTP)",
            category_key="email",
            params=_EMAIL_CATEGORY_PARAMS,
            is_system=True,
        )
        db.add(email_cat)
        db.flush()
    else:
        # Keep the param schema current.
        email_cat.params = _EMAIL_CATEGORY_PARAMS
        db.flush()

    # Migrate legacy smtp.* keys if present.
    smtp_keys = [
        "smtp.enabled", "smtp.host", "smtp.port", "smtp.security",
        "smtp.username", "smtp.password", "smtp.from", "smtp.to",
    ]
    rows = {k: db.get(AppConfig, k) for k in smtp_keys}
    if any(v is not None for v in rows.values()):
        def _val(k, default=None):
            r = rows.get(k)
            return r.value if (r is not None and r.value is not None) else default

        # Only create an Email credential if there's a host configured.
        host = _val("smtp.host")
        if host and not db.execute(
            select(Credential).where(Credential.category_id == email_cat.uuid)
        ).first():
            cred = Credential(
                mnemonic_id=next_mnemonic(db, "credential"),
                name="Email (migrated from SMTP settings)",
                category_id=email_cat.uuid,
                values={
                    "host": str(host),
                    "port": _val("smtp.port", 587),
                    "security": _val("smtp.security", "starttls"),
                    "username": _val("smtp.username", ""),
                    "password": _val("smtp.password", ""),
                    "from": _val("smtp.from", ""),
                    "recipient": _val("smtp.to", ""),
                },
            )
            db.add(cred)
            db.flush()
            ref = db.get(AppConfig, "email.credentials_ref")
            if ref is not None:
                ref.value = cred.mnemonic_id
            enabled = db.get(AppConfig, "email.enabled")
            if enabled is not None:
                enabled.value = bool(_val("smtp.enabled", False))

        # Remove the stray smtp.* keys (clear-text password leak).
        for r in rows.values():
            if r is not None:
                db.delete(r)
        db.flush()


def _seed_expense_categories(db: Session) -> None:
    """Seed a default expense-category hierarchy from a bundled CSV (#8, ADR #47).

    Idempotent: skips names that already exist. Parents are resolved by name;
    `level` is derived (parent.level + 1, else 1)."""
    # Only seed if there are no categories yet (don't fight user edits later).
    existing_any = db.execute(select(ExpenseCategory.uuid).limit(1)).first()
    if existing_any is not None:
        return
    path = os.path.join(os.path.dirname(__file__), "seed_expense_categories.csv")
    if not os.path.exists(path):
        return
    by_name: dict[str, ExpenseCategory] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    # Two passes so parents are created before children regardless of row order.
    def _create(name: str, parent_name: str | None) -> ExpenseCategory:
        parent = by_name.get(parent_name) if parent_name else None
        level = (parent.level + 1) if parent else 1
        cat = ExpenseCategory(
            mnemonic_id=next_mnemonic(db, "expense_category"),
            name=name,
            parent_id=parent.uuid if parent else None,
            level=level,
        )
        db.add(cat)
        db.flush()
        by_name[name] = cat
        return cat

    # Pass 1: roots (no parent).
    for r in rows:
        if not (r.get("parent") or "").strip():
            nm = (r.get("name") or "").strip()
            if nm and nm not in by_name:
                _create(nm, None)
    # Pass 2: children (may need multiple passes for deeper nesting).
    pending = [r for r in rows if (r.get("parent") or "").strip()]
    for _ in range(5):
        still: list[dict] = []
        for r in pending:
            nm = (r.get("name") or "").strip()
            pn = (r.get("parent") or "").strip()
            if not nm or nm in by_name:
                continue
            if pn in by_name:
                _create(nm, pn)
            else:
                still.append(r)
        pending = still
        if not pending:
            break
    db.flush()


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
    # Batch 10: migrate a legacy FX endpoint that pointed at frankfurter.app
    # (now 301-redirects and isn't er-api-shaped) to the reliable keyless
    # open.er-api.com base so refreshes work out of the box.
    fx = db.execute(
        select(IntegrationEndpoint).where(IntegrationEndpoint.scenario_key == "FX_RATES")
    ).scalar_one_or_none()
    if fx is not None and fx.base_url and "frankfurter" in fx.base_url:
        fx.base_url = "https://open.er-api.com/v6"
        fx.provider_name = "open.er-api.com"
        db.flush()

    defaults = [
        ("FX_RATES", "open.er-api.com", "https://open.er-api.com/v6"),
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
    # Session 815, Item 6: rename a legacy "Owner" role to "Admin" so existing
    # grants (user_role links) are preserved rather than orphaned.
    legacy = db.execute(select(Role).where(Role.name == "Owner")).scalar_one_or_none()
    if legacy is not None and db.execute(
        select(Role).where(Role.name == "Admin")
    ).scalar_one_or_none() is None:
        legacy.name = "Admin"
        legacy.description = "Full control incl. user administration"
        db.flush()
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

    # Session 742, Bug 6: consolidate the duplicate LLM switch. Older installs
    # created a stray `llm.enabled` (from the Settings UI) alongside the seeded
    # `llm.master_enabled`. Migrate the value across, then drop the stray key so
    # only one row remains.
    stray = db.get(AppConfig, "llm.enabled")
    if stray is not None:
        master = db.get(AppConfig, "llm.master_enabled")
        if master is not None and stray.value is not None:
            master.value = stray.value
        db.delete(stray)
        db.flush()
