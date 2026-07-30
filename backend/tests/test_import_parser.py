"""Tests for mnemonic id generation (fake session with row locking emulated)."""

from types import SimpleNamespace

from app.services import id_sequence


class FakeResult:
    def __init__(self, row):
        self._row = row

    def scalar_one_or_none(self):
        return self._row

    def scalar_one(self):
        return self._row


class FakeSession:
    """Holds one IdSequence-like row per prefix in a dict."""

    def __init__(self):
        self.rows = {}

    def execute(self, *_a, **_k):
        # id_sequence._ensure_row calls select(...).where(prefix==p).with_for_update();
        # we can't parse the stmt, so return the most-recently-requested prefix row.
        return FakeResult(self._pending)

    def add(self, obj):
        self.rows[obj.prefix] = obj

    def flush(self):
        pass

    # Helper used by the patched _ensure_row below.
    _pending = None


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
    a = id_sequence.next_mnemonic(db, "transaction")
    b = id_sequence.next_mnemonic(db, "transaction")
    assert a == "TRN-0000000001"
    assert b == "TRN-0000000002"


def test_partner_pad_width(monkeypatch):
    monkeypatch.setattr(id_sequence, "_ensure_row", _patched_ensure_row)
    db = FakeSession()
    assert id_sequence.next_mnemonic(db, "partner") == "PRT-00001"


def test_institution_prefix_no_collision(monkeypatch):
    monkeypatch.setattr(id_sequence, "_ensure_row", _patched_ensure_row)
    db = FakeSession()
    inst = id_sequence.next_mnemonic(db, "institution")
    ins = id_sequence.next_mnemon