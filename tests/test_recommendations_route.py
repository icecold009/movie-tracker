from api import index
from database import DatabaseError
from tmdb import TMDBRequestError


def test_recommendations_route_renders_empty_state(app, monkeypatch):
    monkeypatch.setattr(index, "get_all", lambda: [])
    monkeypatch.setattr(index, "discover_tmdb", lambda media_type: [])

    response = app.test_client().get("/recommendations")

    assert response.status_code == 200
    assert b"No results to show" in response.data
    assert b"Based on" in response.data
    assert b"Data freshness" in response.data
    assert b"Limitations" in response.data
    assert b"TMDB cache refresh age is not exposed" in response.data
    assert b'href="/recommendations" class="state-primary"' in response.data
    assert b'href="/" class="state-secondary"' in response.data


def test_recommendations_route_renders_results(app, monkeypatch):
    monkeypatch.setattr(
        index,
        "get_all",
        lambda: [{"title": "Known", "genre_ids": [28], "tmdb_id": 1, "tmdb_media_type": "movie"}],
    )
    monkeypatch.setattr(
        index,
        "discover_tmdb",
        lambda media_type: [
            {
                "title": "New",
                "tmdb_id": 2,
                "media_type": media_type,
                "genre_ids": [28],
                "poster_url": "",
                "release_date": "2025-04-20",
            }
        ],
    )

    response = app.test_client().get("/recommendations")

    assert response.status_code == 200
    assert b"New" in response.data
    assert b"shares 1 genre with Known" in response.data
    assert b"Genre affinity" in response.data
    assert b"Movie" in response.data
    assert b"2025" in response.data
    assert b"Page generated" in response.data


def test_recommendations_route_omits_year_when_provider_does_not_supply_it(app, monkeypatch):
    monkeypatch.setattr(
        index,
        "get_all",
        lambda: [{"title": "Known", "genre_ids": [28], "tmdb_id": 1, "tmdb_media_type": "movie"}],
    )
    monkeypatch.setattr(
        index,
        "discover_tmdb",
        lambda media_type: ([
            {"title": "New", "tmdb_id": 2, "media_type": media_type, "genre_ids": [28], "poster_url": ""}
        ] if media_type == "movie" else []),
    )

    response = app.test_client().get("/recommendations")

    assert response.status_code == 200
    assert b"New" in response.data
    assert b"Available title details" in response.data
    assert b"Movie" in response.data
    assert b"2025" not in response.data

def test_recommendations_route_surfaces_tmdb_errors(app, monkeypatch):
    monkeypatch.setattr(index, "get_all", lambda: [])

    def raise_tmdb_error(media_type):
        raise TMDBRequestError("TMDB unavailable.")

    monkeypatch.setattr(index, "discover_tmdb", raise_tmdb_error)

    response = app.test_client().get("/recommendations")

    assert response.status_code == 503
    assert b"TMDB unavailable." in response.data
    assert b"Retry recommendations" in response.data
    assert b"Back to tracker" in response.data


def test_recommendations_database_error_does_not_retry_usage_write(app, monkeypatch):
    usage_events = []

    def raise_database_error():
        raise DatabaseError("Database unavailable.")

    monkeypatch.setattr(index, "get_all", raise_database_error)
    monkeypatch.setattr(index, "_record_usage_event", usage_events.append)

    response = app.test_client().get("/recommendations")

    assert response.status_code == 503
    assert b"Saved titles unavailable" in response.data
    assert b"when Movie Tracker can reach your saved titles" in response.data
    assert b"when TMDB is reachable" not in response.data
    assert b"Retry recommendations" in response.data
    assert b"Back to tracker" in response.data
    assert usage_events == []
