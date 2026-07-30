"""Initial schema: create all tables + extensions + FX no-overlap constraint.

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-30
"""
from typing import Sequence, Union

from alembic import op

from app.core.database import Base
import app.models  # noqa: F401  (register all tables on Base.metadata)

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "pfm"


def upgrade() -> None:
    bind = op.get_bind()

    # Required extensions (trigram search, GiST exclusion for FX validity).
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    # Create every mapped table.
    Base.metadata.create_all(bind=bind)

    # currency_rate: no overlapping validity periods per (base_ccy, quote_ccy).
    op.execute(
        f"""
        ALTER TABLE {SCHEMA}.currency_rate
        ADD CONSTRAINT ex_currency_rate_no_overlap
        EXCLUDE USING gist (
            base_ccy WITH =,
            quote_ccy WITH =,
            daterange(begin_date, end_date) WITH &&
        )
        WHERE (deleted_at IS NULL)
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    op.execute(f"ALTER TABLE {SCHEMA}.currency_rate DROP CONSTRAINT IF EXISTS ex_currency_rate_no_overlap")
    Base.metadata.drop_all(bind=bind)