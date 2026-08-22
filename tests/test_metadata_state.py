from datetime import datetime, timedelta, timezone

from api import index


def test_metadata_state_distinguishes_missing_tmdb_and_stale_entries():
    assert index._metadata_state({}) == "Missing"
    assert index._metadata_state({"poster_url": "/poster.jpg", "metadata_source": "TMDB"}) == "TMDB"
    assert index._metadata_state({
        "tmdb_id": 42,
        "metadata_source": "TMDB",
        "metadata_updated_at": datetime.now(timezone.utc) - timedelta(days=181),
    }) == "Stale"


def test_index_renders_metadata_state_on_cards_and_details(app, monkeypatch):
    monkeypatch.setattr(index, "get_all", lambda: [{
        "id": 1,
        "title": "Old Metadata",
        "entry_type": "Movie",
        "status": "Watched",
        "rating": 8,
        "poster_url": "/poster.jpg",
        "metadata_source": "TMDB",
        "tmdb_id": 42,
        "metadata_updated_at": datetime.now(timezone.utc) - timedelta(days=181),
    }])
    monkeypatch.setattr(index, "_record_usage_event", lambda event_name: None)

    response = app.test_client().get("/")

    assert response.status_code == 200
    assert b"Stale metadata" in response.data
    assert b'data-detail-metadata-state="Stale"' in response.data
