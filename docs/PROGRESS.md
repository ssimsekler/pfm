# PFM Build Progress (Resume File)

> **On restart, read this file FIRST.** Then `docs/PLAN.md` and `docs/DECISIONS.md`.
> This file records the current phase, what is done, and the exact next step.

## Current status

- **Active phase:** Phase 3 — Recurrence, installments, loans, goals, income (COMPLETE) → next: Phase 4
- **Last completed (Phase 3):** models (`models/scheduling.py`): holiday_calendar(+day),
  recurrence_profile, installment_plan(+schedule), loan(+amortization_schedule), goal;
  **recurrence engine** (`services/recurrence.py`: weekly, monthly_nth_day, monthly_last_day,
  monthly_last_bday, quarterly, yearly; business-day rules prev/next with holiday calendars —
  Decision #9/#13); **schedule generators** (`services/schedules.py`: equal installments +
  fixed-rate amortization); CRUD routers for holiday-calendars (+ `/{id}/days`),
  recurrence-profiles (+ `/{id}/occurrences` preview), installment-plans (+ `/generate`,
  `/schedule`), loans (+ `/generate`, `/schedule`), goals; and the **recurring** router:
  `GET /api/v1/recurring/pending?until=` (recurring cash-flow items with no txn yet) and
  `POST /api/v1/recurring/materialize` (creates a txn with next `expense_item_seq_no`,
  Policy 1 category inheritance — spec 1.4.1). Wired into `main.py`. Income is supported via
  `cash_flow_item.flow_type` (Decision #17). All 37 backend files pass syntax check.
- **Next step:** Begin **Phase 4 — Integrations & automation**: canonical connector framework
  driven by `integration_endpoint`; FX-rate pull (Frankfurter) + stock (yfinance/AlphaVantage)
  + crypto (CoinGecko) connectors; **LLM Gateway** (llm_provider + feature_llm_binding,
  primary→secondary failover, master switch, PII redaction, seed default Ollama provider);
  categorization rules engine; investment valuation refresh + history.
- **Verify:** `cd infra && cp .env.example .env && docker compose up -d --build`, then
  `GET /api/docs`, `/api/v1/recurrence-profiles/{id}/occurrences?until=2026-12-31`,
  `/api/v1/loans/{id}/generate`, `/api/v1/recurring/pending?until=2026-12-31`.

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
