from api import index


def test_watchlist_includes_progressive_loading_skeleton(app, monkeypatch):
    monkeypatch.setattr(index, "get_all", lambda: [])
    monkeypatch.setattr(index, "_record_usage_event", lambda event_name: None)

    response = app.test_client().get("/")

    assert response.status_code == 200
    assert b"data-page-skeleton" in response.data
    assert b"/static/app.js" in response.data
    assert b"Shaurya's archive" in response.data


def test_empty_library_has_one_server_rendered_empty_state(app, monkeypatch):
    monkeypatch.setattr(index, "get_all", lambda: [])
    monkeypatch.setattr(index, "_record_usage_event", lambda event_name: None)

    response = app.test_client().get("/")

    assert response.status_code == 200
    assert b'data-library-empty aria-labelledby="library-empty-title"' in response.data
    assert b"No titles yet." in response.data
    assert b'data-filter-empty hidden' in response.data
    assert b'data-library-section=' not in response.data


def test_library_search_is_separate_from_admin_title_lookup(app, monkeypatch):
    monkeypatch.setattr(index, "get_all", lambda: [{
        "id": 1,
        "title": "Arrival",
        "entry_type": "Movie",
        "status": "Watched",
        "rating": 9,
        "poster_url": None,
    }])
    monkeypatch.setattr(index, "_record_usage_event", lambda event_name: None)
    client = app.test_client()
    with client.session_transaction() as session:
        session["logged_in"] = True

    response = client.get("/")

    assert response.status_code == 200
    assert b'type="search" id="library-search"' in response.data
    assert b'type="text" id="title" name="title"' in response.data
    assert b'data-library-section="Movie"' in response.data
    assert b'data-library-section="TV Show"' not in response.data
    assert b'data-entry-title="Arrival"' in response.data


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
    assert b'data-detail-rating-context="Top tier"' in response.data
    assert b"Top tier" in response.data
    assert b"Personal rating" in response.data
    assert b"rating-panel" not in response.data


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
    assert b'id="detail-modal"' in response.data
    assert b"/static/app.js" in response.data
