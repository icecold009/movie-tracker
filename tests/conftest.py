import os

import pytest
from werkzeug.security import generate_password_hash


os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["ADMIN_PASSWORD_HASH"] = generate_password_hash("test-password")
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/test"
os.environ["TMDB_API_KEY"] = "test-tmdb-key"


@pytest.fixture
def app():
    from api.index import app as flask_app

    flask_app.config.update(TESTING=True)
    return flask_app

@pytest.fixture
def ui_entries():
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    return [
        {
            "id": 101,
            "title": "Arrival",
            "entry_type": "Movie",
            "status": "Watched",
            "rating": 9,
            "poster_url": "/fixture-poster/arrival.svg",
            "added_on": "2026-09-28",
            "release_date": "2016-11-11",
            "synopsis": "A linguist studies an unfamiliar signal.",
            "metadata_source": "TMDB",
            "metadata_updated_at": now,
            "tmdb_id": 329865,
            "tmdb_media_type": "movie",
            "genre_ids": [18, 878],
        },
        {
            "id": 102,
            "title": "Dune: Part Two",
            "entry_type": "Movie",
            "status": "Want to Watch",
            "rating": 7,
            "poster_url": None,
            "added_on": "2026-09-29",
            "release_date": None,
            "synopsis": "",
            "metadata_source": "Manual",
            "metadata_updated_at": None,
            "tmdb_id": None,
            "tmdb_media_type": None,
            "genre_ids": [],
        },
        {
            "id": 103,
            "title": "Severance",
            "entry_type": "TV Show",
            "status": "Watched",
            "rating": 10,
            "poster_url": "/fixture-poster/severance.svg",
            "added_on": "2026-09-30",
            "release_date": "2022-02-18",
            "synopsis": "Employees navigate a divided work and home life.",
            "metadata_source": "Manual",
            "metadata_updated_at": None,
            "tmdb_id": None,
            "tmdb_media_type": None,
            "genre_ids": [],
        },
    ]


@pytest.fixture
def ui_state_render(app, monkeypatch, ui_entries):
    """Render named UI states with synthetic reads and in-memory-only writes."""
    import copy
    import time
    from datetime import datetime, timedelta, timezone

    from api import index
    from database import DatabaseError
    from tmdb import TMDBRequestError

    def render(state, path="/"):
        entries = copy.deepcopy(ui_entries)
        if state in {"empty-library", "authenticated-admin-empty", "recommendation-empty"}:
            entries = []
        if state == "stale-metadata":
            stale = copy.deepcopy(entries[0])
            stale["title"] = "Old Metadata"
            stale["metadata_updated_at"] = (
                datetime.now(timezone.utc) - timedelta(days=181)
            ).isoformat()
            entries = [stale]

        writes = []
        provider_calls = []

        def get_all():
            if state == "database-error":
                raise DatabaseError("Synthetic database outage.")
            if state == "recommendation-database-error":
                raise DatabaseError("Synthetic saved-title outage.")
            return copy.deepcopy(entries)

        def discover_tmdb(media_type):
            if state == "recommendation-provider-error":
                raise TMDBRequestError("Synthetic TMDB outage.")
            return []

        def search_tmdb(title):
            provider_calls.append(title)
            if state == "tmdb-error":
                raise TMDBRequestError("Synthetic TMDB outage.")
            return None

        def add_entry(*args, **kwargs):
            writes.append(("add", args, kwargs))
            return 1

        def update_entry(*args, **kwargs):
            writes.append(("update", args, kwargs))
            return True

        def get_entry(entry_id):
            return next(
                (copy.deepcopy(entry) for entry in entries if entry["id"] == entry_id),
                None,
            )

        def delete_entry(entry_id):
            writes.append(("delete", entry_id))
            return 1

        def restore_entry(entry):
            writes.append(("restore", copy.deepcopy(entry)))
            return 1

        monkeypatch.setattr(index, "get_all", get_all)
        monkeypatch.setattr(index, "discover_tmdb", discover_tmdb)
        monkeypatch.setattr(index, "search_tmdb", search_tmdb)
        monkeypatch.setattr(index, "add_entry", add_entry)
        monkeypatch.setattr(index, "update_entry", update_entry)
        monkeypatch.setattr(index, "get_entry", get_entry)
        monkeypatch.setattr(index, "delete_entry", delete_entry)
        monkeypatch.setattr(index, "restore_entry", restore_entry)
        monkeypatch.setattr(index, "_record_usage_event", lambda event_name: None)

        client = app.test_client()
        if state in {
            "authenticated-admin",
            "authenticated-admin-empty",
            "manual-fallback",
            "tmdb-error",
            "undo-recovery",
        }:
            with client.session_transaction() as session:
                session["logged_in"] = True
                session["_csrf_token"] = "ui-fixture-csrf"
                if state == "manual-fallback":
                    session[index.PENDING_ADD_SESSION_KEY] = {
                        "title": "Preserved fixture title",
                        "entry_type": "TV Show",
                        "status": "Want to Watch",
                        "rating": 8,
                    }
                    session[index.ADD_RECOVERY_SESSION_KEY] = {
                        "kind": "provider",
                        "message": "Synthetic TMDB fixture outage.",
                    }
                if state == "undo-recovery":
                    session[index.UNDO_ENTRY_SESSION_KEY] = {
                        "expires_at": time.time() + 30,
                        "entry": copy.deepcopy(entries[0]),
                    }

        response = client.get(path)
        return {
            "client": client,
            "response": response,
            "writes": writes,
            "provider_calls": provider_calls,
        }

    return render
