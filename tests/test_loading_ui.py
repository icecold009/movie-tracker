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


def test_pages_include_professional_footer(app, monkeypatch):
    monkeypatch.setattr(index, "get_all", lambda: [])
    monkeypatch.setattr(index, "discover_tmdb", lambda media_type: [])
    monkeypatch.setattr(index, "_record_usage_event", lambda event_name: None)

    client = app.test_client()
    for path in ("/", "/recommendations", "/login"):
        response = client.get(path)
        assert response.status_code == 200
        assert b"site-footer" in response.data
        assert b"Shaurya" in response.data
        assert b"Flask" in response.data


def test_perfect_ratings_get_distinct_gold_treatment(app, monkeypatch):
    monkeypatch.setattr(index, "get_all", lambda: [{
        "id": 10,
        "title": "A Perfect Title",
        "entry_type": "Movie",
        "status": "Watched",
        "rating": 10,
        "poster_url": None,
    }])
    monkeypatch.setattr(index, "_record_usage_event", lambda event_name: None)

    response = app.test_client().get("/")

    assert response.status_code == 200
    assert b"card-perfect" in response.data
    assert b"rating-perfect" in response.data
    assert b"Top tier" in response.data
    assert b"Personal rating" in response.data


def test_authenticated_edit_modal_exposes_accessible_focus_boundary(app, monkeypatch):
    monkeypatch.setattr(index, "get_all", lambda: [])
    client = app.test_client()
    with client.session_transaction() as session:
        session["logged_in"] = True
        session["_csrf_token"] = "test-csrf-token"

    response = client.get("/")

    assert response.status_code == 200
    assert b'role="dialog"' in response.data
    assert b'aria-hidden="true"' in response.data
    assert b'aria-live="polite"' in response.data
    assert b"if (e.key !== 'Tab') return;" in response.data
    assert b"e.preventDefault();" in response.data
