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

Each phase ends with a working, committed increment. Commit continuously; attempt push to
`https://github.com/ssimsekler/pfm.git`; if push fails, keep committing locally.

## 9. Timeline

Measured in build sessions, not calendar months. Working app by ~Phase 2; complete v1 across
roughly a dozen focused sessions. ("~3–5 months" only references equivalent traditional team effort.)