import pytest
import psycopg2

import database


def test_connection_failure_is_wrapped_as_database_error(monkeypatch):
    def raise_connection_error():
        raise psycopg2.OperationalError("connection failed")

    monkeypatch.setattr(
        database,
        "get_conn",
        raise_connection_error,
    )

    with pytest.raises(database.DatabaseError, match="watchlist database"):
        with database.db_transaction():
            pass
