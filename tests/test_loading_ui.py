from api import index


def test_watchlist_includes_progressive_loading_skeleton(app, monkeypatch):
    monkeypatch.setattr(index, "get_all", lambda: [])
    monkeypatch.setattr(index, "_record_usage_event", lambda event_name: None)

    response = app.test_client().get("/")

    assert response.status_code == 200
    assert b"data-page-skeleton" in response.data
    assert b"/static/app.js" in response.data
    assert b"Shaurya's watchlist" in response.data


def test_recommendations_includes_progressive_loading_skeleton(app, monkeypatch):
    monkeypatch.setattr(index, "get_all", lambda: [])
    monkeypatch.setattr(index, "discover_tmdb", lambda media_type: [])
    monkeypatch.setattr(index, "_record_usage_event", lambda event_name: None)

    response = app.test_client().get("/recommendations")

    assert response.status_code == 200
    assert b"data-page-skeleton" in response.data
    assert b"/static/app.js" in response.data
