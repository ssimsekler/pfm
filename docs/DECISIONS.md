# Architecture Decision Records (ADR Log)

Chronological log of key decisions. Newest decisions appended at the bottom.

| # | Decision | Rationale |
|---|---|---|
| 1 | Backend is Python + FastAPI only (no Node hybrid for v1) | Native OpenAPI, strong for parsing/LLM/data; single runtime simplifies deploy/auth/testing. Modular so a worker can split later. |
| 2 | Frontend: React + Vite + `@ui5/webcomponents-react` | Authentic SAP Fiori look (T.11) with React productivity. |
| 3 | Auth: Keycloak (OIDC) with RBAC (Owner/Editor/Viewer) | Standard, SSO-ready; multi-user requirement. |
| 4 | Keycloak shares the same PostgreSQL instance (separate schema) | One DB container; simpler ops. |
| 5 | Events: transactional outbox table only (CloudEvents 1.0); broker optional/future | Minimum viable per user choice; guarantees data/event consistency. |
| 6 | mnemonic IDs immutable; prefix change affects only NEW records | Preserves referential stability (A.1). |
| 7 | Per-prefix configurable pad width in `id_sequence` | Supports TRN 10-digit vs PRT 5-digit (A.2). |
| 8 | Cross-currency transfers store both leg amounts + derived fx_rate | Correct multi-currency accounting (A.4). |
| 9 | Investment current value = latest `valuation_history` row (cache field allowed) | Single source of truth (A.5). |
| 10 | SQL reporting: read-only role, timeout, forced LIMIT, views only, no DDL/DML | Security for free-form SQL (6.2/A.6). |
| 11 | T.9 confirmation enforced at UI only; APIs use prepare/commit for destructive bulk ops | Keeps APIs clean/automatable (A.7). |
| 12 | CloudEvents emitted only for state-changing operations | Avoids read noise (A.8). |
| 13 | Configurable holiday calendars for business-day recurrence rules | Supports "last working day" (A.9). |
| 14 | Document provenance stores original filename + server storage key (not client full path) | Browser cannot obtain client full path (A.10). |
| 15 | Expense item fulfilled by multiple transactions; `expense_item_seq_no` auto-assigned but editable | Matches A.11 semantics. |
| 16 | Category inheritance = Policy 1: item-linked transactions inherit item's category; no category-split when item-linked | Integrity between transaction & item category (D.a). |
| 17 | Income & expense unified in one `cash_flow_item` table with `flow_type` flag | Reuses recurrence/budget logic; supports projections. |
| 18 | `integration_endpoint` is a single registry for all non-LLM integrations (FX/stock/crypto/SMTP) | Canonical, swappable interfaces (T.4.2). |
| 19 | LLM Gateway: central provider list, per-feature primary/secondary, disable switches, master switch, PII redaction, graceful placeholders | T.4.1 requirements. |
| 20 | Notifications: in-app always; email when SMTP configured | User choice; graceful degradation. |
| 21 | Soft delete for financial records; audit_log with before/after; correlation to CloudEvent id | Auditability & recoverability. |
| 22 | Commit continuously; attempt push to remote; if push fails, keep committing locally | User instruction. |
| 23 | All enumerated value sets are configurable entities (`code_list` + `code_value`); every former enum column becomes a `*_cv_id` FK to `code_value` constrained to a specific `list_key` | Drives value helps/comboboxes and server-side validation; lets users extend value sets. System lists seeded with predefined values. Structural `level` fields excepted. |
| 24 | Bundle a local **Ollama** container as a default, configurable LLM provider (kind=ollama) | Out-of-the-box, privacy-friendly, offline-capable local LLM; seeded as an `llm_provider` the Gateway can use as primary/secondary. Model pulled on demand; GPU optional. |
| 25 | Every list screen + `GET /api/v1/{entity}` supports free-text search, structured filters, sort, pagination (Fiori FilterBar; `pg_trgm` indexes) | Users can search/filter transactions, partners, beneficiaries, categories, etc. (spec 6.1 + user request). |
| 26 | `currency_rate` uses validity periods (`begin_date`/`end_date`), lookup `begin_date <= date < end_date`; open-ended entry uses `9999-12-31`; overlaps prevented by GiST exclusion constraint | User-requested; guarantees a valid rate always exists; replaces closest-date approach. |
| 27 | Reporting currency is configurable, **default USD** (`app_config.default_base_currency=USD`, per-user `app_user.base_currency`); transactions stay in native currency (mostly AED). Imports always land on the validation screen for user review/entry before recording | Reports (cash position, projection, net worth, volumes) roll up in USD via validity-period FX; user confirms/edits parsed statement rows before commit (spec 3.2). |
