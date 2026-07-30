# PFM Build Progress (Resume File)

> **On restart, read this file FIRST.** Then `docs/PLAN.md` and `docs/DECISIONS.md`.
> This file records the current phase, what is done, and the exact next step.

## Current status

- **Active phase:** Phase 7 — Notifications & scheduler (COMPLETE) → next: Phase 8
- **Last completed (Phase 7):** `notification` model (`models/notifications.py`); **notification
  service** (`services/notifications.py`: create in-app; optional SMTP email when
  `app_config['smtp.enabled']` + `smtp.config`, graceful in-app fallback — Decision #20);
  **outbox publisher** (`services/outbox_publisher.py`: relays pending `event_outbox` CloudEvents,
  v1 log sink, marks published/failed — Decision #5); **scheduler jobs** (`services/scheduler_jobs.py`:
  publish-outbox, installment-due & loan-due reminders); **worker** (`app/worker.py`) now runs
  **APScheduler** (outbox every 15s; reminders hourly); **notifications API** (`api/notifications.py`:
  list, create (dev/test), mark-read). Wired into `main.py`. All 50 backend files pass syntax check.
- **Next step:** Begin **Phase 8 — Frontend polish & UX** (React + UI5 Web Components): OIDC login
  (Keycloak), Fiori launchpad with KPI tiles, list-report + object pages for core entities
  (accounts, transactions w/ filter bar, partners, categories, budgets, investments, imports wizard),
  reports area with charts + SQL console, configuration area (code lists, LLM/integration endpoints,
  currencies/rates, holiday calendars), global confirmation dialogs (T.9), notification center.
- **Verify:** `cd infra && cp .env.example .env && docker compose up -d --build`, then
  `GET /api/docs`; `GET /api/v1/notifications`; `POST /api/v1/notifications {"subject":"Test"}`;
  worker logs show `[worker] ... scheduler` and periodic `[outbox]` lines.

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
- [x] **Phase 1 — Data & platform core** (models, base mixin, id-sequence, outbox+audit, Keycloak/RBAC, code_list/code_value + seed system code lists, value-help endpoints, generic Repository with search/filter/sort/pagination; Alembic scaffolded — first real migration pending in Phase 2)
- [x] **Phase 2 — Core financial APIs** (accounts, transactions, categories, cash_flow_items, partners, beneficiaries, currencies/rates, transfers, splits, tags, attachments, FX lookup, country/institution/currency reference routers, first Alembic migration + FX no-overlap constraint)
- [x] **Phase 3 — Recurrence, installments, loans, goals, income** (recurrence engine w/ business-day rules + holiday calendars; installment plans + schedule; loans + amortization; goals; pending-recurring + materialize-to-transaction; income via cash_flow_item.flow_type)
- [x] **Phase 4 — Integrations & automation** (connector framework FX/stock/crypto, LLM Gateway w/ failover+redaction, rules engine, investment valuation refresh+history, FX refresh into validity periods, seeded Ollama provider + default endpoints)
- [x] **Phase 5 — Import pipeline** (pdf/csv/xlsx parse → rule/LLM-assisted mapping matched/new/unmapped → validation rows + amend → commit creating transactions with dedup + filename note + source_document_id)
- [x] **Phase 6 — Budgeting & reporting** (budgets + lines + budget-vs-actual variance + recommendations; prebuilt reports: category/partner/beneficiary volume, cash position, net worth, projection — all in USD via FX; guarded read-only SQL console)
- [x] **Phase 7 — Notifications & scheduler** (notification model + API list/create/mark-read; SMTP email w/ in-app fallback; APScheduler worker: outbox publisher + installment/loan due reminders; CloudEvents outbox relay)
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
