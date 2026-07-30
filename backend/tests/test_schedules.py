"""Tests for the statement parser (CSV) + amount/date normalization."""

from app.services import import_parser


def test_parse_csv_maps_canonical_fields():
    csv = (
        "Date,Description,Amount,Currency\n"
        "2025-01-15,Grocery Store,-120.50,AED\n"
        "15/02/2025,Salary,5,000.00,AED\n"
    )
    rows = import_parser.parse_csv(csv.encode("utf-8"))
    assert len(rows) == 2
    assert rows[0]["mapped"]["date"] == "2025-01-15"
    assert rows[0]["mapped"]["amount"] == -120.50
    assert rows[0]["mapped"]["description"] == "Grocery Store"
    assert rows[0]["mapped"]["currency"] == "AED"


def test_parse_amount_parentheses_negative():
    assert import_parser._parse_amount("(200.00)") == -200.0
    assert import_parser._parse_amount("1,234.56") == 1234.56
    assert import_parser._parse_amount("") is None


def test_parse_date_multiple_formats():
    assert import_parser._parse_date("2025-03-01") == "2025-03-01"
    assert import_parser._