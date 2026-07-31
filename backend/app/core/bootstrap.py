"""Startup bootstrap: run migrations (or create tables) and seed system data.

Prefers Alembic migrations (`upgrade head`), which also install extensions and
the currency_rate GiST no-overlap constraint. Falls back to metadata create_all
if Alembic is unavailable. Seeding is idempotent.
"""

import os

from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
import app.models  # noqa: F401  (register all tables)
from app.services.seeder import seed_all

settings = get_settings()


def _run_migrations() -> bool:
    """Run `alembic upgrade head`. Returns True on success."""
    try:
        from alembic import command
        from alembic.config import Config

        here = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # backend/
        cfg = Config(os.path.join(here, "alembic.ini"))
        cfg.set_main_option("script_location", os.path.join(here, "alembic"))
        cfg.set_main_option("sqlalchemy.url", settings.database_url)
        command.upgrade(cfg, "head")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[bootstrap] Alembic upgrade failed ({exc}); falling back to create_all.", flush=True)
        return False


# Additive, idempotent column additions for evolving models. `create_all` and the
# initial migration create *tables* but never alter existing ones, so new nullable
# columns are added here so both fresh and existing databases converge (Phase 11).
_ADDITIVE_COLUMNS: list[tuple[str, str, str]] = [
    # (table, column, type/definition)
    ("partner", "country_id", "UUID"),
    ("loan", "loan_category_cv_id", "UUID"),
    # app_user display-format preferences + name (Phase 11 Batch 3, A.7 / profile).
    ("app_user", "name", "VARCHAR(160)"),
    ("app_user", "date_format", "VARCHAR(40)"),
    ("app_user", "number_format", "VARCHAR(40)"),
    ("app_user", "time_format", "VARCHAR(40)"),
    # app_user ↔ Keycloak subject link (Session 742, Bug 1).
    ("app_user", "keycloak_subject", "VARCHAR(64)"),
    # Session 815: time locale + high-precision decimals + username mirror.
    ("app_user", "time_locale", "VARCHAR(20)"),
    ("app_user", "amount_decimals", "INTEGER"),
    ("app_user", "username", "VARCHAR(160)"),
    # holiday_calendar weekend/week-start config (Phase 11 Batch 3, A.1).
    ("holiday_calendar", "weekend_days", "JSONB"),
    ("holiday_calendar", "week_start", "SMALLINT"),
    # Goals ↔ transactions (Session 742, Bug 19).
    ("goal", "goal_type_cv_id", "UUID"),
    ("goal", "expense_category_id", "UUID"),
    ("goal", "period", "VARCHAR(20)"),
    ("goal", "limit_amount", "NUMERIC(18,4)"),
    ("transaction", "goal_id", "UUID"),
    # Account bank/identifier numbers (Session 815, Item 14). Variable length,
    # numeric+dashes (IBAN alphanumeric); credit-card number for card accounts.
    ("account", "iban", "VARCHAR(40)"),
    ("account", "card_number", "VARCHAR(40)"),
    ("account", "bank_sort_code", "VARCHAR(20)"),
    ("account", "bank_account_number", "VARCHAR(40)"),
    ("account", "building_society_number", "VARCHAR(40)"),
    ("account", "routing_number", "VARCHAR(20)"),
    ("account", "other_bank_numbers", "JSONB"),
]

# Idempotent column alterations (not just additions) for evolving models.
_ALTER_STATEMENTS: list[str] = [
    # user_role.grant_household_id must be nullable so role grants work in the
    # single-user model (no household required) — Session 742, Bug 2.
    'ALTER TABLE "{schema}"."user_role" ALTER COLUMN "grant_household_id" DROP NOT NULL',
    # Session 815, Item 21: backfill NULL hierarchy levels to 1 so the
    # beneficiary/expense-category list & tree don't fail response validation
    # (older/seeded rows created before the derive-level hook had level = NULL).
    'UPDATE "{schema}"."beneficiary" SET "level" = 1 WHERE "level" IS NULL',
    'UPDATE "{schema}"."expense_category" SET "level" = 1 WHERE "level" IS NULL',
    # Batch 12: clean up stray "dev" users auto-created by the old profile
    # auto-provision (guest fallback). Soft-delete any app_user named/usernamed
    # "dev" that has no Keycloak subject link (never a real account).
    'UPDATE "{schema}"."app_user" SET "deleted_at" = now() '
    'WHERE "deleted_at" IS NULL AND "keycloak_subject" IS NULL '
    "AND (lower(\"name\") = 'dev' OR lower(coalesce(\"username\",'')) = 'dev')",
]


def _apply_additive_columns() -> None:
    schema = settings.db_schema
    with engine.begin() as conn:
        for table, column, coltype in _ADDITIVE_COLUMNS:
            conn.execute(
                text(
                    f'ALTER TABLE "{schema}"."{table}" '
                    f'ADD COLUMN IF NOT EXISTS "{column}" {coltype}'
                )
            )
        for stmt in _ALTER_STATEMENTS:
            try:
                conn.execute(text(stmt.format(schema=schema)))
            except Exception as exc:  # noqa: BLE001
                print(f"[bootstrap] alter skipped ({stmt}): {exc}", flush=True)


# Advisory-lock key so the API and worker containers don't run migrations/seeding
# concurrently on startup (which caused duplicate-key races and a backend exit 3).
_INIT_LOCK_KEY = 776_2011


def _try_advisory_lock(conn, *, attempts: int = 30, delay: float = 1.0) -> bool:
    """Acquire the init advisory lock **without blocking forever**.

    The original code used the blocking `pg_advisory_lock`, which deadlocks
    startup if a previous (wedged) process or the worker still holds the lock —
    under `uvicorn --reload` this left the backend stuck on "Waiting for
    application startup" and every request 502'd (Session 815, Batch 7 follow-up).
    We now poll `pg_try_advisory_lock` for a bounded time, then proceed anyway
    (all init steps are idempotent, so worst case two processes race harmlessly).
    """
    import time

    for _ in range(max(1, attempts)):
        got = conn.execute(
            text("SELECT pg_try_advisory_lock(:k)"), {"k": _INIT_LOCK_KEY}
        ).scalar()
        conn.commit()
        if got:
            return True
        time.sleep(delay)
    print(
        "[bootstrap] init advisory lock busy; proceeding without it "
        "(init is idempotent).",
        flush=True,
    )
    return False


def init_db() -> None:
    # Serialize startup init across containers (API + worker) with a Postgres
    # advisory lock held on a single dedicated connection for the whole routine.
    # NB: non-blocking acquisition (bounded retry) so a stale lock can't wedge
    # startup — see _try_advisory_lock.
    lock_conn = engine.connect()
    have_lock = False
    try:
        lock_conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{settings.db_schema}"'))
        lock_conn.commit()
        have_lock = _try_advisory_lock(lock_conn)

        # Run migrations if available. IMPORTANT: also run create_all
        # unconditionally afterwards. `alembic upgrade head` is a no-op on a DB
        # already stamped at head, so **new tables added to the models after the
        # initial migration are never created** by migrations alone (this caused
        # the startup crash where `credential_category` didn't exist and seeding
        # raised UndefinedTable → lifespan startup failed → app never served).
        # `create_all` only CREATES missing tables (never drops/alters), so it's
        # safe to run every time and converges existing DBs (Session 815 fix).
        _run_migrations()
        try:
            Base.metadata.create_all(bind=engine)
        except Exception as exc:  # noqa: BLE001
            print(f"[bootstrap] create_all skipped: {exc}", flush=True)

        # Converge additive schema changes on existing databases.
        try:
            _apply_additive_columns()
        except Exception as exc:  # noqa: BLE001
            print(f"[bootstrap] additive column sync skipped: {exc}", flush=True)

        # Seed system reference data (idempotent).
        db = SessionLocal()
        try:
            seed_all(db)
        finally:
            db.close()
    finally:
        try:
            lock_conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": _INIT_LOCK_KEY})
            lock_conn.commit()
        except Exception:  # noqa: BLE001
            pass
        lock_conn.close()
