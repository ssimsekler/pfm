# Personal Finance Management (PFM) — Master Plan

> This document is the single source of truth for the agreed plan. On any restart,
> read `docs/PROGRESS.md` first, then this file, then `docs/DECISIONS.md`.

## 1. Overview

A containerized, multi-user personal finance management application covering:
accounts, transactions, transfers, expense categories/items, recurrence, installments,
loans, goals, investments, budgeting, imports (pdf/csv/xlsx with LLM-assisted mapping),
multi-currency, analytics/reporting, notifications, and configurable integrations.

## 2. Technical Stack

| Layer | Choice |
|---|---|
| Packaging | Docker + Docker Compose (single-command up) |
| Backend | Python + FastAPI (OpenAPI-native) |
| ORM/Migrations | SQLAlchemy + Alembic |
| DB | PostgreSQL (shared by app + Keycloak, separate schemas) |
| Frontend | React + Vite + `@ui5/webcomponents-react` (SAP Fiori look) |
| Auth | Keycloak (OIDC), RBAC (Owner/Editor/Viewer) |
| Object storage | MinIO (S3-compatible) for documents/receipts |
| Events | Transactional outbox table (CloudEvents 1.0); broker optional/future |
| Worker | Same image as backend; APScheduler + DB-backed job queue |
| Reverse proxy | Traefik (TLS, routing) |
| LLM | Internal LLM Gateway: primary→secondary failover, disable switches, PII redaction |
| Local LLM | Ollama container (kind=ollama), seeded as a default configurable provider |
| External data | FX: Frankfurter/exchangerate.host · Stocks: yfinance/Alpha Vantage · Crypto: CoinGecko (all configurable) |

## 3. Resolved Spec Inconsistencies (A.1–A.12)

- A.1 Prefix change: only NEW records use the new sequence; mnemonic IDs immutable.
- A.2 Per-prefix pad width configurable (`id_sequence.pad_width`).
- A.3 Beneficiary vs Partner: distinct concepts, clarified in UX.
- A.4 Cross-currency transfers store both leg amounts + derived fx_rate.
- A.5 Investment current value = latest `valuation_history` row (cache field allowed).
- A.6 SQL reporting: read-only role, statement timeout, forced LIMIT, views only, no DDL/DML.
- A.7 Confirmation (T.9) enforced at UI only; APIs support prepare/commit for destructive bulk ops.
- A.8 CloudEvents emitted only for state-changing operations.
- A.9 Configurable holiday calendars for business-day rules.
- A.10 Document note stores original filename + server storage key (client full path not obtainable).
- A.11 Expense item = named obligation (one category, optional recurrence, expected amount),
  fulfilled by multiple transactions; each transaction has `expense_item_seq_no`
  (auto-assigned, editable). Fulfillment status tracked.
- A.12 Installment plan modeled separately but reuses recurrence generator.

## 4. Accepted Enhancements (Section B + gaps)

Multi-currency base; split transactions; tags; attachments; reconciliation; rules engine;
net worth; budget vs actual; audit trail; soft delete; import dedup; export/backup;
multi-user roles. Additional gaps accepted: loans/liabilities, goals, recurring income,
opening balances & balance reconstruction, scheduled jobs, notifications (in-app + optional
email), multi-currency net worth, encryption of secrets + PII redaction for LLM, idempotent import.

## 5. Data Model (see docs/ERD.md for field-level)

Base columns on all entities: `uuid` PK, `mnemonic_id` (unique), `name(120)`,
`description` (markup text), `created_at/by`, `updated_at/by`, `deleted_at` (soft delete),
`household_id` (tenant scope).

Groups: Security/tenancy; Config/meta; Core financial; Investments; Budgeting; Currency;
Import/docs; Automation/tagging; Notifications. Full field-level definitions in `docs/ERD.md`.

Key policies:
- **Policy 1 (category inheritance):** item-linked transactions inherit category from the
  expense item; category-split disallowed on item-linked transactions.
- **Cash flow item:** income & expense unified in one table with `flow_type` flag.
- **FX validity periods:** `currency_rate` has `begin_date`/`end_date`; lookup uses
  `begin_date <= date < end_date` (open-ended `9999-12-31`) — Decision #26.
- **Reporting currency:** transactions are native (mostly AED); reports/roll-ups compute in a
  configurable reporting currency (default **USD**) — Decision #27.
- **Search/filter:** every list endpoint & screen supports search, filter, sort, pagination —
  Decision #25.

## 6. API Surface (OpenAPI / T.8)

- CRUD for all entities: `/api/v1/{entity}` with **free-text search + structured filters +
  sort + pagination** on every list endpoint (transactions, partners, beneficiaries,
  categories, etc.) — Decision #25.
- Complex ops: transfers; import prepare→parse→preview→commit; recurrence pending/materialize;
  fx refresh/import; valuation refresh; reports run; reports sql (guarded); budget recommendations;
  projection.
- State-changing endpoints write to outbox + audit in the same DB transaction.

## 7. UX / Navigation (Fiori)

Launchpad with KPI tiles; List reports + object pages for all entities; import wizard;
reports area with charts + read-only SQL console; configuration area; global confirmation
dialogs; notification center.

## 8. Build Sequence (Phases)

- **Phase 0** Foundation: docs, repo scaffold, docker-compose, field-level ERD.
- **Phase 1** Data & platform core: models, migrations, base mixin, id-sequence, outbox+audit, Keycloak/RBAC.
- **Phase 2** Core financial APIs: accounts, transactions, categories, items, partners, beneficiaries, currencies/rates, transfers, splits, tags, attachments, FX lookup.
- **Phase 3** Recurrence, installments, loans, goals, income (cash_flow_item).
- **Phase 4** Integrations & automation: connector framework, FX/stock/crypto, LLM Gateway, rules engine, valuation refresh.
- **Phase 5** Import pipeline (pdf/csv/xlsx → mapping → preview → commit, dedup, filename note).
- **Phase 6** Budgeting & reporting: budgets, recommendations, variance, prebuilt reports, charts, SQL console.
- **Phase 7** Notifications & scheduler.
- **Phase 8** Frontend polish & UX.
- **Phase 9** Quality & delivery: tests, OpenAPI export, seed data, README, release.
- **Phase 10** CRUD UX & maintenance APIs: metadata-driven frontend CRUD layer
  (`entities.js` + `EntityManager`/`EntityForm`/`ComboField`/`ConfirmDialog`) giving every
  master/config/transactional entity create/view/edit/delete with autocomplete value help and
  universal confirm-on-write (ADR #32); transaction splits API + multi-line split editor
  (ADR #33); code-value/code-list admin API + UI (ADR #34); Institutions wired into navigation;
  layout reset (`index.css`) and responsive launchpad cards.

Each phase ends with a working, committed increment. Commit continuously; attempt push to
`https://github.com/ssimsekler/pfm.git`; if push fails, keep committing locally.

## 9. Timeline

Measured in build sessions, not calendar months. Working app by ~Phase 2; complete v1 across
roughly a dozen focused sessions. ("~3–5 months" only references equivalent traditional team effort.)

## 10. Phase 11 — Session 742 bug-fix & feature pass (ACTIVE)

> Resume marker for future sessions. All batches use the shared prefix **`742-`**.
> Commit + push after each batch, then proceed to the next without asking.
> Update PROGRESS.md/DECISIONS.md/ERD.md as each batch lands (docs-continuity rule).

### 742-Batch 1 — Auth & identity (bugs 1, 2, 3)
- **Bug 1 (profile 404 "No user profile row"):** `admin.py::_get_or_create_user` must
  **upsert** an `app_user` keyed by the Keycloak `sub`. Add additive column
  `app_user.keycloak_subject VARCHAR(64)` (bootstrap `_ADDITIVE_COLUMNS`). Lookup order:
  by `keycloak_subject`, then by email; if none, create a row (name/email from token) and
  set `keycloak_subject`. Then `update_profile` never 404s.
- **Bug 2 (add user → 500; no password; role grant 500):** **full Keycloak provisioning.**
  New `app/services/keycloak_admin.py` obtaining an **admin token** via the realm's
  `admin-cli`/service account (client credentials or the bootstrap admin creds from settings),
  and helpers: `create_user(username,email,temp_password) → sub`, `set_password`,
  `assign_realm_role(sub, role)`, `list_users`. `POST /v1/users` now creates the Keycloak user
  (returns a generated temp password once), then mirrors locally (`app_user` with
  `keycloak_subject`). Fix `_grant_role` (drop bogus `grant_household_id=role.uuid`; the
  single-user model doesn't need a household — make `grant_household_id` nullable or reuse the
  user's own id consistently). Surface Keycloak errors as 422 with detail. Realm: ensure a
  service account / admin client is enabled for the backend.
  - Settings/config additions: `keycloak_admin_client_id`, `keycloak_admin_client_secret`
    (or reuse `KEYCLOAK_ADMIN`/`KEYCLOAK_ADMIN_PASSWORD`).
- **Bug 3 (token expiry cascade — "401 Signature has expired" on every page):** the
  password-fallback token is never refreshed. In `auth.js`, persist the `refresh_token` from
  `/v1/auth/password-login`; add backend `POST /v1/auth/refresh` (proxy Keycloak refresh grant);
  in `api.js`, on a 401 attempt one silent refresh + retry; if it still fails, clear the
  fallback session and drop to guest (prompt re-login) instead of surfacing the raw 401 on
  every navigation.

### 742-Batch 2 — Data model, validation & schedule import (bugs 4, 10, 11, 12, 19, New-1)
- **Bug 4:** make `account_type_cv_id` + `institution_id` **required** — `required: true` in
  `entities.js` accounts fields and validate presence in `AccountCreate` (422 if missing).
- **Bug 10:** confirm `ensure_backing_account` fires for **both** loans and investments
  (`pre_write` already wired). On the create forms, **hide/disable the Account field** so the
  backing account is always auto-created; loan backing account should use a `loan`-type account
  (pass `account_type` code into `ensure_backing_account`). Show the linked account read-only on
  edit.
- **Bug 11:** *(explanation + surfacing)* installment↔transaction link is
  `installment_schedule.linked_txn_id` + `transaction.installment_plan_id`, set by
  **Record payment** in **ScheduleDialog** (opened from the per-row "Schedule & payments" action
  on the Loans & Installments lists). Show the linked transaction (mnemonic/date/amount) in the
  dialog; document in Help.
- **Bug 12:** budget line is **either/or** — either a **Cash Flow Item** (category + direction
  inherited from the item; hide those inputs) **or** a **Category + Direction** pair (when no
  item is chosen). `BudgetLinesDialog` toggles inputs by mode; validate exactly one mode
  server-side in `add_budget_line`.
- **Bug 19 (Goals ↔ Transactions):** add additive `transaction.goal_id` (FK goal, nullable) and
  extend `goal` with `goal_type_cv_id` (new code list `goal_type`: `save_to_target`,
  `cap_expense`), optional `expense_category_id`, `period` (e.g. monthly), `limit_amount`.
  New `GET /v1/goals/{id}/progress` evaluating matching transactions per period (e.g. fuel
  category sum vs `limit_amount`/month). Goals page shows progress. Transaction form gains an
  optional Goal ref.
- **New-1 (import loan/installment schedules from CSV):**
  `POST /v1/loans/{id}/schedule/import` and `POST /v1/installment-plans/{id}/schedule/import`
  (multipart CSV). Parse via `import_parser`; map columns → rows
  (loan: `period,due_date,principal_portion,interest_portion,balance`;
  installment: `seq,due_date,amount`). Replace-or-append (query/body flag). UI: "Import
  schedule (CSV)" button in `ScheduleDialog` with a small column-mapping/preview step.

### 742-Batch 3 — Reports & display (bugs 5, 22, 23)
- **Bug 5:** `reporting.volume_by_field` must resolve partner/beneficiary **names** (join;
  null → "Unassigned"); return a `label` field so the pie legend shows names (not UUID/"—").
- **Bug 22:** `BudgetLinesDialog` resolves category/CFI/direction **UUID → label** (shared
  id→label resolver reusing ComboField option loads).
- **Bug 23 (cash projection report):** `GET /v1/reports/cash-projection?budget_id=&months=`
  computing **month-end** cash / investments / loans / net for N months from current balances +
  budget/recurring net flows + loan amortization draw-down. Reports page: Budget picker +
  months input + multi-line Recharts chart.

### 742-Batch 4 — Settings, SMTP, FX, LLM sequence (bugs 6, 7, 8, 20, New-2)
- **Bug 6:** standardize the LLM master switch on **`llm.master_enabled`** (seed key). Update
  Settings UI (`LLM_MASTER_KEY`) to use it; **remove/migrate** the stray `llm.enabled` row.
  (Note ADR #48 used `llm.enabled`; this pass supersedes that to the seed's `llm.master_enabled`.)
- **Bug 7:** *(docs)* `llm.master_enabled` is the global kill-switch checked by the LLM gateway
  before any provider call; document in Help + the setting `description`.
- **Bug 8 (SMTP, any provider):** remove the **duplicate** notification service (there are two
  `notifications.py` implementations with conflicting SMTP schemes). Settle on structured
  `smtp.*` app-config keys (`smtp.enabled/host/port/username/password/from/to/security` where
  security ∈ none/starttls/ssl). Add a **generic SMTP settings card** in Settings + a
  **"Send test email"** action (`POST /v1/notifications/test-email`). Help includes a generic
  setup + a **Yahoo** example (smtp.mail.yahoo.com; 465 SSL or 587 STARTTLS; app password).
- **Bug 20:** add a **"Refresh from source"** control (base + comma quotes) to the Currency
  Rates section of Configuration, calling the existing `POST /v1/fx/refresh`.
- **New-2 (LLM provider sequence/failover):** the LLM gateway iterates **`LlmProvider` by
  `priority` ascending**, skipping disabled/unhealthy providers and falling through to the next
  on error/timeout (respect `llm.master_enabled`). **Resolve the duplicate `llm_gateway.py`**
  (one copy is actually the rules engine) so the real failover gateway is authoritative. Expose
  `priority` on the LLM Providers form; show effective order.

### 742-Batch 5 — Investment valuation fix (new bug)
- `valuation.refresh_holding(db, holding, on: date | None)` accepts a **target date**
  (default today); overwrite the row if one exists for that date, else insert. `ValuationDialog`
  passes the chosen date to `POST …/refresh-valuation` (add `on` body/query param).
- Fix **"422: Could not fetch a price"**: distinguish (a) generic `asset` type = manual-only
  (return an informative 422/hint, not a hard failure), (b) source unreachable / symbol not
  found (clear message). Offer a manual entry fallback in the dialog.

### 742-Batch 6 — Import intelligence & flexibility (bugs 17, 18)
- **Bug 17:**
  - Add **LLM-assisted categorization** on the import validation screen (gated by
    `llm.master_enabled`) producing category/partner suggestions per row.
  - Add **mapping memory**: new table
    `import_mapping_memory(uuid, source_text, mapped_partner_id, mapped_category_id,
    accept_count, updated_at)`. On commit, upsert + increment `accept_count` for the row's
    statement text → chosen partner/category. When mapping a new row, look up by `source_text`
    and **recommend the most-frequently-accepted** mapping (user can override). Learns from user
    actions (bank statement supplier text is stable).
- **Bug 18 (generic multi-account CSV):** support a **per-row account** deduced from an
  `account` / `iban` / `account_number` column, matched to an existing account; fall back to the
  commit's default account. Extend `import_mapper.map_row` + `commit_import`.

### 742-Batch 7 — UX polish (bugs 9, 13, 14, 15, 16, 21, 24, 25)
- **9 & 24:** distinct MUI icons per nav item; **collapsible mini Drawer** (icons + tooltips
  when collapsed) with a persisted toggle in the AppBar.
- **13:** global **success toast** on save across `EntityForm` + CFI flows.
- **14:** inherit **beneficiary** (and partner) from the cash-flow item into the transaction on
  materialize/create; keep the field editable.
- **15:** Help "chips" must use **in-page expand + `scrollIntoView`** (not `#help-...` hash
  links, which HashRouter treats as routes → "Not found").
- **16:** expand the Help **categorization-rules** section (condition keys/operators, action
  keys, priority/first-match, testing on import) with examples.
- **21:** **format utility** for date/number/time resolving **profile → app settings → defaults**
  (`yyyy-MM-dd`, `HH:mm`, `1,234.56`), wired into DataTable cells, Reports, and dialogs via a
  `FormatContext`/hook loaded once from `/v1/profile` + `/v1/app-config`.
- **25:** **tree view** (MUI `SimpleTreeView`) for Categories & Beneficiaries via `parent_id`,
  with a list/tree toggle on those pages.
