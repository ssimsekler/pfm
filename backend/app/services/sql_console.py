"""Guarded read-only SQL console (Decision #10 / spec 6.2).

Runs a single SELECT via a read-only transaction with a statement timeout and a
forced row LIMIT. Blocks DDL/DML and multiple statements. Intended for power-user
reporting against the app schema / reporting views only.
"""

import re

from sqlalchemy import create_engine, text

from app.core.config import get_settings

settings = get_settings()

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|"
    r"copy|call|do|merge|vacuum|comment|reindex|cluster)\b",
    re.IGNORECASE,
)


def _readonly_url() -> str:
    """DSN for the SQL console. For v1 reuse the app URL and enforce read-only
    at the transaction level (a dedicated pfm_readonly role exists in infra)."""
    return settings.database_url


def run_query(sql: str) -> dict:
    stripped = sql.strip().rstrip(";")
    if ";" in stripped:
        raise ValueError("Only a single statement is allowed.")
    if not stripped.lower().startswith(("select", "with")):
        raise ValueError("Only SELECT/WITH queries are allowed.")
    if _FORBIDDEN.search(stripped):
        raise ValueError("Only read-only SELECT queries are permitted.")

    limit = settings.sql_console_row_limit
    timeout_ms = settings.sql_console_timeout_ms
    wrapped = f"SELECT * FROM ({stripped}) AS _q LIMIT {limit}"

    engine = create_engine(_readonly_url(), pool_pre_ping=True, future=True)
    with engine.connect() as conn:
        conn.execute(text("SET TRANSACTION READ ONLY"))
        conn.execute(text(f"SET LOCAL statement_timeout = {int(timeout_ms)}"))
        result = conn.execute(text(wrapped))
        columns = list(result.keys())
        rows = [list(r) for r in result.fetchall()]
    return {
        "columns": columns,
        "rows": [[_json_safe(v) for v in row] for row in rows],
        "row_count": len(rows),
        "truncated": len(rows) >= limit,
    }


def _json_safe(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)