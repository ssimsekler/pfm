# PFM Build Progress (Resume File)

> **On restart, read this file FIRST.** Then `docs/PLAN.md` and `docs/DECISIONS.md`.
> This file records the current phase, what is done, and the exact next step.

## Current status

- **Active phase:** Phase 1 — Data & platform core (IN PROGRESS)
- **Last completed (Phase 1 so far):** app config (`core/config.py`), DB session + declarative
  base bound to `pfm` schema (`core/database.py`), base entity mixin (`models/base.py`),
  meta models (app_config, id_sequence, code_list, code_value, event_outbox, audit_log),
  security models (household, app_user, role, user_role), reference models (currency, country,
  institution), id-sequence service, events (CloudEvents outbox) + audit services, seed data
  (23 code lists, currencies, countries, roles, app_config), idempotent seeder, Alembic scaffold
  (alembic.ini + env.py schema-aware), startup bootstrap (create schema/tables + seed),
  value-help API (`/api/v1/code-lists`, `/api/v1/code-lists/{list_key}/values`), DB-backed
  readiness probe. All 20 backend files pass syntax check.
- **Next step (Phase 1 remaining):** Keycloak OIDC auth middleware + RBAC dependency;
  generic CRUD/repository base with search/filter/sort/pagination; wire seeded default
  Ollama `llm_provider`. Then generate the first real Alembic migration to replace
  create_all. Then proceed to Phase 2 (core financial entities).
- **Verify:** `cd infra && cp .env.example .env && docker compose up -d --build`, then
  `GET http://localhost/api/ready` (db ok) and `GET http://localhost/api/v1/code-lists`.

## How to resume

1. Read this file, `PLAN.md`, `DECISIONS.md`.
2. Check `git log --oneline` to see the last committed increment.
3. Continue from "Next step" above / the first unchecked phase task below.
4. At the end of each phase: update this file, commit, attempt push.

## Phase checklist

- [x] **Phase 0 — Foundation**
  - [x] docs/PLAN.md
  - [x] docs/DECISIONS.md
  - [x] docs/PROGRESS.md
  - [x] docs/ERD.md (field-level data model)
  - [x] Repo scaffold (`/backend`, `/frontend`, `/infra`, `/docs`)
  - [x] `infra/docker-compose.yml` + `.env.example` (proxy, frontend, backend, worker, db, objectstore, keycloak)
  - [x] Postgres init (schemas + read-only role), Keycloak realm import
  - [x] Minimal FastAPI health app + worker placeholder
  - [x] React + Vite + UI5 Web Components scaffold
  - [x] `.gitignore`, `README.md`, `LICENSE`, `.dockerignore` files
  - [x] git init, first commit, attempt push to remote
  - [ ] PAUSE for user review
- [ ] **Phase 1 — Data & platform core** (models, migrations, base mixin, id-sequence, outbox+audit, Keycloak/RBAC, code_list/code_value + seed system code lists, value-help endpoints)
- [ ] **Phase 2 — Core financial APIs** (accounts, transactions, categories, cash_flow_items, partners, beneficiaries, currencies/rates, transfers, splits, tags, attachments, FX lookup)
- [ ] **Phase 3 — Recurrence, installments, loans, goals, income**
- [ ] **Phase 4 — Integrations & automation** (connector framework, FX/stock/crypto, LLM Gateway, rules engine, valuation refresh)
- [ ] **Phase 5 — Import pipeline** (pdf/csv/xlsx → mapping → preview → commit, dedup, filename note)
- [ ] **Phase 6 — Budgeting & reporting** (budgets, recommendations, variance, prebuilt reports, charts, SQL console)
- [ ] **Phase 7 — Notifications & scheduler**
- [ ] **Phase 8 — Frontend polish & UX**
- [ ] **Phase 9 — Quality & delivery** (tests, OpenAPI export, seed data, README, release)

## Notes / open items

- Remote: `https://github.com/ssimsekler/pfm.git`. If push fails (auth/network), keep committing locally.
- Confirmation dialogs (T.9) are UI-only.
- Each phase must end in a runnable, committed increment.
- All enumerated value sets are `code_value` FK columns (`*_cv_id`) driven by `code_list` (Decision #23); Phase 1 seeds the system lists and exposes a value-help endpoint.
- Ollama runs as a local LLM container (Decision #24); Phase 1/4 seeds a default `llm_provider` (kind=ollama, `OLLAMA_BASE_URL`/`OLLAMA_DEFAULT_MODEL`). Pull a model with `docker compose exec ollama ollama pull llama3.2`.
- Search/filter/sort/pagination on all list endpoints & screens (Decision #25) — build in Phase 2 (financial entities) and reuse the pattern everywhere.
- `currency_rate` uses validity periods `begin_date`/`end_date` with GiST exclusion; FX lookup `begin_date <= date < end_date` (Decision #26) — Phase 2 FX service.
- Reporting currency default **USD** (`APP_REPORTING_CURRENCY`), transactions native (mostly AED via `APP_DEFAULT_TXN_CURRENCY`); seed `app_config.default_base_currency=USD` (Decision #27). Imports always land on validation screen (Phase 5).
- `country` and `institution` are configurable entities; `account.institution_id` FK; `institution_type` code list (Decision #28). Phase 1 creates tables + seeds ISO countries; Phase 2 wires account→institution value help.
