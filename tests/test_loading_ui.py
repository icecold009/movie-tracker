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
    assert b'aria-modal="true" aria-hidden="true" aria-labelledby="detail-modal-title"' in response.data
    assert b'id="delete-modal"' in response.data
    assert b'id="edit-modal"' in response.data


def test_authenticated_library_groups_mutations_behind_manage_mode(app, monkeypatch):
    monkeypatch.setattr(index, "get_all", lambda: [{
        "id": 41,
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
        session["_csrf_token"] = "test-csrf-token"

    response = client.get("/")

    assert response.status_code == 200
    assert b'data-management-mode="inactive"' in response.data
    assert b'id="manage-toggle"' in response.data
    assert b'aria-expanded="false"' in response.data
    assert b'id="management-workspace"' in response.data
    assert b"Curator workspace" in response.data
    assert b"Search TMDB and add" in response.data
    assert b"Save without metadata" in response.data
    assert b'data-management-actions role="group"' in response.data
    assert b'class="card-edit-fallback-form" method="POST" action="/edit/41"' in response.data
    assert b'name="status"' in response.data
    assert b'name="rating" min="1" max="10" step="1" value="9"' in response.data
    assert b'class="card-action-fallback card-delete-fallback"' in response.data
    assert b'class="delete-confirm-btn card-fallback-delete-confirm"' in response.data
    assert b'class="edit-btn card-edit-js"' in response.data
    assert b'class="delete-btn card-delete-js"' in response.data
    assert b'action="/delete/41"' in response.data
    assert b'name="csrf_token" value="test-csrf-token"' in response.data


def test_add_recovery_reopens_curator_workspace_with_entered_values(app, monkeypatch):
    monkeypatch.setattr(index, "get_all", lambda: [])
    monkeypatch.setattr(index, "_record_usage_event", lambda event_name: None)
    client = app.test_client()
    with client.session_transaction() as session:
        session["logged_in"] = True
        session[index.PENDING_ADD_SESSION_KEY] = {
            "title": "Unchanged title",
            "entry_type": "TV Show",
            "status": "Want to Watch",
            "rating": 8,
        }
        session[index.ADD_RECOVERY_SESSION_KEY] = {
            "kind": "provider",
            "message": "TMDB fixture unavailable.",
        }

    response = client.get("/")

    assert response.status_code == 200
    assert b'data-management-mode="active"' in response.data
    assert b'aria-expanded="true"' in response.data
    assert b'value="Unchanged title"' in response.data
    assert b'value="TV Show" selected' in response.data
    assert b'value="Want to Watch" selected' in response.data
    assert b'value="8"' in response.data
    assert b"TMDB fixture unavailable." in response.data

def test_reusable_fixture_renders_every_required_server_state(ui_state_render):
    cases = [
        ("empty-library", "/", 200, b"No titles yet."),
        ("authenticated-admin-empty", "/", 200, b'data-management-mode="inactive"'),
        ("database-error", "/", 503, b"Synthetic database outage."),
        ("manual-fallback", "/", 200, b"Preserved fixture title"),
        ("stale-metadata", "/", 200, b'data-detail-metadata-state="Stale"'),
        ("undo-recovery", "/", 200, b"Undo delete"),
        ("recommendation-empty", "/recommendations", 200, b"No results to show"),
        (
            "recommendation-provider-error",
            "/recommendations",
            503,
            b"Synthetic TMDB outage.",
        ),
        (
            "recommendation-database-error",
            "/recommendations",
            503,
            b"Synthetic saved-title outage.",
        ),
    ]

    for state, path, status, marker in cases:
        rendered = ui_state_render(state, path)
        assert rendered["response"].status_code == status, state
        if marker:
            assert marker in rendered["response"].data, state


def test_manual_no_metadata_submission_uses_only_fixture_write(ui_state_render):
    rendered = ui_state_render("authenticated-admin-empty")
    response = rendered["client"].post(
        "/add",
        data={
            "csrf_token": "ui-fixture-csrf",
            "title": "Fixture-only addition",
            "entry_type": "Movie",
            "status": "Want to Watch",
            "rating": "7",
            "lookup_mode": "manual",
        },
    )

    assert response.status_code == 302
    assert len(rendered["writes"]) == 1
    assert rendered["writes"][0][0] == "add"
    assert rendered["writes"][0][1][0] == "Fixture-only addition"
    assert rendered["provider_calls"] == []

def test_fixture_tmdb_failure_preserves_add_values_for_manual_recovery(ui_state_render):
    rendered = ui_state_render("tmdb-error")
    response = rendered["client"].post(
        "/add",
        data={
            "csrf_token": "ui-fixture-csrf",
            "title": "Synthetic provider failure",
            "entry_type": "Movie",
            "status": "Want to Watch",
            "rating": "6",
            "lookup_mode": "tmdb",
        },
    )
    page = rendered["client"].get("/")

    assert response.status_code == 302
    assert b"Synthetic TMDB outage." in page.data
    assert b'value="Synthetic provider failure"' in page.data
    assert rendered["provider_calls"] == ["Synthetic provider failure"]
    assert rendered["writes"] == []
