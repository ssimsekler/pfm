# PFM — Personal Finance Management

A containerized, multi-user personal finance management application: accounts, transactions,
transfers, expense categories/items, recurrence, installments, loans, goals, investments,
budgeting, document imports (PDF/CSV/XLSX with LLM-assisted mapping), multi-currency,
analytics/reporting, notifications, and configurable integrations.

> **Status:** Phase 0 (Foundation). See [`docs/PROGRESS.md`](docs/PROGRESS.md) for current state.

## Documentation

- [`docs/PLAN.md`](docs/PLAN.md) — master plan (stack, scope, phases).
- [`docs/ERD.md`](docs/ERD.md) — field-level data model.
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — architecture decision log.
- [`docs/PROGRESS.md`](docs/PROGRESS.md) — build progress / resume file.

## Tech stack

| Layer | Choice |
|---|---|
| Backend | Python + FastAPI (OpenAPI-native) |
| ORM/Migrations | SQLAlchemy + Alembic |
| DB | PostgreSQL |
| Frontend | React + Vite + `@ui5/webcomponents-react` (SAP Fiori) |
| Auth | Keycloak (OIDC) |
| Object storage | MinIO (S3-compatible) |
| Events | Transactional outbox (CloudEvents 1.0) |
| Local LLM | Ollama (default configurable provider) |
| Proxy | Traefik |

## Repository layout

```
/backend      FastAPI app + services + worker (scheduler, jobs, outbox publisher)
/frontend     React + UI5 Web Components (Vite)
/infra        docker-compose, Traefik, Keycloak realm, MinIO init
/docs         plan, ERD, decisions, progress, OpenAPI export
```

## Quick start (development)

> Requires Docker + Docker Compose.

```bash
cp infra/.env.example infra/.env    # then edit secrets
cd infra
docker compose up -d
```

Services (via Traefik on http://localhost):
- Frontend SPA: `/`
- Backend API + docs: `/api`, `/api/docs`
- Keycloak: `/auth`
- MinIO console: `:9001`
- Ollama (local LLM): `:11434`

Pull a local model after first start (used by the LLM Gateway as a default provider):

```bash
docker compose exec ollama ollama pull llama3.2
```

## Development phases

See [`docs/PLAN.md`](docs/PLAN.md) §8. Each phase ends in a runnable, committed increment.

## License

See [LICENSE](LICENSE).