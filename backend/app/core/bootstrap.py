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


# Advisory-lock key so the API and worker containers don't run migrations/seeding
# concurrently on startup (which caused duplicate-key races and a backend exit 3).
_INIT_LOCK_KEY = 776_2011


def init_db() -> None:
    # Serialize startup init across containers (API + worker) with a Postgres
    # advisory lock held on a single dedicated connection for the whole routine.
    lock_conn = engine.connect()
    try:
        lock_conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{settings.db_schema}"'))
        lock_conn.execute(text("SELECT pg_advisory_lock(:k)"), {"k": _INIT_LOCK_KEY})
        lock_conn.commit()

        if not _run_migrations():
            Base.metadata.create_all(bind=engine)

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
