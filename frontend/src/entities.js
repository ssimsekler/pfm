// Central, metadata-driven entity registry (ADR #32).
//
// Each entity defines:
//   - title:    display name
//   - path:     list/CRUD base path (e.g. "/v1/partners")
//   - idField:  primary key field returned by the API (default "uuid")
//   - readOnly: if true, no create/edit/delete (list only)
//   - columns:  [{ key, label, render? }] for the list table
//   - fields:   [{ name, label, type, required?, ... }] for the create/edit form
//   - hasSplits: transactions only — enables the split editor
//
// Field types: text | textarea | number | date | boolean | select | codeValue | ref
//   - select:    static options via `options: [{value,label}]`
//   - codeValue: dropdown from a code list via `listKey` (value = code_value.uuid)
//   - ref:       dropdown from another entity via `refEntity`; optional
//                `refLabel` (default "name") and `refValue` (default "uuid")
//
// Consumed by ComboField / EntityForm / EntityManager / SplitEditor.

export const CURRENCY_FIELD = {
  name: "currency",
  label: "Currency",
  type: "ref",
  refEntity: "currencies",
  refValue: "code",
  refLabel: "code",
};

export const ENTITIES = {
  // ---------------------------------------------------------------- Reference
  currencies: {
    title: "Currencies",
    path: "/v1/currencies",
    idField: "code",
    readOnly: true, // backend exposes currencies read-only (ADR #33 note)
    columns: [
      { key: "code", label: "Code" },
      { key: "name", label: "Name" },
      { key: "symbol", label: "Symbol" },
      { key: "decimals", label: "Decimals" },
    ],
    fields: [],
  },

  countries: {
    title: "Countries",
    path: "/v1/countries",
    columns: [
      { key: "name", label: "Name" },
      { key: "iso2", label: "ISO2" },
      { key: "iso3", label: "ISO3" },
      { key: "default_currency", label: "Default Ccy" },
      { key: "mnemonic_id", label: "ID" },
    ],
    fields: [
      { name: "name", label: "Name", type: "text", required: true },
      { name: "iso2", label: "ISO2", type: "text", required: true },
      { name: "iso3", label: "ISO3", type: "text", required: true },
      { name: "default_currency", label: "Default Currency", type: "ref", refEntity: "currencies", refValue: "code", refLabel: "code" },
      { name: "description", label: "Description", type: "textarea" },
    ],
  },

  institutions: {
    title: "Institutions",
    path: "/v1/institutions",
    columns: [
      { key: "name", label: "Name" },
      { key: "swift_bic", label: "SWIFT/BIC" },
      { key: "website", label: "Website" },
      { key: "mnemonic_id", label: "ID" },
    ],
    fields: [
      { name: "name", label: "Name", type: "text", required: true },
      { name: "country_id", label: "Country", type: "ref", refEntity: "countries", required: true },
      { name: "institution_type_cv_id", label: "Type", type: "codeValue", listKey: "institution_type" },
      { name: "swift_bic", label: "SWIFT/BIC", type: "text" },
      { name: "website", label: "Website", type: "text" },
      { name: "description", label: "Description", type: "textarea" },
    ],
  },

  // ------------------------------------------------------------------- Master
  accounts: {
    title: "Accounts",
    path: "/v1/accounts",
    filterFields: [
      { name: "currency", label: "Currency", kind: "ref", refEntity: "currencies", refValue: "code", refLabel: "code" },
      { name: "account_type_cv_id", label: "Type", kind: "codeValue", listKey: "account_type" },
      { name: "institution_id", label: "Institution", kind: "ref", refEntity: "institutions" },
    ],
    columns: [
      { key: "name", label: "Name" },
      { key: "mnemonic_id", label: "ID" },
      { key: "currency", label: "Currency" },
      { key: "opening_balance", label: "Opening Balance", money: true },
      { key: "is_active", label: "Active" },
    ],
    fields: [
      { name: "name", label: "Name", type: "text", required: true },
      { name: "account_type_cv_id", label: "Type", type: "codeValue", listKey: "account_type", required: true },
      { ...CURRENCY_FIELD, required: true },
      { name: "opening_balance", label: "Opening Balance", type: "number" },
      { name: "opening_balance_date", label: "Opening Balance Date", type: "date" },
      { name: "institution_id", label: "Institution", type: "ref", refEntity: "institutions", required: true },
      { name: "is_active", label: "Active", type: "boolean" },
      // Item 14: bank/account identifiers (variable length; digits/dashes; IBAN
      // alphanumeric). Credit-card number applies to credit-card accounts.
      { name: "iban", label: "IBAN", type: "text", section: "Bank / identifiers", help: "Alphanumeric; spaces allowed." },
      { name: "card_number", label: "Card Number", type: "text", section: "Bank / identifiers", help: "For credit-card accounts (digits/dashes)." },
      { name: "bank_sort_code", label: "Bank Sort Code", type: "text", section: "Bank / identifiers", help: "Digits/dashes." },
      { name: "bank_account_number", label: "Bank Account Number", type: "text", section: "Bank / identifiers", help: "Digits/dashes." },
      { name: "building_society_number", label: "Building Society Number", type: "text", section: "Bank / identifiers", help: "Digits/dashes." },
      { name: "routing_number", label: "Routing Number", type: "text", section: "Bank / identifiers", help: "US routing number (digits)." },
      { name: "description", label: "Description", type: "textarea" },
    ],
  },

  partners: {
    title: "Partners",
    path: "/v1/partners",
    filterFields: [
      { name: "partner_type_cv_id", label: "Type", kind: "codeValue", listKey: "partner_type" },
      { name: "country_id", label: "Country", kind: "ref", refEntity: "countries" },
    ],
    columns: [
      { key: "name", label: "Name" },
      { key: "mnemonic_id", label: "ID" },
      { key: "description", label: "Description" },
    ],
    fields: [
      { name: "name", label: "Name", type: "text", required: true },
      { name: "partner_type_cv_id", label: "Type", type: "codeValue", listKey: "partner_type" },
      { name: "country_id", label: "Country", type: "ref", refEntity: "countries" },
      { name: "description", label: "Description", type: "textarea" },
    ],
  },

  beneficiaries: {
    title: "Beneficiaries",
    path: "/v1/beneficiaries",
    columns: [
      { key: "name", label: "Name" },
      { key: "mnemonic_id", label: "ID" },
      { key: "level", label: "Level" },
    ],
    fields: [
      { name: "name", label: "Name", type: "text", required: true },
      { name: "parent_id", label: "Parent", type: "ref", refEntity: "beneficiaries", help: "Level is derived automatically from the parent (top-level = 1)." },
      { name: "description", label: "Description", type: "textarea" },
    ],
  },

  "expense-categories": {
    title: "Expense Categories",
    path: "/v1/expense-categories",
    columns: [
      { key: "name", label: "Name" },
      { key: "mnemonic_id", label: "ID" },
      { key: "level", label: "Level" },
    ],
    fields: [
      { name: "name", label: "Name", type: "text", required: true },
      { name: "parent_id", label: "Parent", type: "ref", refEntity: "expense-categories", help: "Level is derived automatically from the parent (top-level = 1)." },
      { name: "description", label: "Description", type: "textarea" },
    ],
  },

  "cash-flow-items": {
    title: "Cash Flow Items",
    path: "/v1/cash-flow-items",
    filterFields: [
      { name: "flow_type_cv_id", label: "Flow Type", kind: "codeValue", listKey: "flow_type" },
      { name: "expense_category_id", label: "Category", kind: "ref", refEntity: "expense-categories" },
      { name: "status_cv_id", label: "Status", kind: "codeValue", listKey: "cfi_status" },
    ],
    columns: [
      { key: "name", label: "Name" },
      { key: "mnemonic_id", label: "ID" },
      { key: "expected_amount", label: "Expected", money: true },
      { key: "currency", label: "Currency" },
    ],
    fields: [
      { name: "name", label: "Name", type: "text", required: true },
      { name: "flow_type_cv_id", label: "Flow Type", type: "codeValue", listKey: "flow_type" },
      { name: "expense_category_id", label: "Category", type: "ref", refEntity: "expense-categories", required: true },
      { name: "expected_amount", label: "Expected Amount", type: "number" },
      { ...CURRENCY_FIELD },
      { name: "recurrence_profile_id", label: "Recurrence Profile", type: "ref", refEntity: "recurrence-profiles", help: "Link a schedule to list this item under Recurring." },
      { name: "status_cv_id", label: "Status", type: "codeValue", listKey: "cfi_status" },
      { name: "description", label: "Description", type: "textarea" },
    ],
  },

  investments: {
    title: "Investments",
    path: "/v1/investments",
    columns: [
      { key: "name", label: "Name" },
      { key: "symbol", label: "Symbol" },
      { key: "quantity", label: "Quantity", highPrecision: true },
      { key: "current_value_cache", label: "Current Value", money: true },
      { key: "currency", label: "Currency" },
    ],
    fields: [
      { name: "name", label: "Name", type: "text", required: true },
      { name: "symbol", label: "Symbol", type: "text", required: true },
      { name: "account_id", label: "Account", type: "ref", refEntity: "accounts", disabled: true, help: "A backing investment account is created automatically." },
      { name: "asset_type_cv_id", label: "Asset Type", type: "codeValue", listKey: "asset_type" },
      { name: "quantity", label: "Quantity", type: "number" },
      { name: "entry_value", label: "Entry Value", type: "number" },
      { name: "entry_date", label: "Entry Date", type: "date" },
      { ...CURRENCY_FIELD },
      { name: "description", label: "Description", type: "textarea" },
    ],
  },

  loans: {
    title: "Loans",
    path: "/v1/loans",
    columns: [
      { key: "name", label: "Name" },
      { key: "mnemonic_id", label: "ID" },
      { key: "principal", label: "Principal", money: true },
      { key: "interest_rate", label: "Rate %" },
      { key: "term_months", label: "Term (mo)" },
      { key: "currency", label: "Currency" },
    ],
    fields: [
      { name: "name", label: "Name", type: "text", required: true },
      { name: "loan_category_cv_id", label: "Category", type: "codeValue", listKey: "loan_category" },
      { name: "account_id", label: "Account", type: "ref", refEntity: "accounts", disabled: true, help: "A backing loan account is created automatically." },
      { name: "principal", label: "Principal", type: "number", required: true },
      { name: "interest_rate", label: "Interest Rate %", type: "number", required: true },
      { name: "term_months", label: "Term (months)", type: "number", required: true },
      { name: "start_date", label: "Start Date", type: "date", required: true },
      { ...CURRENCY_FIELD },
      { name: "description", label: "Description", type: "textarea" },
    ],
  },

  "installment-plans": {
    title: "Installment Plans",
    path: "/v1/installment-plans",
    columns: [
      { key: "name", label: "Name" },
      { key: "mnemonic_id", label: "ID" },
      { key: "total_amount", label: "Total", money: true },
      { key: "installment_count", label: "Count" },
      { key: "currency", label: "Currency" },
    ],
    fields: [
      { name: "name", label: "Name", type: "text", required: true },
      { name: "account_id", label: "Account", type: "ref", refEntity: "accounts" },
      { name: "total_amount", label: "Total Amount", type: "number", required: true },
      { name: "installment_count", label: "Installment Count", type: "number", required: true },
      { name: "start_date", label: "Start Date", type: "date", required: true },
      { name: "frequency_cv_id", label: "Frequency", type: "codeValue", listKey: "frequency_type" },
      { name: "interest_rate", label: "Interest Rate %", type: "number" },
      { ...CURRENCY_FIELD },
      { name: "description", label: "Description", type: "textarea" },
    ],
  },

  goals: {
    title: "Goals",
    path: "/v1/goals",
    columns: [
      { key: "name", label: "Name" },
      { key: "mnemonic_id", label: "ID" },
      { key: "target_amount", label: "Target", money: true },
      { key: "target_date", label: "Target Date", date: true },
      { key: "currency", label: "Currency" },
    ],
    fields: [
      { name: "name", label: "Name", type: "text", required: true },
      { name: "goal_type_cv_id", label: "Goal Type", type: "codeValue", listKey: "goal_type", help: "Save to target, or cap an expense category per period." },
      { name: "target_amount", label: "Target Amount", type: "number", required: true },
      { ...CURRENCY_FIELD },
      { name: "target_date", label: "Target Date", type: "date" },
      // Batch 12: goals are tracked via **goal-tagged transactions** (see the
      // Goal picker on the transaction form), not a linked account.
      // For "cap_expense" goals (e.g. "Keep fuel < 1000/month").
      { name: "expense_category_id", label: "Category (cap)", type: "ref", refEntity: "expense-categories", help: "Category to cap for a 'cap expense' goal." },
      { name: "period", label: "Period (cap)", type: "select", options: [
        { value: "monthly", label: "Monthly" },
        { value: "yearly", label: "Yearly" },
        { value: "total", label: "Total" },
      ], help: "Evaluation window for a 'cap expense' goal." },
      { name: "limit_amount", label: "Limit Amount (cap)", type: "number" },
      { name: "description", label: "Description", type: "textarea" },
    ],
  },

  budgets: {
    title: "Budgets",
    path: "/v1/budgets",
    columns: [
      { key: "name", label: "Name" },
      { key: "mnemonic_id", label: "ID" },
      { key: "period_start", label: "From", date: true },
      { key: "period_end", label: "To", date: true },
      { key: "base_currency", label: "Currency" },
    ],
    fields: [
      { name: "name", label: "Name", type: "text", required: true },
      { name: "period_start", label: "Period Start", type: "date", required: true },
      { name: "period_end", label: "Period End", type: "date", required: true },
      { name: "base_currency", label: "Base Currency", type: "ref", refEntity: "currencies", refValue: "code", refLabel: "code" },
      { name: "description", label: "Description", type: "textarea" },
    ],
  },

  // ------------------------------------------------------------ Transactional
  transactions: {
    title: "Transactions",
    path: "/v1/transactions",
    hasSplits: true,
    filterFields: [
      { name: "account_id", label: "Account", kind: "ref", refEntity: "accounts" },
      { name: "partner_id", label: "Partner", kind: "ref", refEntity: "partners" },
      { name: "beneficiary_id", label: "Beneficiary", kind: "ref", refEntity: "beneficiaries" },
      { name: "expense_category_id", label: "Category", kind: "ref", refEntity: "expense-categories" },
      { name: "status_cv_id", label: "Status", kind: "codeValue", listKey: "txn_status" },
      { name: "currency", label: "Currency", kind: "ref", refEntity: "currencies", refValue: "code", refLabel: "code" },
      { name: "txn_date", label: "Date", kind: "dateRange", fromParam: "date_from", toParam: "date_to" },
      { name: "amount", label: "Amount", kind: "numberRange", fromParam: "amount_min", toParam: "amount_max" },
    ],
    columns: [
      { key: "name", label: "Name" },
      { key: "txn_date", label: "Date", date: true },
      { key: "amount", label: "Amount", money: true },
      { key: "currency", label: "Currency" },
      { key: "is_split", label: "Split" },
      { key: "mnemonic_id", label: "ID" },
    ],
    fields: [
      { name: "name", label: "Name", type: "text", required: true },
      { name: "account_id", label: "Account", type: "ref", refEntity: "accounts", required: true },
      // Read-only link shown when the transaction was created from a cash-flow item
      // (Policy 1). Always disabled — set only via the item's "Create transaction" action.
      { name: "cash_flow_item_id", label: "Cash Flow Item", type: "ref", refEntity: "cash-flow-items", disabled: true, help: "Set when created from a cash-flow item; category & direction are inherited and locked (Policy 1)." },
      { name: "txn_date", label: "Transaction Date", type: "date", required: true },
      { name: "booking_date", label: "Booking Date", type: "date" },
      { name: "amount", label: "Amount", type: "number", required: true },
      { ...CURRENCY_FIELD, required: true },
      // Category & direction are locked when a cash-flow item is linked (Policy 1).
      { name: "direction_cv_id", label: "Direction", type: "codeValue", listKey: "txn_direction", required: true, lockWhenItemLinked: true },
      { name: "partner_id", label: "Partner", type: "ref", refEntity: "partners" },
      { name: "beneficiary_id", label: "Beneficiary", type: "ref", refEntity: "beneficiaries" },
      { name: "expense_category_id", label: "Category", type: "ref", refEntity: "expense-categories", lockWhenItemLinked: true },
      { name: "status_cv_id", label: "Status", type: "codeValue", listKey: "txn_status" },
      // Batch 12: tag a transaction to a goal (feeds save-to-target progress).
      { name: "goal_id", label: "Goal", type: "ref", refEntity: "goals", help: "Link this transaction to a savings goal (optional)." },
      { name: "note", label: "Note", type: "textarea" },
    ],
  },

  // -------------------------------------------------------------------- Config
  "llm-providers": {
    title: "LLM Providers",
    path: "/v1/llm-providers",
    columns: [
      { key: "name", label: "Name" },
      { key: "model", label: "Model" },
      { key: "base_url", label: "Base URL" },
      { key: "enabled", label: "Enabled" },
    ],
    fields: [
      { name: "name", label: "Name", type: "text", required: true },
      { name: "kind_cv_id", label: "Kind", type: "codeValue", listKey: "llm_kind" },
      { name: "base_url", label: "Base URL", type: "text" },
      { name: "model", label: "Model", type: "text" },
      { name: "credentials_ref", label: "Credentials", type: "credentialRef", category: "llm_provider", help: "Pick an LLM Provider Key from the Credentials Store." },
      { name: "priority", label: "Priority", type: "number", help: "Lower is tried first; the gateway fails over to the next enabled provider (New-2)." },
      { name: "enabled", label: "Enabled", type: "boolean" },
      { name: "description", label: "Description", type: "textarea" },
    ],
  },

  "integration-endpoints": {
    title: "Integration Endpoints",
    path: "/v1/integration-endpoints",
    columns: [
      { key: "scenario_key", label: "Scenario" },
      { key: "provider_name", label: "Provider" },
      { key: "base_url", label: "Base URL" },
      { key: "enabled", label: "Enabled" },
    ],
    fields: [
      { name: "name", label: "Name", type: "text", required: true },
      { name: "scenario_key", label: "Scenario Key", type: "text", required: true },
      { name: "provider_name", label: "Provider Name", type: "text" },
      { name: "base_url", label: "Base URL", type: "text" },
      { name: "auth_type_cv_id", label: "Auth Type", type: "codeValue", listKey: "auth_type" },
      { name: "credentials_ref", label: "Credentials", type: "credentialRef", help: "Pick a credential (API Key, Basic, Bearer, OAuth2) from the Credentials Store." },
      { name: "timeout_ms", label: "Timeout (ms)", type: "number" },
      { name: "priority", label: "Priority", type: "number" },
      { name: "enabled", label: "Enabled", type: "boolean" },
      { name: "description", label: "Description", type: "textarea" },
    ],
  },

  "categorization-rules": {
    title: "Categorization Rules",
    path: "/v1/categorization-rules",
    columns: [
      { key: "name", label: "Name" },
      { key: "priority", label: "Priority" },
      { key: "enabled", label: "Enabled" },
      { key: "mnemonic_id", label: "ID" },
    ],
    fields: [
      { name: "name", label: "Name", type: "text", required: true },
      { name: "priority", label: "Priority", type: "number" },
      { name: "conditions", label: "Conditions (JSON)", type: "json" },
      { name: "actions", label: "Actions (JSON)", type: "json" },
      { name: "enabled", label: "Enabled", type: "boolean" },
      { name: "description", label: "Description", type: "textarea" },
    ],
  },

  "currency-rates": {
    title: "Currency Rates",
    path: "/v1/currency-rates",
    columns: [
      { key: "base_ccy", label: "Base" },
      { key: "quote_ccy", label: "Quote" },
      { key: "rate", label: "Rate", highPrecision: true },
      { key: "begin_date", label: "From", date: true },
      { key: "end_date", label: "To", date: true },
    ],
    fields: [
      { name: "name", label: "Name", type: "text", required: true },
      { name: "base_ccy", label: "Base Currency", type: "ref", refEntity: "currencies", refValue: "code", refLabel: "code", required: true },
      { name: "quote_ccy", label: "Quote Currency", type: "ref", refEntity: "currencies", refValue: "code", refLabel: "code", required: true },
      { name: "rate", label: "Rate", type: "number", required: true },
      { name: "begin_date", label: "Begin Date", type: "date", required: true },
      { name: "end_date", label: "End Date", type: "date", required: true },
      { name: "description", label: "Description", type: "textarea" },
    ],
  },

  "holiday-calendars": {
    title: "Holiday Calendars",
    path: "/v1/holiday-calendars",
    columns: [
      { key: "name", label: "Name" },
      { key: "mnemonic_id", label: "ID" },
      { key: "description", label: "Description" },
    ],
    fields: [
      { name: "name", label: "Name", type: "text", required: true },
      { name: "description", label: "Description", type: "textarea" },
    ],
  },

  "recurrence-profiles": {
    title: "Recurrence Profiles",
    path: "/v1/recurrence-profiles",
    columns: [
      { key: "name", label: "Name" },
      { key: "mnemonic_id", label: "ID" },
      { key: "start_date", label: "Start" },
      { key: "end_date", label: "End" },
    ],
    fields: [
      { name: "name", label: "Name", type: "text", required: true },
      { name: "frequency_type_cv_id", label: "Frequency", type: "codeValue", listKey: "frequency_type" },
      { name: "start_date", label: "Start Date", type: "date", required: true },
      { name: "end_date", label: "End Date", type: "date" },
      { name: "business_day_rule_cv_id", label: "Business Day Rule", type: "codeValue", listKey: "business_day_rule" },
      { name: "holiday_calendar_id", label: "Holiday Calendar", type: "ref", refEntity: "holiday-calendars" },
      { name: "config", label: "Config (JSON)", type: "json", help: "e.g. {\"nth\":5} or {\"weekday\":\"MON\"}" },
      { name: "description", label: "Description", type: "textarea" },
    ],
  },
};

export function getEntity(key) {
  return ENTITIES[key] || null;
}
