"""Tests for mnemonic id generation (patched row allocator)."""

from types import SimpleNamespace

from app.services import id_sequence


class FakeSession:
    """Holds one IdSequence-like row per prefix in a dict."""

    def __init__(self):
        self.rows = {}

    def add(self, obj):
        self.rows[obj.prefix] = obj

    def flush(self):
        pass


def _patched_ensure_row(db, entity_type):
    prefix, pad = id_sequence.DEFAULT_PREFIXES.get(
        entity_type, (entity_type[:3].upper(), 5)
    )
    row = db.rows.get(prefix)
    if row is None:
        row = SimpleNamespace(prefix=prefix, entity_type=entity_type, pad_width=pad, current_seq=0)
        db.rows[prefix] = row
    return row


def test_next_mnemonic_formats_and_increments(monkeypatch):
    monkeypatch.setattr(id_sequence, "_ensure_row", _patched_ensure_row)
    db = FakeSession()
    assert id_sequence.next_mnemonic(db, "transaction") == "TRN-0000000001"
    assert id_sequence.next_mnemonic(db, "transaction") == "TRN-0000000002"


def test_partner_pad_width(monkeypatch):
    monkeypatch.setattr(id_sequence, "_ensure_row", _patched_ensure_row)
    db = FakeSession()
    assert id_sequence.next_mnemonic(db, "partner") == "PRT-00001"


def test_institution_prefix_no_collision_with_installment():
    inst_prefix = id_sequence.DEFAULT_PREFIXES["institution"][0]
    ins_prefix = id_sequence.DEFAULT_PREFIXES["installment_plan"][0]
    assert inst_prefix != ins_prefix
    assert inst_prefix == "IST"
    assert ins_prefix == "INS"