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


def init_db() -> None:
    # Ensure the app schema exists first (migrations/create_all target it).
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{settings.db_schema}"'))

    if not _run_migrations():
        Base.metadata.create_all(bind=engine)

    # Seed system reference data (idempotent).
    db = SessionLocal()
    try:
        seed_all(db)
    finally:
        db.close()
