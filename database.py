import datetime
import logging
from contextlib import contextmanager

import psycopg2
import psycopg2.extras

from config import DATABASE_URL
from observability import log_event


logger = logging.getLogger(__name__)
DB_CONNECT_TIMEOUT_SECONDS = 5


class DatabaseError(Exception):
    """Safe application-level error for database connectivity or SQL failures."""


def get_conn():
    url = DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    # Vercel should use Supabase's Shared Pooler transaction-mode URL. Keep
    # connection attempts bounded because serverless requests have finite time.
    return psycopg2.connect(
        url,
        sslmode="require",
        connect_timeout=DB_CONNECT_TIMEOUT_SECONDS,
    )


@contextmanager
def db_transaction(cursor_factory=None):
    conn = None
    cur = None
    try:
        conn = get_conn()
        if cursor_factory is None:
            cur = conn.cursor()
        else:
            cur = conn.cursor(cursor_factory=cursor_factory)
        yield cur
        conn.commit()
    except psycopg2.Error as exc:
        if conn is not None:
            conn.rollback()
        log_event(
            logger,
            logging.WARNING,
            "database.operation_failed",
            exception_type=type(exc).__name__,
            operation="transaction",
        )
        raise DatabaseError("The watchlist database is temporarily unavailable.") from exc
    except Exception:
        if conn is not None:
            conn.rollback()
        raise
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()


def add_entry(
    title,
    entry_type,
    status,
    rating,
    poster_url,
    tmdb_id=None,
    tmdb_media_type=None,
    genre_ids=None,
    synopsis="",
    release_date=None,
    metadata_source="Manual",
    metadata_updated_at=None,
):
    with db_transaction() as cur:
        cur.execute(
            """
            INSERT INTO entries (
                title, entry_type, status, rating, poster_url, added_on,
                tmdb_id, tmdb_media_type, genre_ids, synopsis, release_date,
                metadata_source, metadata_updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                title,
                entry_type,
                status,
                rating,
                poster_url,
                str(datetime.date.today()),
                tmdb_id,
                tmdb_media_type,
                genre_ids or [],
                synopsis or "",
                release_date,
                metadata_source or "Manual",
                metadata_updated_at,
            )
        )


def record_usage_event(event_name):
    """Increment an allowlisted daily aggregate usage counter."""
    if event_name not in {"public_view", "successful_add", "recommendation_view"}:
        raise ValueError("Unsupported usage event")
    with db_transaction() as cur:
        cur.execute(
            """
            INSERT INTO usage_daily (event_date, event_name, event_count)
            VALUES (%s, %s, 1)
            ON CONFLICT (event_date, event_name)
            DO UPDATE SET event_count = usage_daily.event_count + 1
            """,
            (datetime.date.today(), event_name),
        )


def get_all():
    with db_transaction(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM entries ORDER BY id DESC")
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def get_entry(entry_id):
    with db_transaction(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM entries WHERE id = %s", (entry_id,))
        row = cur.fetchone()
    return dict(row) if row else None


def restore_entry(entry):
    with db_transaction() as cur:
        cur.execute(
            """
            INSERT INTO entries (
                title, entry_type, status, rating, poster_url, added_on,
                tmdb_id, tmdb_media_type, genre_ids, synopsis, release_date,
                metadata_source, metadata_updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                entry.get("title", ""),
                entry.get("entry_type", "Movie"),
                entry.get("status", "Want to Watch"),
                entry.get("rating", 7),
                entry.get("poster_url", ""),
                entry.get("added_on", str(datetime.date.today())),
                entry.get("tmdb_id"),
                entry.get("tmdb_media_type"),
                entry.get("genre_ids") or [],
                entry.get("synopsis", ""),
                entry.get("release_date"),
                entry.get("metadata_source", "Manual"),
                entry.get("metadata_updated_at"),
            ),
        )

def update_entry(entry_id, status, rating):
    with db_transaction() as cur:
        cur.execute(
            "UPDATE entries SET status = %s, rating = %s WHERE id = %s",
            (status, rating, entry_id)
        )
        return cur.rowcount

def delete_entry(entry_id):
    with db_transaction() as cur:
        cur.execute("DELETE FROM entries WHERE id = %s", (entry_id,))
        return cur.rowcount
