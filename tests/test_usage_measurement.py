from contextlib import contextmanager

import pytest

import database


class RecordingCursor:
    def __init__(self):
        self.calls = []

    def execute(self, query, params):
        self.calls.append((query, params))


def test_record_usage_event_upserts_daily_counter(monkeypatch):
    cursor = RecordingCursor()

    @contextmanager
    def fake_transaction():
        yield cursor

    monkeypatch.setattr(database, "db_transaction", fake_transaction)

    database.record_usage_event("public_view")

    assert len(cursor.calls) == 1
    query, params = cursor.calls[0]
    assert "ON CONFLICT (event_date, event_name)" in query
    assert params[1] == "public_view"


def test_record_usage_event_rejects_unknown_event(monkeypatch):
    called = False

    def fail_if_called():
        nonlocal called
        called = True

    monkeypatch.setattr(database, "db_transaction", fail_if_called)

    with pytest.raises(ValueError, match="Unsupported"):
        database.record_usage_event("password")

    assert called is False
