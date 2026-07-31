"""Seed data definitions: system code lists, currencies, countries, roles.

Applied idempotently at startup (Phase 1). See docs/ERD.md and Decision #23/#28.
"""

# list_key -> list of (code, label, is_default)
SYSTEM_CODE_LISTS: dict[str, list[tuple[str, str, bool]]] = {
    "account_type": [
        ("bank", "Bank Account", True),
        ("credit_card", "Credit Card", False),
        ("investment", "Investment Account", False),
        ("cash", "Cash", False),
        ("loan", "Loan Account", False),
    ],
    "partner_type": [
        ("person", "Person", False),
        ("supplier", "Supplier", True),
        ("employer", "Employer", False),
        ("other", "Other", False),
    ],
    "txn_status": [
        ("pending", "Pending", True),
        ("cleared", "Cleared", False),
        ("reconciled", "Reconciled", False),
    ],
    "txn_direction": [
        ("debit", "Debit", True),
        ("credit", "Credit", False),
    ],
    "flow_type": [
        ("expense", "Expense", True),
        ("income", "Income", False),
    ],
    "cfi_status": [
        ("open", "Open", True),
        ("partially_paid", "Partially Paid", False),
        ("settled", "Settled", False),
    ],
    "frequency_type": [
        ("weekly", "Weekly", False),
        ("monthly_nth_day", "Monthly (nth day)", True),
        ("monthly_last_bday", "Monthly (last business day)", False),
        ("monthly_last_day", "Monthly (last day)", False),
        ("quarterly", "Quarterly", False),
        ("yearly", "Yearly", False),
    ],
    "business_day_rule": [
        ("none", "None", True),
        ("prev_bday", "Previous business day", False),
        ("next_bday", "Next business day", False),
    ],
    "asset_type": [
        ("stock", "Stock", True),
        ("etf", "ETF", False),
        ("crypto", "Crypto", False),
        ("asset", "Other Asset", False),
    ],
    "valuation_source": [
        ("manual", "Manual", True),
        ("api", "API", False),
    ],
    "rate_source": [
        ("manual", "Manual", True),
        ("api", "API", False),
        ("import", "Import", False),
    ],
    "installment_status": [
        ("due", "Due", True),
        ("paid", "Paid", False),
        ("overdue", "Overdue", False),
    ],
    "import_status": [
        ("uploaded", "Uploaded", True),
        ("parsed", "Parsed", False),
        ("previewed", "Previewed", False),
        ("committed", "Committed", False),
        ("failed", "Failed", False),
    ],
    "mapping_status": [
        ("matched", "Matched", False),
        ("new", "New", False),
        ("unmapped", "Unmapped", True),
    ],
    "auth_type": [
        ("none", "None", True),
        ("api_key", "API Key", False),
        ("oauth", "OAuth", False),
        ("basic", "Basic", False),
    ],
    "llm_kind": [
        ("ollama", "Ollama (local)", True),
        ("openai", "OpenAI", False),
        ("azure", "Azure OpenAI", False),
        ("anthropic", "Anthropic", False),
        ("custom", "Custom", False),
    ],
    "notification_type": [
        ("recurring_due", "Recurring Item Due", False),
        ("budget_overrun", "Budget Overrun", False),
        ("installment_due", "Installment Due", False),
        ("loan_due", "Loan Payment Due", False),
        ("valuation_updated", "Valuation Updated", False),
    ],
    "notification_channel": [
        ("in_app", "In-App", True),
        ("email", "Email", False),
    ],
    "notification_status": [
        ("pending", "Pending", True),
        ("sent", "Sent", False),
        ("read", "Read", False),
    ],
    "outbox_status": [
        ("pending", "Pending", True),
        ("published", "Published", False),
        ("failed", "Failed", False),
    ],
    "audit_operation": [
        ("create", "Create", False),
        ("update", "Update", False),
        ("delete", "Delete", False),
        ("restore", "Restore", False),
    ],
    "source_channel": [
        ("ui", "UI", False),
        ("api", "API", True),
        ("import", "Import", False),
        ("job", "Job", False),
    ],
    "config_value_type": [
        ("string", "String", True),
        ("bool", "Boolean", False),
        ("int", "Integer", False),
        ("json", "JSON", False),
    ],
    "institution_type": [
        ("bank", "Bank", True),
        ("broker", "Broker", False),
        ("card_issuer", "Card Issuer", False),
        ("exchange", "Exchange", False),
        ("other", "Other", False),
    ],
    "loan_category": [
        ("mortgage", "Mortgage", False),
        ("personal", "Personal Loan", True),
        ("car", "Car Loan", False),
        ("student", "Student Loan", False),
        ("business", "Business Loan", False),
        ("other", "Other", False),
    ],
    # Goal evaluation modes (Session 742, Bug 19).
    "goal_type": [
        ("save_to_target", "Save to target", True),
        ("cap_expense", "Cap expense", False),
    ],
}

# code, symbol, decimals, name
CURRENCIES: list[tuple[str, str, int, str]] = [
    ("AED", "د.إ", 2, "UAE Dirham"),
    ("USD", "$", 2, "US Dollar"),
    ("EUR", "€", 2, "Euro"),
    ("GBP", "£", 2, "British Pound"),
    ("INR", "₹", 2, "Indian Rupee"),
    ("TRY", "₺", 2, "Turkish Lira"),
    ("SAR", "﷼", 2, "Saudi Riyal"),
    ("CHF", "CHF", 2, "Swiss Franc"),
    ("JPY", "¥", 0, "Japanese Yen"),
    ("BTC", "₿", 8, "Bitcoin"),
]

# iso2, iso3, name, default_currency
COUNTRIES: list[tuple[str, str, str, str | None]] = [
    ("AE", "ARE", "United Arab Emirates", "AED"),
    ("US", "USA", "United States", "USD"),
    ("GB", "GBR", "United Kingdom", "GBP"),
    ("DE", "DEU", "Germany", "EUR"),
    ("FR", "FRA", "France", "EUR"),
    ("IN", "IND", "India", "INR"),
    ("TR", "TUR", "Türkiye", "TRY"),
    ("SA", "SAU", "Saudi Arabia", "SAR"),
    ("CH", "CHE", "Switzerland", "CHF"),
    ("JP", "JPN", "Japan", "JPY"),
]

# name, description
# Session 815, Item 6: the top role is now named **Admin** (was "Owner"). The
# seeder renames any existing "Owner" role row to "Admin" so grants are preserved.
ROLES: list[tuple[str, str]] = [
    ("Admin", "Full control incl. user administration"),
    ("Editor", "Create/edit financial data"),
    ("Viewer", "Read-only access"),
]

# key, value, value_type, description
APP_CONFIG: list[tuple[str, object, str, str]] = [
    ("llm.master_enabled", False, "bool", "Master switch: enables all LLM features (categorization suggestions, budget commentary). When off, the LLM gateway returns nothing."),
    # Email (Session 815, Item 20): SMTP settings now live in the Credentials Store
    # (category "email"); app_config keeps only the enable flag + a credentials_ref.
    ("email.enabled", False, "bool", "Enable outgoing email"),
    ("email.credentials_ref", "", "string", "Credentials Store entry (Email category) for SMTP settings"),
    # Display-format defaults (Session 815, Item 18) — second priority after the
    # per-user profile, before the hard-coded last-resort defaults.
    ("format.date", "yyyy-MM-dd", "string", "Default date display format (fallback after profile)"),
    ("format.time", "HH:mm", "string", "Default time display format (fallback after profile)"),
    ("format.number", "1,234.56", "string", "Default number display format (grouping/decimal)"),
    ("format.time_locale", "", "string", "Default time locale (blank → browser locale)"),
    ("format.amount_decimals", 6, "int", "Decimals for high-precision amounts (FX rates, investment quantities/unit prices)"),
    ("default_base_currency", "USD", "string", "Reporting currency for roll-ups (overridden by a user's profile base currency)"),
    ("default_txn_currency", "AED", "string", "Default currency for new transactions"),
    ("sql_console.enabled", True, "bool", "Enable the read-only SQL console"),
    ("sql_console.row_limit", 1000, "int", "Max rows returned by SQL console"),
    ("sql_console.timeout_ms", 5000, "int", "Statement timeout for SQL console"),
    ("import.dedup_window_days", 5, "int", "Window for import de-duplication"),
]
