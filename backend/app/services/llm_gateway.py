"""LLM Gateway (Session 742, New-2 — real gateway, supersedes the stray copy).

Central entry point for all LLM features. Iterates configured ``llm_provider``
rows **by ascending priority** (New-2 failover), skipping disabled/unhealthy
providers and falling through to the next on error/timeout. The whole subsystem
is gated by the ``llm.master_enabled`` app-config switch (Bug 6/7): when off,
``complete()`` returns ``None`` (callers must treat LLM output as optional).

Note: the categorization **rules engine** lives in ``app/services/rules.py``.
This module previously duplicated that engine by mistake; it is now the gateway.
"""

from __future__ import annotations

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.automation import LlmProvider
from app.models.meta import AppConfig, CodeValue

settings = get_settings()

# app_config key for the global kill-switch (standardized in Batch 4, Bug 6).
MASTER_KEY = "llm.master_enabled"


def is_enabled(db: Session) -> bool:
    """Master LLM switch: app_config[llm.master_enabled] OR settings default."""
    row = db.get(AppConfig, MASTER_KEY)
    if row is not None and row.value is not None:
        val = row.value
        if isinstance(val, bool):
            return val
        return str(val).strip().lower() in ("1", "true", "t", "yes", "y")
    return bool(settings.llm_master_enabled)


def _provider_priority(p: LlmProvider) -> int:
    """Ordering key: providers carry an optional numeric priority in `params`.

    We keep priority in `params.priority` (int, lower = tried first) so no schema
    change is needed; providers without it sort last.
    """
    try:
        return int((p.params or {}).get("priority", 1_000_000))
    except (TypeError, ValueError):
        return 1_000_000


def _ordered_providers(db: Session) -> list[LlmProvider]:
    rows = list(
        db.execute(
            select(LlmProvider).where(
                LlmProvider.enabled.is_(True),
                LlmProvider.deleted_at.is_(None),
            )
        ).scalars()
    )
    return sorted(rows, key=_provider_priority)


def _kind_code(db: Session, provider: LlmProvider) -> str:
    if provider.kind_cv_id is None:
        return "ollama"
    cv = db.get(CodeValue, provider.kind_cv_id)
    return (cv.code if cv else None) or "ollama"


def _call_provider(db: Session, provider: LlmProvider, prompt: str) -> str | None:
    """Attempt a single completion against one provider. Returns text or None.

    Only the local **Ollama** kind is implemented directly here; other kinds are
    left as graceful no-ops (return None) so the gateway falls through to the next
    provider. Extend per-kind as needed.
    """
    kind = _kind_code(db, provider)
    base = (provider.base_url or settings.ollama_base_url or "").rstrip("/")
    model = provider.model or settings.ollama_default_model

    try:
        if kind == "ollama":
            resp = httpx.post(
                f"{base}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=30.0,
            )
            if resp.status_code != 200:
                return None
            return (resp.json() or {}).get("response")
        # openai/azure/anthropic/custom: not wired without credentials — skip.
        return None
    except Exception:  # noqa: BLE001 — failover to the next provider
        return None


def complete(db: Session, feature_key: str, prompt: str) -> str | None:
    """Run a completion for a feature, trying providers by priority (New-2).

    Returns the first non-empty response, or None when LLM is disabled or every
    provider fails. Callers must treat the result as optional commentary.
    """
    if not is_enabled(db):
        return None
    for provider in _ordered_providers(db):
        text = _call_provider(db, provider, prompt)
        if text:
            return text
    return None