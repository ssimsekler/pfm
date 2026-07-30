"""PFM FastAPI application entrypoint.

Phase 0: minimal app with health/readiness endpoints so the container stack
is verifiable end-to-end. Routers, auth, DB, and CRUD are added in Phase 1+.
"""

from fastapi import FastAPI

from app import __version__

app = FastAPI(
    title="PFM API",
    version=__version__,
    description="Personal Finance Management API. See docs/PLAN.md for scope.",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    root_path="",
)


@app.get("/api/health", tags=["system"])
def health() -> dict:
    """Liveness probe."""
    return {"status": "ok", "version": __version__}


@app.get("/api/ready", tags=["system"])
def ready() -> dict:
    """Readiness probe. Extended in Phase 1 to check DB connectivity."""
    return {"status": "ready"}