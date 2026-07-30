# PFM Build Progress (Resume File)

> **On restart, read this file FIRST.** Then `docs/PLAN.md` and `docs/DECISIONS.md`.
> This file records the current phase, what is done, and the exact next step.

## Current status

- **Active phase:** Phase 9 — Quality & delivery (COMPLETE). **All planned phases (0–9) done.**
- **Last completed (Phase 9):** backend **pytest suite** under `backend/tests/` covering pure
  logic — recurrence engine (`test_recurrence.py`), installment + loan amortization schedules
  (`test_schedules.py`), CSV import parsing + date/amount normalization (`test_import_parser.py`),
  mnemonic id-sequence formatting/prefix rules (`test_id_sequence.py`), and consolidated FX
  validity lookup + SQL-console guard + rules matcher + import dedup hash (`test_services.py`);
  `pytest.ini`; `requirements-dev.txt` (pytest); expanded **README** with run/verify/test guide;
  data-export + import round-trip already present. All test files parse cleanly.
- **Next step:** None — development plan complete. Optional future work: real Alembic
  autogenerate migrations per change, broker-backed outbox, more UI object-page editors,
  end-to-end (Playwright) tests, Helm chart.
- **Verify:** `cd infra && cp .env.example .env && docker compose up -d --build`; open
  `http://localhost/` (Fiori shell) and `http://localhost/api/docs`. Run tests:
  `docker compose run --rm backend sh -c "pip install -r requirements-dev.txt && pytest"`.

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
  - [x] `infra/docker-compose.yml` + `.env.example`
  - [x] Postgres init (schemas + read-only role), Keycloak realm import
  - [x] Minimal FastAPI health app + worker placeholder
  - [x] React + Vite + UI5 Web Components scaffold
  - [x] `.gitignore`, `README.md`, `LICENSE`, `.dockerignore` files
  - [x] git init, first commit, push to remote
- [x] **Phase 1 — Data & platform core** (models, base mixin, id-sequence, outbox+audit, Keycloak/RBAC, code_list/code_value + seeds, value-help, generic Repository w/ search/filter/sort/pagination)
- [x] **Phase 2 — Core financial APIs** (accounts, transactions, categories, cash_flow_items, partners, beneficiaries, currencies/rates, transfers, splits, tags, attachments, FX lookup, country/institution/currency routers, initial Alembic migration + FX no-overlap constraint)
- [x] **Phase 3 — Recurrence, installments, loans, goals, income** (recurrence engine + holiday calendars; installments; loans + amortization; goals; pending-recurring + materialize; income via flow_type)
- [x] **Phase 4 — Integrations & automation** (connectors FX/stock/crypto, LLM Gateway w/ failover+redaction, rules engine, valuation refresh+history, FX refresh, seeded Ollama + endpoints)
- [x] **Phase 5 — Import pipeline** (pdf/csv/xlsx parse → mapping → validation rows → commit w/ dedup + filename note + source_document_id)
- [x] **Phase 6 — Budgeting & reporting** (budgets + lines + variance + recommendations; prebuilt reports in USD; guarded SQL console)
- [x] **Phase 7 — Notifications & scheduler** (notifications in-app + SMTP; APScheduler worker: outbox publisher + due reminders)
- [x] **Phase 8 — Frontend polish & UX** (Fiori shell, launchpad KPIs, transactions filter bar, reusable DataTable, entity lists, reports+charts+SQL, imports wizard, notifications, configuration, export)
- [x] **Phase 9 — Quality & delivery** (pytest suite for id-sequence/FX/recurrence/schedules/rules/import/SQL-console; pytest.ini; requirements-dev; README run/verify/test guide)

## Enhancements delivered (beyond base spec)

- Configurable code lists driving all enums (ADR #23); local Ollama LLM (ADR #24);
  search/filter on all lists (ADR #25); FX validity periods (ADR #26); USD reporting
  currency (ADR #27); configurable country + institution (ADR #28); full XLSX data
  export + import round-trip (ADR #29).

## Notes / open items

- Remote: `https://github.com/ssimsekler/pfm.git`. If push fails, keep committing locally.
- Confirmation dialogs (T.9) are UI-only.
- `pip` is blocked on the build host; backend/pytest run inside the container image.
- Data export (ADR #29): `GET /api/v1/export/xlsx` + `POST /api/v1/export/to-folder`.
- DB admin GUIs (ADR #30, dev utilities): **pgAdmin** at `/pgadmin`, **Adminer** at `:8081`,
  MinIO console at `:9001`. Connect to Postgres via host `db`, port `5432`.
