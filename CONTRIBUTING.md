# Contributing to PFM

Thanks for contributing! This project keeps its **docs and code in lockstep**. Please follow
the workflow below — it applies to human contributors and AI-assisted changes alike, and is
enforced repo-wide via [`.clinerules/docs-continuity.md`](.clinerules/docs-continuity.md)
(auto-loaded by Cline every session).

## Documentation-continuity rule (mandatory)

**Before making any change**, read — in this order — to reload context:

1. [`docs/PROGRESS.md`](docs/PROGRESS.md) — current phase, what's done, exact next step.
2. [`docs/PLAN.md`](docs/PLAN.md) — scope and phases.
3. [`docs/DECISIONS.md`](docs/DECISIONS.md) — architecture decision records (ADRs).
4. [`docs/ERD.md`](docs/ERD.md) — field-level data model.

**With every change**, update the affected docs in the **same** increment:

- **`docs/PROGRESS.md`** — update "Current status", "Next step", and the phase checklist.
- **`docs/DECISIONS.md`** — add a new numbered ADR for any new architectural/cross-cutting
  decision (keep incrementing ADR numbers).
- **`docs/ERD.md`** — reflect any data-model change (tables/columns/constraints) and any new
  persistence-affecting endpoints.
- **`docs/PLAN.md`** — reflect any scope/phase change.

**Definition of done:** a change is complete only when **code and docs are updated together**.

**Commit & push after every pass (mandatory):** after each pass of changes, stage everything,
commit with a clear message, and `git push` to the remote. If the push fails (no network or
credentials), keep committing locally and retry the push next time (ADR #22).

## Development

See [`README.md`](README.md) for the quick start:

```bash
cp infra/.env.example infra/.env
cd infra
docker compose up -d --build
```

- Backend: Python + FastAPI (`/backend`). Tests run inside the backend image:
  `docker compose run --rm backend sh -c "pip install -r requirements-dev.txt && pytest"`.
- Frontend: React + Vite + UI5 Web Components v1 (`/frontend`). Rebuild after changes:
  `docker compose up -d --build frontend`.

## Conventions

- Prefer **configurable / metadata-driven** solutions consistent with existing ADRs
  (e.g. code lists for enums, the `entities.js`-driven CRUD layer).
- Every **state-changing** UI action requires an explicit confirmation dialog (ADR #32).
- Financial deletes are **soft** (recoverable); keep it that way.
- Keep `docs/PROGRESS.md` accurate enough that a fresh session can resume from it alone.