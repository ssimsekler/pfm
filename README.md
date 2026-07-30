# PFM — Personal Finance Management

A containerized, multi-user personal finance management application: accounts, transactions,
transfers, expense categories/items, recurrence, installments, loans, goals, investments,
budgeting, document imports (PDF/CSV/XLSX with LLM-assisted mapping), multi-currency,
analytics/reporting, notifications, data export, and configurable integrations.

> **Status:** Phases 0–9 complete (backend + Fiori frontend, tests, docs). See
> [`docs/PROGRESS.md`](docs/PROGRESS.md).

## Documentation

- [`docs/PLAN.md`](docs/PLAN.md) — master plan (stack, scope, phases).
- [`docs/ERD.md`](docs/ERD.md) — field-level data model.
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — architecture decision log (ADRs).
- [`docs/PROGRESS.md`](docs/PROGRESS.md) — build progress / resume file.

## Tech stack

| Layer | Choice |
|---|---|
| Backend | Python + FastAPI (OpenAPI-native) |
| ORM/Migrations | SQLAlchemy + Alembic |
| DB | PostgreSQL (pg_trgm + btree_gist) |
| Frontend | React + Vite + `@ui5/webcomponents-react` (SAP Fiori) |
| Auth | Keycloak (OIDC), RBAC (Owner/Editor/Viewer) |
| Object storage | MinIO (S3-compatible) |
| Events | Transactional outbox (CloudEvents 1.0) |
| Local LLM | Ollama (default configurable provider) |
| Proxy | Traefik |

## Repository layout

```
/backend      FastAPI app + services + worker (scheduler, jobs, outbox publisher) + tests
/frontend     React + UI5 Web Components (Vite)
/infra        docker-compose, Traefik, Keycloak realm, MinIO/Postgres init
/docs         plan, ERD, decisions, progress
```

## Quick start (development)

> Requires Docker + Docker Compose.

```bash
cp infra/.env.example infra/.env    # then edit secrets
cd infra
docker compose up -d --build
```

Services (via Traefik on http://localhost):
- Frontend SPA: `/`
- Backend API + docs: `/api`, `/api/docs`
- Keycloak: `/auth`
- **pgAdmin** (PostgreSQL admin GUI): `/pgadmin`
- **Adminer** (lightweight DB GUI): `:8081` (server `db`)
- MinIO console (object-store admin GUI): `:9001`
- Ollama (local LLM): `:11434`

> DB admin GUIs are **dev utilities**. Connect them to Postgres with host `db`, port `5432`,
> and the `POSTGRES_USER`/`POSTGRES_PASSWORD` from your `.env`.

Pull a local model after first start (used by the LLM Gateway as a default provider):

```bash
docker compose exec ollama ollama pull llama3.2
```

## Verify the running stack

- Health/readiness: `GET http://localhost/api/health`, `GET http://localhost/api/ready`.
- OpenAPI: `GET http://localhost/api/openapi.json` (interactive docs at `/api/docs`).
- Value help: `GET http://localhost/api/v1/code-lists`.
- Try: `/api/v1/accounts`, `/api/v1/transactions?date_from=2025-01-01`,
  `/api/v1/fx/convert?amount=100&from_ccy=AED&to_ccy=USD`,
  `/api/v1/reports/cash-position`, `/api/v1/reports/net-worth`.
- Export: `GET http://localhost/api/v1/export/xlsx` (single workbook) or the **Export** screen.

## Feature highlights

- **Configurable code lists** drive every enumerated value (value help + validation).
- **Multi-currency** with validity-period FX rates; **USD** reporting roll-ups.
- **Recurrence engine** (business-day rules + holiday calendars); installments, loans (amortization), goals.
- **Import pipeline**: parse PDF/CSV/XLSX → rule/LLM-assisted mapping → validation screen → commit (dedup + filename note).
- **Budgets** + variance + recommendations; prebuilt **reports** + charts + guarded read-only **SQL console**.
- **Notifications** (in-app + optional SMTP) and a **scheduler** worker (outbox publisher, due reminders).
- **Full data export** to XLSX (single multi-tab workbook or per-entity files).
- **RBAC** (Keycloak), **audit trail**, **CloudEvents** outbox, **soft delete**.

## Tests

Backend unit tests (pure logic: id-sequence, FX lookup, recurrence, schedules, rules, import
parsing/dedup, SQL-console guard) run with pytest inside the backend image:

```bash
cd infra
docker compose run --rm backend sh -c "pip install -r requirements-dev.txt && pytest"
```

## Development phases

See [`docs/PLAN.md`](docs/PLAN.md) §8. Each phase ended in a runnable, committed increment.

## License

See [LICENSE](LICENSE).