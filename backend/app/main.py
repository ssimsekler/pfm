"""PFM FastAPI application entrypoint.

Phase 1: DB bootstrap + seeding on startup, value-help router, readiness check.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app import __version__
from app.api.value_help import router as value_help_router
from app.core.bootstrap import init_db
from app.core.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create schema/tables and seed system data on startup.
    init_db()
    yield


app = FastAPI(
    title="PFM API",
    version=__version__,
    description="Personal Finance Management API. See docs/PLAN.md for scope.",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    root_path="",
    lifespan=lifespan,
)

app.include_router(value_help_router)


@app.get("/api/health", tags=["system"])
def health() -> dict:
    """Liveness probe."""
    return {"status": "ok", "version": __version__}


@app.get("/api/ready", tags=["system"])
def ready() -> dict:
    """Readiness probe — verifies DB connectivity."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ready", "db": "ok"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "degraded", "db": f"error: {exc}"}
