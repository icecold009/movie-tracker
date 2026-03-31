from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

import psycopg2
from psycopg2.extras import RealDictCursor


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return url


def _normalize_database_url(url: str) -> str:
    """
    Accepts common Postgres URL schemes.

    psycopg2 supports postgresql:// and postgres://; we normalize for clarity.
    """
    parsed = urlparse(url)
    if parsed.scheme == "postgres":
        return url.replace("postgres://", "postgresql://", 1)
    return url


@contextmanager
def get_conn():
    conn = psycopg2.connect(_normalize_database_url(get_database_url()))
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """
    Creates the base schema if it doesn't exist.
    """
    ddl = """
    CREATE TABLE IF NOT EXISTS movies (
      id BIGSERIAL PRIMARY KEY,
      tmdb_id BIGINT UNIQUE,
      title TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'planned',
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(ddl)


def execute(
    sql: str,
    params: Optional[Sequence[Any]] = None,
    *,
    fetch: bool = False,
) -> List[Dict[str, Any]]:
    """
    Runs a query; when fetch=True returns rows as dicts.
    """
    with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        if fetch:
            return list(cur.fetchall())
        return []


def add_movie(*, tmdb_id: int, title: str, status: str = "planned") -> None:
    execute(
        """
        INSERT INTO movies (tmdb_id, title, status)
        VALUES (%s, %s, %s)
        ON CONFLICT (tmdb_id) DO UPDATE
          SET title = EXCLUDED.title,
              status = EXCLUDED.status;
        """,
        (tmdb_id, title, status),
        fetch=False,
    )


def list_movies(*, status: Optional[str] = None) -> List[Dict[str, Any]]:
    if status:
        return execute(
            "SELECT * FROM movies WHERE status = %s ORDER BY created_at DESC;",
            (status,),
            fetch=True,
        )
    return execute("SELECT * FROM movies ORDER BY created_at DESC;", fetch=True)


def update_movie_status(*, tmdb_id: int, status: str) -> None:
    execute(
        "UPDATE movies SET status = %s WHERE tmdb_id = %s;",
        (status, tmdb_id),
        fetch=False,
    )


def delete_movie(*, tmdb_id: int) -> None:
    execute("DELETE FROM movies WHERE tmdb_id = %s;", (tmdb_id,), fetch=False)

