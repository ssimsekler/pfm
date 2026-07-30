# PFM Build Progress (Resume File)

> **On restart, read this file FIRST.** Then `docs/PLAN.md` and `docs/DECISIONS.md`.
> This file records the current phase, what is done, and the exact next step.

## Current status

- **Active phase:** Phase 6 — Budgeting & reporting (COMPLETE) → next: Phase 7
- **Last completed (Phase 6):** models (`models/budgeting.py`): budget, budget_line,
  budget_actual_snapshot; **reporting service** (`services/reporting.py`: volume-by-category,
  volume-by-field partner/beneficiary, cash position per account + per-currency + reporting-ccy
  total, net worth — all converted to USD via FX); **SQL console** (`services/sql_console.py`:
  single SELECT only, read-only txn, statement_timeout, forced LIMIT, DDL/DML blocked —
  Decision #10); **reporting API** (`api/reporting.py`): budgets CRUD + `/{id}/lines` (add/list/
  delete) + `/{id}/variance` (budget-vs-actual in USD) + `/{id}/recommendations` (recent spend +
  optional LLM commentary via Gateway); `GET /api/v1/reports/volume-by-category|volume-by-partner|
  volume-by-beneficiary|cash-position|net-worth|projection`; `POST /api/v1/reports/sql`.
  Wired into `main.py`. All 49 backend files pass syntax check.
- **Next step:** Begin **Phase 7 — Notifications & scheduler**: notification model + CRUD/read
  endpoints; SMTP sender (configurable, in-app fallback — Decision #20); worker scheduler
  (APScheduler) jobs for FX refresh, valuation refresh, recurring-due reminders, budget-overrun
  and installment/loan-due alerts; outbox publisher loop.
- **Verify:** `cd infra && cp .env.example .env && docker compose up -d --build`, then
  `GET /api/docs`; `/api/v1/reports/cash-position`, `/api/v1/reports/net-worth`,
  `/api/v1/reports/volume-by-category`; create a budget + lines then `/{id}/variance`;
  `POST /api/v1/reports/sql {"sql":"select * from pfm.account"}`.

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
