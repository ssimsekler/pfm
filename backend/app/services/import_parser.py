"""Parse uploaded statements (CSV/XLSX/PDF) into normalized row dicts.

Best-effort column detection maps common header names to canonical fields:
date, amount, description, partner, currency. Unknown columns are preserved
under raw_data for user review on the validation screen (spec 3.2).
"""

import csv
import io
import re
from datetime import datetime
from typing import Any

# Canonical field -> candidate header substrings (lowercased).
HEADER_MAP = {
    "date": ["date", "value date", "txn date", "transaction date", "posting date"],
    "amount": ["amount", "debit", "credit", "value", "amt"],
    "description": ["description", "details", "narrative", "memo", "particulars", "reference"],
    "partner": ["partner", "payee", "merchant", "counterparty", "beneficiary", "to", "from"],
    "currency": ["currency", "ccy", "curr"],
}

# Day-first date formats (most of the world, e.g. AE/GB/DE).
DATE_FORMATS_DAY_FIRST = [
    "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
    "%d %b %Y", "%d %B %Y", "%Y/%m/%d", "%m/%d/%Y",
]
# Month-first date formats (US-style).
DATE_FORMATS_MONTH_FIRST = [
    "%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y",
    "%d %b %Y", "%d %B %Y", "%Y/%m/%d", "%d/%m/%Y",
]

# ISO country codes that conventionally use month-first dates.
_MONTH_FIRST_COUNTRIES = {"US", "USA"}
# ISO country codes that conventionally use comma as the decimal separator.
_COMMA_DECIMAL_COUNTRIES = {
    "DE", "FR", "IT", "ES", "NL", "BE", "AT", "PT", "TR", "BR", "AR", "RU",
    "PL", "SE", "NO", "DK", "FI", "CZ", "GR", "HU", "RO", "ID", "VN",
}


class Locale:
    """Country-derived parsing hints (A.1 / #4 country-aware import mapping)."""

    def __init__(self, country: str | None):
        code = (country or "").strip().upper()
        self.month_first = code in _MONTH_FIRST_COUNTRIES
        self.comma_decimal = code in _COMMA_DECIMAL_COUNTRIES
        self.date_formats = (
            DATE_FORMATS_MONTH_FIRST if self.month_first else DATE_FORMATS_DAY_FIRST
        )


def _canonical(header: str) -> str | None:
    h = header.strip().lower()
    for field, candidates in HEADER_MAP.items():
        if any(c in h for c in candidates):
            return field
    return None


def _parse_date(value: str, locale: Locale) -> str | None:
    value = (value or "").strip()
    for fmt in locale.date_formats:
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _parse_amount(value: Any, locale: Locale) -> float | None:
    if value is None:
        return None
    s = str(value).strip()
    if locale.comma_decimal:
        # e.g. "1.234,56" -> "1234.56": drop thousands dots, comma is decimal.
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")
    s = re.sub(r"[^\d.\-()]", "", s)
    if not s:
        return None
    negative = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    try:
        num = float(s)
        return -num if negative else num
    except ValueError:
        return None


def _normalize_rows(headers: list[str], rows: list[list[Any]], locale: Locale) -> list[dict]:
    canon = [_canonical(h) for h in headers]
    result: list[dict] = []
    for row in rows:
        raw = {headers[i]: row[i] for i in range(min(len(headers), len(row)))}
        mapped: dict[str, Any] = {}
        for i, field in enumerate(canon):
            if field is None or i >= len(row):
                continue
            val = row[i]
            if field == "date":
                mapped["date"] = _parse_date(str(val), locale)
            elif field == "amount":
                amt = _parse_amount(val, locale)
                if amt is not None and mapped.get("amount") in (None, 0):
                    mapped["amount"] = amt
            else:
                if val not in (None, ""):
                    mapped[field] = str(val).strip()
        result.append({"raw": raw, "mapped": mapped})
    return result


def parse_csv(content: bytes, locale: Locale) -> list[dict]:
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    all_rows = [r for r in reader if any(c.strip() for c in r)]
    if not all_rows:
        return []
    headers = [c.strip() for c in all_rows[0]]
    return _normalize_rows(headers, all_rows[1:], locale)


def parse_xlsx(content: bytes, locale: Locale) -> list[dict]:
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    rows = [r for r in rows if any(c is not None and str(c).strip() for c in r)]
    if not rows:
        return []
    headers = [str(c).strip() if c is not None else f"col{i}" for i, c in enumerate(rows[0])]
    return _normalize_rows(headers, rows[1:], locale)


def parse_pdf(content: bytes, locale: Locale) -> list[dict]:
    import pdfplumber

    result: list[dict] = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                if not table or len(table) < 2:
                    continue
                headers = [str(c).strip() if c else f"col{i}" for i, c in enumerate(table[0])]
                result.extend(_normalize_rows(headers, table[1:], locale))
    return result


def parse(content: bytes, filename: str, mime: str | None = None, country: str | None = None) -> list[dict]:
    """Parse a statement. `country` (ISO2/3) biases date/number formats (#4)."""
    locale = Locale(country)
    name = (filename or "").lower()
    if name.endswith(".csv") or (mime and "csv" in mime):
        return parse_csv(content, locale)
    if name.endswith((".xlsx", ".xls")) or (mime and "sheet" in (mime or "")):
        return parse_xlsx(content, locale)
    if name.endswith(".pdf") or (mime and "pdf" in (mime or "")):
        return parse_pdf(content, locale)
    # Fallback: try CSV.
    return parse_csv(content, locale)
