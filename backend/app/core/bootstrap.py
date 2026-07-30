"""Startup bootstrap: ensure schema/tables exist and seed system data.

For v1 we create tables via SQLAlchemy metadata (Alembic is scaffolded for
future incremental migrations). Seeding is idempotent.
"""

from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
import app.models  # noqa: F401  (register all tables)
from app.services.seeder import seed_all

settings = get_settings()


def init_db() -> None:
    # Ensure the app schema exists, then create tables.
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{settings.db_schema}"'))
    Base.metadata.create_all(bind=engine)

    # Seed system reference data.
    db = SessionLocal()
    try:
        seed_all(db)
    finally:
        db.close()