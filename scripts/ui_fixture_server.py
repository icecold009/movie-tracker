"""Local-only synthetic UI fixture server; all persistence and providers are stubbed."""
import argparse
import copy
import os
import secrets
import sys
import time
from datetime import date, datetime, timedelta, timezone

# Force synthetic child-process configuration before importing the application.
os.environ["SECRET_KEY"] = secrets.token_urlsafe(32)
os.environ["DATABASE_URL"] = "postgresql://fixture:fixture@127.0.0.1/fixture"
os.environ["TMDB_API_KEY"] = "fixture-only-no-provider-requests"
os.environ.pop("VERCEL", None)
os.environ.pop("FLASK_ENV", None)

from flask import Response, abort, jsonify, request, session  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ["ADMIN_PASSWORD_HASH"] = generate_password_hash(secrets.token_urlsafe(32))

from api import index  # noqa: E402
from database import DatabaseError  # noqa: E402
from tmdb import TMDBRequestError  # noqa: E402


FIXTURE_STATES = {
    "results",
    "zero-search-results",
    "empty-library",
    "loading-skeleton",
    "database-error",
    "tmdb-error",
    "admin",
    "admin-empty",
    "admin-tmdb-error",
    "manual-fallback",
    "stale-metadata",
    "undo-recovery",
    "recommendation-results",
    "recommendation-empty",
    "recommendation-provider-error",
    "recommendation-database-error",
}
ADMIN_STATES = {
    "admin",
    "admin-empty",
    "admin-tmdb-error",
    "manual-fallback",
    "undo-recovery",
}
_FIXTURE_STORES = {}


def _base_entries():
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
            "metadata_updated_at": datetime.now(timezone.utc).isoformat(),
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


def _seed_entries(state):
    if state in {
        "empty-library",
        "admin-empty",
        "recommendation-empty",
    }:
        return []
    if state == "stale-metadata":
        stale = _base_entries()[0]
        stale["title"] = "Old Metadata"
        stale["metadata_updated_at"] = (
            datetime.now(timezone.utc) - timedelta(days=181)
        ).isoformat()
        return [stale]
    if state == "undo-recovery":
        return [entry for entry in _base_entries() if entry["id"] != 101]
    return _base_entries()


def _state():
    return session.get("_ui_fixture_state", "results")


def _store():
    fixture_id = session.get("_ui_fixture_id")
    if not fixture_id:
        fixture_id = secrets.token_urlsafe(12)
        session["_ui_fixture_id"] = fixture_id
    return _FIXTURE_STORES.setdefault(
        fixture_id,
        _seed_entries(_state()),
    )


def _get_all():
    if _state() == "database-error":
        raise DatabaseError("Synthetic database outage.")
    if _state() == "recommendation-database-error":
        raise DatabaseError("Synthetic saved-title outage.")
    return copy.deepcopy(_store())


def _discover_tmdb(media_type):
    if _state() == "recommendation-provider-error":
        raise TMDBRequestError("Synthetic TMDB outage.")
    if _state() == "recommendation-empty" or media_type != "movie":
        return []
    return [
        {
            "title": "New Mystery",
            "tmdb_id": 704,
            "media_type": "movie",
            "genre_ids": [18],
            "release_date": "2025-04-20",
            "poster_url": "/fixture-poster/arrival.svg",
        }
    ]


def _search_tmdb(title):
    if _state() in {"tmdb-error", "admin-tmdb-error"}:
        raise TMDBRequestError("Synthetic TMDB outage.")
    return None


def _add_entry(
    title,
    entry_type,
    status,
    rating,
    poster_url,
    **metadata,
):
    current = _store()
    new_entry = {
        "id": max((entry["id"] for entry in current), default=9000) + 1,
        "title": title,
        "entry_type": entry_type,
        "status": status,
        "rating": rating,
        "poster_url": poster_url,
        "added_on": date.today().isoformat(),
        "release_date": metadata.get("release_date"),
        "synopsis": metadata.get("synopsis", ""),
        "metadata_source": metadata.get("metadata_source", "Manual"),
        "metadata_updated_at": metadata.get("metadata_updated_at"),
        "tmdb_id": metadata.get("tmdb_id"),
        "tmdb_media_type": metadata.get("tmdb_media_type"),
        "genre_ids": metadata.get("genre_ids", []),
    }
    current.append(new_entry)
    return new_entry["id"]


def _get_entry(entry_id):
    return next(
        (
            copy.deepcopy(entry)
            for entry in _store()
            if entry["id"] == entry_id
        ),
        None,
    )


def _update_entry(entry_id, status, rating):
    for entry in _store():
        if entry["id"] == entry_id:
            entry["status"] = status
            entry["rating"] = rating
            return True
    return False


def _delete_entry(entry_id):
    current = _store()
    original_count = len(current)
    current[:] = [
        entry for entry in current if entry["id"] != entry_id
    ]
    return original_count - len(current)


def _restore_entry(entry):
    _store().append(copy.deepcopy(entry))
    return 1


index.get_all = _get_all
index.discover_tmdb = _discover_tmdb
index.search_tmdb = _search_tmdb
index.add_entry = _add_entry
index.get_entry = _get_entry
index.update_entry = _update_entry
index.delete_entry = _delete_entry
index.restore_entry = _restore_entry
index._record_usage_event = lambda event_name: None
index.app.config.update(TESTING=True)


@index.app.before_request
def install_fixture_state():
    requested = request.args.get("fixture")
    if requested is not None and requested not in FIXTURE_STATES:
        abort(404)

    fixture_id = session.get("_ui_fixture_id")
    if not fixture_id:
        fixture_id = secrets.token_urlsafe(12)
        session["_ui_fixture_id"] = fixture_id

    previous = session.get("_ui_fixture_state")
    state = requested or previous or "results"
    if state != previous:
        session["_ui_fixture_state"] = state
        _FIXTURE_STORES[fixture_id] = _seed_entries(state)
        session.pop(index.PENDING_ADD_SESSION_KEY, None)
        session.pop(index.ADD_RECOVERY_SESSION_KEY, None)
        session.pop(index.UNDO_ENTRY_SESSION_KEY, None)

        if state in ADMIN_STATES:
            session["logged_in"] = True
            session["_csrf_token"] = "local-ui-fixture-csrf"
        else:
            session.pop("logged_in", None)
            session.pop("_csrf_token", None)

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
        elif state == "undo-recovery":
            session[index.UNDO_ENTRY_SESSION_KEY] = {
                "expires_at": time.time() + 30,
                "entry": _base_entries()[0],
            }


@index.app.after_request
def mark_fixture_response(response):
    response.headers["X-Movie-Tracker-UI-Fixture"] = "synthetic"
    return response


@index.app.get("/_ui_fixture/health")
def fixture_health():
    return jsonify(fixture_only=True, state=_state(), python_version=sys.version.split()[0])


@index.app.get("/fixture-poster/<slug>.svg")
def fixture_poster(slug):
    artwork = {
        "arrival": ("#243447", "#a4c6e8", "ARRIVAL"),
        "severance": ("#1d2c3d", "#b7d1cf", "TWO LIVES"),
    }.get(slug)
    if not artwork:
        return "Not found", 404
    background, accent, title = artwork
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 600">
    <rect width="400" height="600" fill="{background}"/>
    <circle cx="275" cy="180" r="132" fill="none" stroke="{accent}" stroke-opacity=".45" stroke-width="2"/>
    <path d="M0 420 Q130 350 400 455 V600 H0Z" fill="{accent}" fill-opacity=".16"/>
    <text x="34" y="500" fill="{accent}" font-family="Georgia,serif" font-size="32">{title}</text>
    <text x="36" y="550" fill="#d2d0c8" font-family="monospace" font-size="11">LOCAL FIXTURE ART</text>
    </svg>"""
    return Response(svg, mimetype="image/svg+xml")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", choices=["127.0.0.1", "localhost"], default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5069)
    args = parser.parse_args()
    index.app.run(
        host=args.host,
        port=args.port,
        debug=False,
        use_reloader=False,
    )


if __name__ == "__main__":
    main()
