# PFM Build Progress (Resume File)

> **On restart, read this file FIRST.** Then `docs/PLAN.md` and `docs/DECISIONS.md`.
> This file records the current phase, what is done, and the exact next step.
>
> **Maintenance rule (mandatory):** update these docs (PROGRESS/DECISIONS/ERD/PLAN) with
> every change, in the same increment as the code. See `.clinerules/docs-continuity.md`.

## Current status

- **Active phase:** Phase 11 — **Session 815** bug-fix & feature pass (IN PROGRESS).
  Shared batch prefix **`815-`** (per `.clinerules/docs-continuity.md`: one random
  3-digit prefix per session). Commit + push after each batch, then continue.
  - **815-Batch checklist:**
    - [x] 815-Batch 1 — Formatting engine (Items 1, 4, 5, 8, 18) — **DONE** [ADR #76]:
      `format.js` resolves profile → app-config `format.*` → default; new `time_locale`
      (Item 8, dayjs in `App.jsx`) + `amount_decimals` (Item 5) via `formatHighPrecision()`
      used only for FX rates + investment quantity/unit price (`highPrecision` DataTable
      flag; `currency-rates.rate`, `investments.quantity`); Reports charts formatted (Item 1);
      `<DatePicker>` gets `format` + `maxDate=9999-12-31` (Item 4); seeded `format.*` app
      settings (Item 18); additive `app_user.time_locale/amount_decimals/username` +
      Settings→My Profile fields. Frontend builds; backend compiles.
    - [x] 815-Batch 2 — Audit actor population (Item 7) — **DONE**: `crud_router.resolve_actor()`
      maps the caller (keycloak_subject → uuid → email) to an `app_user.uuid`, passed as `actor`
      to `Repository.create/update/soft_delete` so `created_by`/`updated_by` are real users;
      `_strip_audit()` drops any client-sent `created_*`/`updated_*`/`deleted_at`. Wired into the
      generic CRUD factory **and** the dedicated transactions router. All four audit columns
      (`created_at/by`, `updated_at/by`) already exist on every `BaseEntity`. Backend compiles.
    - [x] 815-Batch 3 — Auth/identity/users (Items 6, 9, 10, 11, 12) — **DONE**: role
      **Owner→Admin** (seed_data ROLES + seeder renames the legacy row preserving grants +
      security.py `WRITE_ROLES={Admin,Owner,Editor}` + realm adds `Admin` and grants admin
      user Admin+Owner) (6); **username ≥ 3** enforced in Users create form + backend `create_user`
      (9); **create-user 500/409 fixed** — `keycloak_admin.create_user` reconciles an existing
      username by returning its subject, `create_user` sets the password + reuses/reactivates an
      existing local mirror in one committed unit with rollback (10); **Username column** + `active`
      status + `include_inactive` on Users list; `app_user.username` stored on create and backfilled
      in `_get_or_create_user` (11); AppBar/Users now show **username** (auth.js prefers
      `preferred_username` over the token display name) (12); **deactivate/reactivate/remove** user
      endpoints (`keycloak_admin.set_user_enabled`/`delete_user`) + Users row actions (6). Backend
      compiles; frontend builds.
    - [ ] 815-Batch 4 — FX & stock sources (Items 3, 15).
    - [ ] 815-Batch 5 — Config UX: Credentials Store, SMTP, tabs, base-ccy (Items 16, 17, 19, 20, 22).
    - [ ] 815-Batch 6 — Accounts numbers, tree 422 fix, Help toolbar (Items 14, 21, 2).
- **Previous phase:** Phase 11 — **Session 742** bug-fix & feature pass (COMPLETE).
  **The full, detailed plan for this session lives in `docs/PLAN.md` §10 (Phase 11 — Session
  742).** All batches use the shared prefix **`742-`**; commit + push after each batch, then
  proceed to the next without asking (per `.clinerules/docs-continuity.md`).
  - **742-Batch checklist:**
    - [x] 742-Batch 1 — Auth & identity (bugs 1, 2, 3) — **DONE** [ADR #63–65]:
      `app_user.keycloak_subject` (additive) + profile auto-provision (Bug 1); full Keycloak
      user provisioning via `services/keycloak_admin.py` + temp password + role sync,
      `user_role.grant_household_id` made nullable (Bug 2); password-fallback refresh token +
      `POST /v1/auth/refresh` + `api.js` refresh-on-401 + `pfm:session-expired` re-login prompt
      (Bug 3). Backend compiles; frontend builds.
    - [x] 742-Batch 2 — Data model, validation & schedule import (4, 10, 11, 12, 19, New-1) —
      **DONE** [ADR #66–70]: account type+institution required (Bug 4); loan/investment always
      auto-create a (loan/investment-type) backing account, Account field hidden on create
      (Bug 10); installment↔txn link surfaced in ScheduleDialog (Bug 11); budget line
      either CFI **or** category+direction, enforced server-side + UUID→label in the dialog
      (Bug 12/22); goals gain type/category/period/limit + `transaction.goal_id` +
      `GET /v1/goals/{id}/progress` (Bug 19); CSV schedule import for loans & installments
      (`…/schedule/import`) + ScheduleDialog "Import CSV" (New-1); `EntityForm` gained a
      `select` field type. Backend compiles; frontend builds.
    - [x] 742-Batch 3 — Reports & display (5, 22, 23) — **DONE** [ADR #71]:
      `volume_by_field` resolves partner/beneficiary names → `label` (Bug 5); budget-line
      UUID→label already done in Batch 2 (Bug 22); new `cash_projection` service +
      `GET /v1/reports/cash-projection?budget_id=&months=` + Reports **Cash Projection**
      multi-line chart (month-end cash/investments/loans/net) (Bug 23). Backend compiles;
      frontend builds.
    - [x] 742-Batch 4 — Settings, SMTP, FX, LLM sequence (6, 7, 8, 20, New-2) — **DONE**
      [ADR #72]: standardized LLM switch on `llm.master_enabled` + seeder migrates/deletes
      stray `llm.enabled` (6/7); **rewrote `llm_gateway.py`** into a real gateway with
      priority failover gated by the master switch (fixed a latent missing-`complete()`
      crash) + Priority field on LLM Providers (New-2); consolidated SMTP onto discrete
      `smtp.*` keys + `send_test_email` + `POST /v1/notifications/test-email` + Email (SMTP)
      settings card with "Send test email" (8); FX "Refresh from source" card on Configuration
      → Currency Rates (20). Backend compiles; frontend builds.
    - [x] 742-Batch 5 — Investment valuation fix (new bug) — **DONE** [ADR #73]:
      `refresh_holding(on=None)` accepts a target date, overwrites/inserts that date's row,
      keeps cache on the latest; typed `ValuationError` (manual_only vs source) →
      `POST …/refresh-valuation` (now with `on`) returns a **helpful 422** instead of the
      opaque message; ValuationDialog passes the chosen "As of" date. Backend compiles;
      frontend builds.
    - [x] 742-Batch 6 — Import intelligence & flexibility (17, 18) — **DONE** [ADR #74]:
      new `import_mapping_memory` table + `import_mapper.record_memory` (learns
      source_text→partner/category, `accept_count`) and `map_row` recommends the most-frequent
      mapping; LLM-assisted category hint (gated by `llm.master_enabled`); per-row account
      deduced from `account`/`iban`/`account_number` with fallback to the commit default (Bug 18);
      `commit_import` records memory + books per-row account. Backend compiles.
    - [x] 742-Batch 7 — UX polish (9, 13, 14, 15, 16, 21, 24, 25) — **DONE** [ADR #75]:
      distinct per-item nav icons + **collapsible mini Drawer** with tooltips, persisted
      (`pfm_nav_collapsed`) (9/24); **success toasts** on create/edit/delete in EntityManager
      (and CFI→transaction) (13); **beneficiary inheritance** from the cash-flow item into the
      materialized transaction (server default + pre-filled, editable dialog field) (14); Help
      **chips expand + smooth-scroll** to the section (no dead hash anchors) (15); **greatly
      expanded categorization-rules guide** + new Help sections for SMTP/Yahoo, loan/installment
      link, goals, formats, import intelligence, multi-account CSV, cash projection (16); new
      **`format.js`** display utility (profile → settings `format.*` → defaults yyyy-MM-dd / HH:mm /
      1,234.56), initialized at startup and used by DataTable `money`/`date`/`datetime` columns (21);
      **tree view** for Categories & Beneficiaries via `EntityTree` + `HierarchyList` (Tree/Table
      toggle, shared Create/Edit/Delete) (25). Frontend builds; backend compiles.
    - **742-Batch 7 completes Session 742 — all 28 reported items + New-1/New-2 delivered.**
- **Previous Phase 11 rounds** (kept for history): UX bug-fix & feature pass rounds — fixing
  reported issues in batches; commit/push after each batch (per `.clinerules/docs-continuity.md`).
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
      on the Loans and Installments lists.
    - DONE: **investment valuation history UI** (#18) [ADR #54] — frontend `ValuationDialog`
      (trend line chart + history table + manual add + refresh-from-source) via a "Valuation
      history" row action on Investments, over the existing valuations endpoints.
    - DONE: **recurring cash-flow items UI** (#19) [ADR #55] — new **Recurring** page (Planning nav)
      lists pending occurrences (`GET /v1/recurring/pending?until=`) and materializes them via
      `MaterializeDialog`; `recurrence-profiles` now a managed entity (Configuration) and
      `cash-flow-items` gained a `recurrence_profile_id` field.
    - DONE: **transfers dialog** (A.5) [ADR #56] — `TransferDialog` ("New Transfer" on Transactions)
      posts to `POST /v1/transfers` (dual-leg + transfer_group), cross-currency aware.
    - DONE: **in-app Help/Wiki** (A.2) [ADR #57] — `Help` page (Help nav) with collapsible sections
      incl. categorization rules, Policy 1, recurring, transfers, imports, reporting currency,
      settings/profile.
    - DONE: **auth — default admin + Users admin + password fallback** (#14) [ADR #58] — Keycloak
      realm seeds a default **admin** user (pwd `admin`, Owner) + enables direct-access grant;
      backend **Users admin API** (`/v1/users` + role grant/revoke) and **password-login proxy**
      (`/v1/auth/password-login`); frontend **Users** screen, **"Sign in with password"** dialog,
      and a fallback token in `auth.js`. Frontend builds; backend compiles clean.
    - **Phase 11 Round 2 backlog is now COMPLETE.** Remaining is optional polish only (below).
    - **UX fix pass (post-feedback) [ADR #59]:** materialize sets txn direction from the item's
      flow_type; transaction form shows a **disabled Cash Flow Item** field and **locks + inherits
      category/direction** when item-linked; **direction is mandatory**; fixed the splits PUT for
      plain transactions ("put is not a function"); SplitEditor hides Total/Remaining when empty;
      **all money values render at 2 decimals** (DataGrid `money` columns + Reports `money2`);
      "Volume by Supplier" → **"Volume by Partner"**; **Keycloak admin console** exposed
      (`/auth/admin` via proxy, and direct `:8082`).
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
- **Keycloak admin console** (dev utility, ADR #59): `http://localhost/auth/admin` (via the proxy)
  or `http://localhost:8082/auth/admin` (direct). Log in with `KEYCLOAK_ADMIN` /
  `KEYCLOAK_ADMIN_PASSWORD` from `.env`. A default realm **admin** user (pwd `admin`, Owner) is
  seeded for first app login — change it here for any real use.
- Reverse proxy uses Traefik's **file provider** (`infra/traefik/dynamic.yml`) instead of the
  Docker provider, because Docker Desktop's mounted socket returned HTTP 400 to the Docker API.
- Frontend pins **`@ui5/webcomponents*` v1.x** (source uses the v1 component API); Dockerfile
  runs `npm install --legacy-peer-deps`.
- Frontend routing uses **HashRouter** (`#/screen`) so it works behind nginx/Traefik without
  server-side rewrites; each screen has its own URL (Back/refresh work).
