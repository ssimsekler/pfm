# PFM — Field-Level Data Model (ERD)

PostgreSQL. All tables carry the **Base columns** unless noted. Types are PostgreSQL.
`FK` = foreign key. Monetary amounts use `NUMERIC(18,4)`. Timestamps are `TIMESTAMPTZ`.

## Base columns (mixin on every entity)

| Column | Type | Notes |
|---|---|---|
| uuid | UUID PK | `gen_random_uuid()` |
| mnemonic_id | VARCHAR(20) UNIQUE | e.g. `TRN-0000000001`, `PRT-00001` |
| name | VARCHAR(120) | required |
| description | TEXT | markup (markdown) allowed |
| created_at | TIMESTAMPTZ | default now() |
| created_by | UUID | FK app_user |
| updated_at | TIMESTAMPTZ | |
| updated_by | UUID | FK app_user |
| deleted_at | TIMESTAMPTZ NULL | soft delete |
| household_id | UUID | FK household (tenant scope) |

> Config/meta tables that are global (e.g. `id_sequence`, `app_config`) may omit `household_id`.

---

## Search & filtering (cross-cutting)

Every list screen and its backing `GET /api/v1/{entity}` endpoint supports **search and
filtering** (Decision #25):

- **Free-text search** on `name`, `mnemonic_id`, `description`, and entity-relevant text
  (e.g. transaction `note`, partner name). Backed by trigram (`pg_trgm`) indexes.
- **Structured filters** per attribute: exact match, ranges (dates/amounts), multi-select
  for code-list fields (via `*_cv_id`), and relation filters (e.g. transactions by account,
  partner, beneficiary, category level 1–3, tag, status, currency, date range, amount range).
- **Sort** on any column; **pagination** (offset/limit + total count).
- Filters map to Fiori **FilterBar** controls; the same query params drive the API.

Applies to transactions, partners, beneficiaries, expense categories, cash-flow items,
accounts, investments, budgets, installments, loans, imports, tags, etc.

## Reporting currency

Transactions are entered in their own currency (mostly AED). **Reports and roll-ups
(cash position, projections, net worth, category/beneficiary/partner volumes) are computed
in a configurable reporting currency (default USD)** — see `app_config.default_base_currency`
(seeded `USD`) and per-user `app_user.base_currency`. Conversion uses the validity-period
FX rate (`currency_rate`, `begin_date <= date < end_date`). Reports may also show per-currency
subtotals alongside the reporting-currency total. (Decision #26.)

---

## Configurable code lists (enumerated value sets)

**Every enumerated value set is a configurable entity**, not a hard-coded enum. This drives
value helps / comboboxes in the UI and server-side entry validation via FK constraints.
(Decision #23.)

Two tables implement a generic, extensible pattern:

### code_list
Base columns +:
| Column | Type | Notes |
|---|---|---|
| list_key | VARCHAR(60) UNIQUE | e.g. `partner_type`, `account_type`, `txn_status` |
| is_system | BOOLEAN | system lists cannot be deleted, only extended |
| allow_user_values | BOOLEAN | whether users may add new codes |
| mnemonic_id | `CDL-00001` | |

### code_value
Base columns +:
| Column | Type | Notes |
|---|---|---|
| code_list_id | UUID FK code_list | |
| code | VARCHAR(60) | stable machine value (e.g. `supplier`) |
| label | VARCHAR(120) | display text (localizable later) |
| sort_order | INT | ordering in value helps |
| is_default | BOOLEAN | preselected value |
| is_active | BOOLEAN | inactive values hidden from new entries but kept for history |
| parent_code_value_id | UUID FK code_value NULL | for dependent lists (cascading value help) |
| extra | JSONB | e.g. color, icon, semantic state |
| mnemonic_id | `CDV-000001` | |
| UNIQUE(code_list_id, code) | | |

**How referencing tables use it:** each former enum column becomes
`<name>_code_value_id UUID FK code_value` (validated to belong to the correct `code_list`
via a composite FK or a service/trigger check on `code_list.list_key`). The UI reads the
list's active values for comboboxes; the API validates the submitted value against them.

**Seeded system code lists (predefined values, per recommendation):**

| list_key | Seeded values (code) | Used by |
|---|---|---|
| `account_type` | bank, credit_card, investment, cash, loan | account.account_type |
| `partner_type` | person, supplier, employer, other | partner.partner_type |
| `txn_status` | pending, cleared, reconciled | transaction.status |
| `txn_direction` | debit, credit | transaction.direction |
| `flow_type` | income, expense | cash_flow_item.flow_type, budget_line.direction |
| `cfi_status` | open, partially_paid, settled | cash_flow_item.status |
| `frequency_type` | weekly, monthly_nth_day, monthly_last_bday, monthly_last_day, yearly, quarterly | recurrence_profile.frequency_type, installment_plan.frequency |
| `business_day_rule` | none, prev_bday, next_bday | recurrence_profile.business_day_rule |
| `asset_type` | stock, etf, crypto, asset | investment_holding.asset_type |
| `valuation_source` | manual, api | valuation_history.source |
| `rate_source` | manual, api, import | currency_rate.source |
| `installment_status` | due, paid, overdue | installment_schedule.status |
| `import_status` | uploaded, parsed, previewed, committed, failed | document_import.status |
| `mapping_status` | matched, new, unmapped | document_import_row.mapping_status |
| `auth_type` | none, api_key, oauth, basic | integration_endpoint.auth_type |
| `llm_kind` | openai, azure, anthropic, ollama, custom | llm_provider.kind |
| `notification_type` | recurring_due, budget_overrun, installment_due, loan_due, valuation_updated | notification.type |
| `notification_channel` | in_app, email | notification.channel |
| `notification_status` | pending, sent, read | notification.status |
| `outbox_status` | pending, published, failed | event_outbox.status |
| `audit_operation` | create, update, delete, restore | audit_log.operation |
| `source_channel` | ui, api, import, job | audit_log.source_channel |
| `config_value_type` | bool, string, int, json | app_config.value_type |

> Note: hierarchy **level** fields (beneficiary 1–2, expense_category 1–3) remain integer
> constraints, not code lists, since they are structural. Reporting `v_*` views may resolve
> code_value labels for readability.

---

## Security & tenancy

### household
Base columns. Represents a workspace/family unit.

### app_user
| Column | Type | Notes |
|---|---|---|
| uuid | UUID PK | equals Keycloak subject (sub) |
| mnemonic_id | VARCHAR(20) | `USR-00001` |
| name | VARCHAR(120) | display name |
| email | VARCHAR(255) | |
| default_household_id | UUID FK household | |
| base_currency | CHAR(3) FK currency | user reporting currency |
| + base cols | | |

### role
Base columns. Seeded: Owner, Editor, Viewer.

### user_role
| Column | Type | Notes |
|---|---|---|
| uuid | UUID PK | |
| user_id | UUID FK app_user | |
| role_id | UUID FK role | |
| household_id | UUID FK household | scope of the grant |

---

## Config / meta (global)

### app_config
| Column | Type | Notes |
|---|---|---|
| key | VARCHAR(120) PK | e.g. `llm.master_enabled` |
| value | JSONB | |
| value_type_cv_id | UUID FK code_value | list_key `config_value_type` |
| description | TEXT | |
| updated_at/by | | |

**Seeded keys:** `llm.master_enabled`, `smtp.enabled`, `smtp.config_ref`,
`scheduler.fx_refresh.cron`, `scheduler.valuation_refresh.cron`,
`scheduler.recurring_reminder.cron`, `sql_console.enabled`, `sql_console.row_limit`,
`sql_console.timeout_ms`, `default_base_currency`, `import.dedup_window_days`,
`notifications.channels`.

### id_sequence
| Column | Type | Notes |
|---|---|---|
| prefix | VARCHAR(3) PK | e.g. `TRN`, `PRT` |
| entity_type | VARCHAR(60) | logical entity |
| pad_width | SMALLINT | e.g. 10 for TRN, 5 for PRT |
| current_seq | BIGINT | last used number; resets when a new prefix defined |
| updated_at | TIMESTAMPTZ | |

### llm_provider
Base columns +:
| Column | Type | Notes |
|---|---|---|
| kind_cv_id | UUID FK code_value | list_key `llm_kind` |
| base_url | VARCHAR(500) | |
| model | VARCHAR(120) | |
| credentials_ref | VARCHAR(200) | secret reference (not raw) |
| enabled | BOOLEAN | central disable |
| params | JSONB | temperature, max_tokens, etc. |

### feature_llm_binding
Base columns +:
| Column | Type | Notes |
|---|---|---|
| feature_key | VARCHAR(80) UNIQUE | e.g. `IMPORT_MAPPING`, `BUDGET_RECO` |
| primary_provider_id | UUID FK llm_provider | |
| secondary_provider_id | UUID FK llm_provider NULL | |

### integration_endpoint
Base columns +:
| Column | Type | Notes |
|---|---|---|
| scenario_key | VARCHAR(60) | `FX_RATES`, `STOCK_QUOTE`, `CRYPTO_QUOTE`, `SMTP` |
| provider_name | VARCHAR(120) | |
| base_url | VARCHAR(500) | |
| auth_type_cv_id | UUID FK code_value | list_key `auth_type` |
| credentials_ref | VARCHAR(200) | secret reference |
| config | JSONB | request templates, field maps |
| timeout_ms | INT | |
| priority | SMALLINT | for primary/secondary fallback |
| enabled | BOOLEAN | |

### event_outbox
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | CloudEvents `id` |
| source | VARCHAR(200) | CE `source` |
| type | VARCHAR(200) | CE `type` e.g. `com.pfm.transaction.created` |
| subject | VARCHAR(200) | entity mnemonic/uuid |
| time | TIMESTAMPTZ | CE `time` |
| datacontenttype | VARCHAR(80) | `application/json` |
| dataschema | VARCHAR(300) NULL | |
| data | JSONB | payload/delta |
| traceparent | VARCHAR(120) NULL | correlation |
| status_cv_id | UUID FK code_value | list_key `outbox_status` |
| attempts | INT | |
| last_error | TEXT NULL | |
| published_at | TIMESTAMPTZ NULL | |

### audit_log
| Column | Type | Notes |
|---|---|---|
| uuid | UUID PK | |
| entity_type | VARCHAR(60) | |
| entity_uuid | UUID | |
| entity_mnemonic | VARCHAR(20) | |
| operation_cv_id | UUID FK code_value | list_key `audit_operation` |
| before | JSONB NULL | |
| after | JSONB NULL | |
| changed_by | UUID FK app_user | |
| changed_at | TIMESTAMPTZ | |
| correlation_id | UUID NULL | links to event_outbox.id |
| source_channel_cv_id | UUID FK code_value | list_key `source_channel` |

---

## Currency

### currency
| Column | Type | Notes |
|---|---|---|
| code | CHAR(3) PK | ISO 4217 |
| symbol | VARCHAR(8) | |
| decimals | SMALLINT | |
| name | VARCHAR(120) | |

### currency_rate
Base columns +:
| Column | Type | Notes |
|---|---|---|
| base_ccy | CHAR(3) FK currency | |
| quote_ccy | CHAR(3) FK currency | |
| rate | NUMERIC(18,8) | |
| begin_date | DATE | validity start (inclusive) |
| end_date | DATE | validity end (exclusive); open-ended entries use `9999-12-31` |
| source_cv_id | UUID FK code_value | list_key `rate_source` |
| EXCLUDE overlapping [begin_date, end_date) per (base_ccy, quote_ccy) | | no overlaps (see note) |

> **Validity-period lookup:** the FX service selects the rate where
> `begin_date <= lookup_date < end_date` for the `(base_ccy, quote_ccy)` pair. Users maintain
> contiguous, non-overlapping periods and keep an open-ended entry (`end_date = 9999-12-31`)
> so a valid rate always exists. Overlap is prevented by a PostgreSQL exclusion constraint
> (`btree_gist` on `base_ccy, quote_ccy` + `daterange(begin_date, end_date)`). If no period
> matches (misconfiguration), the service falls back to the closest period and flags a warning.
> CSV/XLSX uploads and the public-source pull populate these periods.

---

## Core financial

> **Enum→FK convention:** columns below named `*_cv_id` are FKs to `code_value`
> constrained to a specific `code_list.list_key` (shown in Notes). They drive value helps
> and validation (Decision #23).

### account
Base columns +:
| Column | Type | Notes |
|---|---|---|
| account_type_cv_id | UUID FK code_value | list_key `account_type` |
| currency | CHAR(3) FK currency | |
| opening_balance | NUMERIC(18,4) | |
| opening_balance_date | DATE | |
| institution | VARCHAR(120) | |
| is_active | BOOLEAN | |

### partner
Base columns +:
| Column | Type | Notes |
|---|---|---|
| partner_type_cv_id | UUID FK code_value | list_key `partner_type` |
| mnemonic_id | `PRT-00001` | |

### beneficiary  (2-level hierarchy)
Base columns +:
| Column | Type | Notes |
|---|---|---|
| parent_id | UUID FK beneficiary NULL | level 1 has null parent |
| level | SMALLINT | 1 or 2 (enforced) |
| mnemonic_id | `BEN-00001` | |

### expense_category  (3-level hierarchy)
Base columns +:
| Column | Type | Notes |
|---|---|---|
| parent_id | UUID FK expense_category NULL | |
| level | SMALLINT | 1..3 (enforced) |
| mnemonic_id | `EC-00001` | |

### recurrence_profile
Base columns +:
| Column | Type | Notes |
|---|---|---|
| frequency_type_cv_id | UUID FK code_value | list_key `frequency_type` |
| config | JSONB | e.g. {nth:5} or {weekday:MON} |
| start_date | DATE | |
| end_date | DATE NULL | |
| business_day_rule_cv_id | UUID FK code_value | list_key `business_day_rule` |
| holiday_calendar_id | UUID FK holiday_calendar NULL | |

### holiday_calendar
Base columns (name e.g. "UAE 2025"). 

### holiday_calendar_day
| Column | Type | Notes |
|---|---|---|
| uuid | UUID PK | |
| calendar_id | UUID FK holiday_calendar | |
| holiday_date | DATE | |
| label | VARCHAR(120) | |

### cash_flow_item  (was "expense_item"; unifies income & expense)
Base columns +:
| Column | Type | Notes |
|---|---|---|
| flow_type_cv_id | UUID FK code_value | list_key `flow_type` |
| expense_category_id | UUID FK expense_category | authoritative category (Policy 1) |
| recurrence_profile_id | UUID FK recurrence_profile NULL | |
| expected_amount | NUMERIC(18,4) NULL | |
| currency | CHAR(3) FK currency | |
| status_cv_id | UUID FK code_value | list_key `cfi_status` |
| mnemonic_id | `CFI-00001` | |

### transaction
Base columns +:
| Column | Type | Notes |
|---|---|---|
| account_id | UUID FK account | |
| txn_date | DATE | value date |
| booking_date | DATE NULL | |
| amount | NUMERIC(18,4) | signed by direction |
| currency | CHAR(3) FK currency | |
| direction_cv_id | UUID FK code_value | list_key `txn_direction` |
| partner_id | UUID FK partner NULL | |
| beneficiary_id | UUID FK beneficiary NULL | when not split |
| expense_category_id | UUID FK expense_category NULL | inherited from item if item-linked (Policy 1) |
| cash_flow_item_id | UUID FK cash_flow_item NULL | |
| expense_item_seq_no | INT NULL | per item; auto-assigned, editable |
| transfer_group_id | UUID FK transfer_group NULL | |
| installment_plan_id | UUID FK installment_plan NULL | |
| source_document_id | UUID FK document_import NULL | |
| is_split | BOOLEAN | if true, see transaction_split |
| status_cv_id | UUID FK code_value | list_key `txn_status` |
| note | TEXT | import note incl. filename |
| mnemonic_id | `TRN-0000000001` | |
| UNIQUE(cash_flow_item_id, expense_item_seq_no) | | when both not null |

> **Policy 1 constraint:** if `cash_flow_item_id` is set, `expense_category_id` must equal
> the item's category (enforced by service + DB trigger); and `is_split` must be false.

### transaction_split
| Column | Type | Notes |
|---|---|---|
| uuid | UUID PK | |
| transaction_id | UUID FK transaction | |
| expense_category_id | UUID FK expense_category | |
| beneficiary_id | UUID FK beneficiary NULL | |
| amount | NUMERIC(18,4) | sum must equal parent amount |

> Disallowed when the parent transaction is item-linked (Decision #16).

### transfer_group
Base columns +:
| Column | Type | Notes |
|---|---|---|
| from_txn_id | UUID FK transaction | debit leg |
| to_txn_id | UUID FK transaction | credit leg |
| from_amount | NUMERIC(18,4) | source currency amount |
| to_amount | NUMERIC(18,4) | target currency amount |
| fx_rate | NUMERIC(18,8) NULL | derived; for audit |

### installment_plan
Base columns +:
| Column | Type | Notes |
|---|---|---|
| account_id | UUID FK account | usually a credit_card |
| total_amount | NUMERIC(18,4) | |
| installment_count | INT | |
| start_date | DATE | |
| frequency_cv_id | UUID FK code_value | list_key `frequency_type` |
| interest_rate | NUMERIC(9,4) NULL | |
| currency | CHAR(3) FK currency | |
| mnemonic_id | `INS-00001` | |

### installment_schedule
| Column | Type | Notes |
|---|---|---|
| uuid | UUID PK | |
| plan_id | UUID FK installment_plan | |
| seq | INT | 1..count |
| due_date | DATE | |
| amount | NUMERIC(18,4) | |
| status_cv_id | UUID FK code_value | list_key `installment_status` |
| linked_txn_id | UUID FK transaction NULL | |

### loan (liability)
Base columns +:
| Column | Type | Notes |
|---|---|---|
| account_id | UUID FK account NULL | linked loan account |
| principal | NUMERIC(18,4) | |
| interest_rate | NUMERIC(9,4) | annual % |
| term_months | INT | |
| start_date | DATE | |
| currency | CHAR(3) FK currency | |
| mnemonic_id | `LON-00001` | |

### amortization_schedule
| Column | Type | Notes |
|---|---|---|
| uuid | UUID PK | |
| loan_id | UUID FK loan | |
| period | INT | |
| due_date | DATE | |
| principal_portion | NUMERIC(18,4) | |
| interest_portion | NUMERIC(18,4) | |
| balance | NUMERIC(18,4) | remaining |
| linked_txn_id | UUID FK transaction NULL | |

### goal
Base columns +:
| Column | Type | Notes |
|---|---|---|
| target_amount | NUMERIC(18,4) | |
| currency | CHAR(3) FK currency | |
| target_date | DATE NULL | |
| linked_account_id | UUID FK account NULL | source of progress |
| mnemonic_id | `GOL-00001` | |

> Progress derived from linked account balance or tagged transactions.

---

## Investments

### investment_holding
Base columns +:
| Column | Type | Notes |
|---|---|---|
| account_id | UUID FK account | investment account |
| symbol | VARCHAR(40) | ticker / coin id |
| asset_type_cv_id | UUID FK code_value | list_key `asset_type` |
| quantity | NUMERIC(24,8) | |
| entry_value | NUMERIC(18,4) | user input at entry |
| entry_date | DATE | |
| current_value_cache | NUMERIC(18,4) NULL | mirror of latest valuation_history |
| currency | CHAR(3) FK currency | |
| mnemonic_id | `INV-00001` | |

### valuation_history
| Column | Type | Notes |
|---|---|---|
| uuid | UUID PK | |
| holding_id | UUID FK investment_holding | |
| as_of_date | DATE | |
| value | NUMERIC(18,4) | |
| source_cv_id | UUID FK code_value | list_key `valuation_source` |
| created_by | UUID FK app_user | |
| created_at | TIMESTAMPTZ | |
| UNIQUE(holding_id, as_of_date) | | |

> Source of truth for current value; `current_value_cache` mirrors the latest row (Decision #9).

---

## Budgeting

### budget  (view)
Base columns +:
| Column | Type | Notes |
|---|---|---|
| period_start | DATE | |
| period_end | DATE | |
| base_currency | CHAR(3) FK currency | |
| mnemonic_id | `BUD-00001` | |

### budget_line
| Column | Type | Notes |
|---|---|---|
| uuid | UUID PK | |
| budget_id | UUID FK budget | |
| cash_flow_item_id | UUID FK cash_flow_item NULL | selectable recurring items |
| expense_category_id | UUID FK expense_category NULL | category-level line |
| direction_cv_id | UUID FK code_value | list_key `flow_type` (income/expense) |
| expected_amount | NUMERIC(18,4) | |

### budget_actual_snapshot  (optional cache)
| Column | Type | Notes |
|---|---|---|
| uuid | UUID PK | |
| budget_id | UUID FK budget | |
| budget_line_id | UUID FK budget_line | |
| actual_amount | NUMERIC(18,4) | |
| computed_at | TIMESTAMPTZ | |

---

## Import & attachments

### document_import
Base columns +:
| Column | Type | Notes |
|---|---|---|
| original_filename | VARCHAR(300) | as uploaded |
| storage_key | VARCHAR(400) | MinIO object key |
| mime | VARCHAR(120) | |
| status_cv_id | UUID FK code_value | list_key `import_status` |
| uploaded_by | UUID FK app_user | |
| uploaded_at | TIMESTAMPTZ | |
| parse_summary | JSONB | row counts, warnings |
| mnemonic_id | `DOC-00001` | |

### document_import_row
| Column | Type | Notes |
|---|---|---|
| uuid | UUID PK | |
| import_id | UUID FK document_import | |
| raw_data | JSONB | extracted fields |
| mapped_values | JSONB | proposed partner/category/etc. |
| mapping_status_cv_id | UUID FK code_value | list_key `mapping_status` |
| dedup_hash | VARCHAR(64) | date+amount+partner hash |
| target_txn_id | UUID FK transaction NULL | set on commit |

### attachment  (polymorphic)
| Column | Type | Notes |
|---|---|---|
| uuid | UUID PK | |
| entity_type | VARCHAR(60) | |
| entity_uuid | UUID | |
| storage_key | VARCHAR(400) | MinIO key |
| filename | VARCHAR(300) | |
| mime | VARCHAR(120) | |
| uploaded_by | UUID FK app_user | |
| uploaded_at | TIMESTAMPTZ | |

---

## Automation & tagging

### categorization_rule
Base columns +:
| Column | Type | Notes |
|---|---|---|
| priority | INT | lower runs first |
| conditions | JSONB | e.g. {partner:"X", amount_lt:100} |
| actions | JSONB | {set_category, set_partner, set_beneficiary} |
| enabled | BOOLEAN | |
| mnemonic_id | `RUL-00001` | |

### tag
Base columns (name + color in description/params).

### entity_tag  (polymorphic)
| Column | Type | Notes |
|---|---|---|
| uuid | UUID PK | |
| tag_id | UUID FK tag | |
| entity_type | VARCHAR(60) | |
| entity_uuid | UUID | |
| UNIQUE(tag_id, entity_type, entity_uuid) | | |

---

## Notifications

### notification
| Column | Type | Notes |
|---|---|---|
| uuid | UUID PK | |
| user_id | UUID FK app_user | |
| type_cv_id | UUID FK code_value | list_key `notification_type` |
| subject | VARCHAR(200) | |
| body | TEXT | |
| channel_cv_id | UUID FK code_value | list_key `notification_channel` |
| status_cv_id | UUID FK code_value | list_key `notification_status` |
| related_entity_type | VARCHAR(60) NULL | |
| related_entity_uuid | UUID NULL | |
| scheduled_for | TIMESTAMPTZ NULL | |
| sent_at | TIMESTAMPTZ NULL | |
| created_at | TIMESTAMPTZ | |

---

## Reporting views (read-only, for SQL console & prebuilt reports)

- `v_transaction_enriched` — transaction joined with account, partner, beneficiary,
  category (levels 1–3), item, tags, and the **reporting-currency** converted amount using
  the validity-period FX rate (`begin_date <= txn_date < end_date`).
- `v_account_balance_daily` — daily running balance per account (for cash-position graph).
- `v_networth_asof` — assets − liabilities per as-of date, per currency + reporting-currency total.
- `v_budget_vs_actual` — budget lines vs. computed actuals.
- `v_installment_status`, `v_loan_status` — outstanding vs. paid.

The SQL console connects with a **read-only role** limited to these views, with
`statement_timeout` and forced `LIMIT` (Decision #10).

---

## Key indexes

- `transaction(account_id, txn_date)`, `transaction(cash_flow_item_id)`,
  `transaction(partner_id)`, `transaction(beneficiary_id)`, `transaction(transfer_group_id)`.
- `currency_rate` GiST exclusion on `(base_ccy, quote_ccy, daterange(begin_date, end_date))`
  + btree on `(base_ccy, quote_ccy, begin_date)` for validity-period lookup.
- `valuation_history(holding_id, as_of_date)`.
- `event_outbox(status_cv_id)` for the publisher loop.
- `code_value(code_list_id, is_active)` for value-help lookups.
- `entity_tag(entity_type, entity_uuid)`, `attachment(entity_type, entity_uuid)`.
- Partial indexes excluding soft-deleted rows (`WHERE deleted_at IS NULL`).
