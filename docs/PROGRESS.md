# PFM Build Progress (Resume File)

> **On restart, read this file FIRST.** Then `docs/PLAN.md` and `docs/DECISIONS.md`.
> This file records the current phase, what is done, and the exact next step.
>
> **Maintenance rule (mandatory):** update these docs (PROGRESS/DECISIONS/ERD/PLAN) with
> every change, in the same increment as the code. See `.clinerules/docs-continuity.md`.

## Current status

- **Active phase:** Phase 11 — UX bug-fix & feature pass (IN PROGRESS). Fixing reported
  issues in batches; commit/push after each batch (per `.clinerules/docs-continuity.md`).
  - **Round 2 Batch 1 (DONE):** fixed create HTTP 500 on Account/Cash Flow Item/Currency Rate
    — audit `_snapshot()` is now JSON-safe (Decimal→float) [ADR #42, #5]; **server-side derived
    level** for beneficiary/expense-category via a CRUD `pre_write` hook (depth guards, self/cycle
    reject) [ADR #43, #3]; **full ISO** currencies+countries seeded (`iso_data.py`) [ADR #44, #1];
    Postgres **advisory lock** serializes API+worker startup [ADR #45]. Verified Account→201,
    132 currencies.
  - **Round 2 Batch 2 (DONE):** **migrated UI from UI5 → MUI** (finance-blue theme) [ADR #41] —
    AppBar+Drawer shell, MUI **DataGrid** lists (built-in filters/sort/pagination), **Autocomplete**
    type-ahead value help (#2), **X Date Pickers** (#4), resizable MUI dialogs (#10); ComboField
    cache clears after writes + excludes self as parent (#3); confirm-on-cancel-if-dirty / delete /
    import-commit / import-replace (#38); Reports use **Recharts** (volume pies incl. supplier &
    beneficiary) (#13 partial). All pages rebuilt on MUI; frontend builds and serves 200.
  - **Round 2 Batch 3 (DONE):** budget lines UI (#6) + expense-category CSV seed (#8) [ADR #47];
    **App Settings** screen incl. LLM master switch + **Entity Prefixes** + **My Profile**
    (backend `admin.py`: `/v1/app-config`, `/v1/id-sequences`, `/v1/profile`; `app_user` gains
    name + date/number/time-format prefs) [ADR #48]; **holiday calendar** weekend/week-start +
    day editor (`HolidayDaysDialog` row action; `weekend_days`/`week_start` + delete-day endpoint)
    (A.1) [ADR #49]; **loan/investment auto-create backing account** via `pre_write` hook (A.6)
    [ADR #50]; **country-aware import mapping** (parser date/number locale + `country` on upload +
    Imports country selector) (#4) [ADR #51]. Frontend builds; backend files compile clean.
  - **Round 2 Batch 4 (IN PROGRESS):**
    - DONE: **more reports** (#13) [ADR #52] — `monthly-trend` endpoint + service and a Reports
      **Monthly Trend** line chart + **Budget vs. Actual** bar chart (per-budget picker on the
      existing `/variance` endpoint).
    - DONE: **installment/loan payment tracking** (#15/#16) [ADR #53] — `POST …/schedule/{sid}/pay`
      on installment-plans (marks paid) and loans (principal+interest); frontend `ScheduleDialog`
      (generate schedule + record payments, paid indicator) via a "Schedule & payments" row action
      on the Loans and Installments lists. Frontend builds; backend compiles clean.
    - TODO: investment valuation history UI (#18); recurring items UI (#19); transfers dialog (A.5);
      auth: admin user + Users admin + password fallback (#14); in-app Help/Wiki (A.2).
  - **Batch A (DONE):** fixed blocking nested-dialog overlay (#1); refined confirmation model
    — no confirm on Save; confirm on **Cancel only if the form is dirty** (#2); resizable/
    draggable dialogs (#10); singular-title typo "Categorie" (#6); reworked value-help to a
    reliable native `<select>` so comboboxes populate/select everywhere (#11); default the
    transaction name from the selected cash-flow item (A.4); real **routing** via `HashRouter`
    so every screen has its own URL and Back/refresh work, plus a working avatar/profile
    popover (#3, part of #14).
  - **Batch B (DONE):** structured **filter bar** on lists (#20) — new `FilterBar` component +
    `EntityManager` wiring + per-entity `filterFields` in `entities.js`; backend `build_crud_router`
    now accepts declared `filter_fields` as exact-match query params (accounts/partners/
    beneficiaries/expense-categories/cash-flow-items), transactions already had rich filters.
    Fixed card "snapping": Overview `Balances by Currency` (#12) and Export/Import cards (#9) now
    use a block flex-column container inside `BusyIndicator` with gaps. Code-list card is now
    scrollable with a sticky header (#7).
  - **Batch C (PARTIAL):** DONE — fixed code-list key mismatches so all comboboxes populate
    (the real cause of #11); **partner `country_id`** (#4, model+schema+form+filter); **loan
    `loan_category`** code list + field (#17); **removed the manual Level field** from
    beneficiary/expense-category forms (#5, derivation note shown); backend `filter_fields`
    declared on generic entities; **additive `ADD COLUMN IF NOT EXISTS`** at startup so existing
    DBs gain new columns. TODO (next pass): country-aware **import mapping** (#4); expense-
    category **CSV seed** (#8); server-side **derived level** (#5); holiday calendar weekend/
    week-start + day editor (A.1); loan/investment **auto-create backing account** (A.6);
    **app_config CRUD + Settings screen** incl. LLM master switch (A.7); **user profile**
    (name/email/date-time-number formats); entity-prefix (`id_sequence`) maintenance UI.
  - **Batch D (TODO):** reports + charts (#13); installment/loan payment tracking + txn link
    (#15/#16); investment valuation history (#18); recurring cash-flow items + profiles (#19);
    transfers dialog (A.5); auth: default admin user, Users admin, password fallback (#14);
    in-app Help/Wiki incl. categorization rules (A.2).
- **Previous:** Phase 10 — CRUD UX & maintenance APIs (COMPLETE). **Phases 0–10 done.**
- **Last completed (Phase 10):**
  - **Backend:** transaction **splits API** on the transaction router
    (`GET/PUT/POST/PATCH/DELETE /api/v1/transactions/{id}/splits`) with exact-sum validation,
    `is_split` maintenance, and Policy-1 block (ADR #33); **code-value admin API**
    (`POST/PATCH/DELETE /api/v1/code-lists/{key}/values`) honoring `is_system`/`allow_user_values`
    (ADR #34); fixed `config.py` Pydantic v2 (`model_config` only); added missing
    `app/models/budgeting.py` (`Budget`/`BudgetLine`), `app/services/rules.py` (rules engine),
    outbox `publish_pending` + real APScheduler `app/worker.py`.
  - **Frontend:** metadata-driven CRUD layer (ADR #32) — `src/entities.js` registry +
    reusable `EntityManager`/`EntityForm`/`ComboField`/`ConfirmDialog`/`SplitEditor` and
    `CodeValueManager`; every master/config/transactional entity now has create/view/edit/delete
    with **autocomplete value help** and **confirm-on-write**; multi-line **split editor** for
    transactions (Policy-1 aware); **Institutions** wired into Master Data nav + routes; fixed
    `investments` path to `/v1/investments`; unified the duplicated `EntityList`/`Transactions`
    configs onto `entities.js`.
  - **Layout:** global `src/index.css` reset (box-sizing; `html/body/#root` height + `margin:0`)
    imported in `main.jsx`; responsive launchpad KPI cards.
  - **Infra (earlier this session):** `.env` created from example; frontend Dockerfile
    `npm install --legacy-peer-deps`; pinned UI5 to v1.x; `DataTable` semantic HTML table;
    Traefik switched to the **file provider** (`infra/traefik/dynamic.yml`) because Docker
    Desktop's socket returned HTTP 400; kept `postgres:16`; removed heavy pgAdmin (Adminer kept).
- **Next step:** Optional — split-sum unit tests + a Playwright happy-path (create/edit/delete
  incl. a transaction with splits); dependent value help (cascading code lists); currency CRUD
  if ever needed. Otherwise plan complete.
- **Verify:** `cd infra && cp .env.example .env && docker compose up -d --build`; open
  `http://localhost/` (Fiori shell) and `http://localhost/api/docs`. Try: create an Institution;
  create a Transaction with split lines; edit/delete any record (each asks for confirmation).
  Run tests: `docker compose run --rm backend sh -c "pip install -r requirements-dev.txt && pytest"`.

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
- [x] **Phase 10 — CRUD UX & maintenance APIs** (metadata-driven frontend CRUD layer with autocomplete value help + universal confirm-on-write [ADR #32]; transaction splits API + multi-line split editor [ADR #33]; code-value/code-list admin API + UI [ADR #34]; Institutions wired into navigation; global CSS reset + responsive launchpad cards; `.clinerules/docs-continuity.md` standing rule for docs continuity)

## Enhancements delivered (beyond base spec)

- Configurable code lists driving all enums (ADR #23); local Ollama LLM (ADR #24);
  search/filter on all lists (ADR #25); FX validity periods (ADR #26); USD reporting
  currency (ADR #27); configurable country + institution (ADR #28); full XLSX data
  export + import round-trip (ADR #29).

## Notes / open items

- Remote: `https://github.com/ssimsekler/pfm.git`. If push fails, keep committing locally.
- Confirmation dialogs (T.9) are UI-only; extended to **all** UI writes (create/edit/delete)
  via the reusable `ConfirmDialog` (ADR #32).
- `pip` is blocked on the build host; backend/pytest run inside the container image.
- Data export (ADR #29): `GET /api/v1/export/xlsx` + `POST /api/v1/export/to-folder`.
- DB admin GUIs (ADR #30, dev utilities): **Adminer** at `:8081` and the MinIO console at
  `:9001` (pgAdmin was removed to reduce image footprint). Connect to Postgres via host `db`,
  port `5432`.
- Reverse proxy uses Traefik's **file provider** (`infra/traefik/dynamic.yml`) instead of the
  Docker provider, because Docker Desktop's mounted socket returned HTTP 400 to the Docker API.
- Frontend pins **`@ui5/webcomponents*` v1.x** (source uses the v1 component API); Dockerfile
  runs `npm install --legacy-peer-deps`.
- Frontend routing uses **HashRouter** (`#/screen`) so it works behind nginx/Traefik without
  server-side rewrites; each screen has its own URL (Back/refresh work).
