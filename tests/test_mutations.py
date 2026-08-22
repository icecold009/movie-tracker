from api import index
from tmdb import TMDBRequestError


def authenticated_client(app):
    client = app.test_client()
    with client.session_transaction() as session:
        session["logged_in"] = True
        session["_csrf_token"] = "test-csrf-token"
    return client


def test_add_rejects_blank_title_before_external_calls(app, monkeypatch):
    calls = []
    monkeypatch.setattr(index, "search_tmdb", lambda title: calls.append(title))
    monkeypatch.setattr(
        index,
        "add_entry",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    response = authenticated_client(app).post(
        "/add",
        data={
            "csrf_token": "test-csrf-token",
            "title": "   ",
            "entry_type": "Movie",
            "status": "Watched",
            "rating": "7",
        },
    )

    assert response.status_code == 302
    assert calls == []


def test_add_accepts_valid_input_with_mocked_tmdb_and_database(app, monkeypatch):
    calls = []
    monkeypatch.setattr(index, "search_tmdb", lambda title: None)
    monkeypatch.setattr(
        index,
        "add_entry",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    response = authenticated_client(app).post(
        "/add",
        data={
            "csrf_token": "test-csrf-token",
            "title": "Example",
            "entry_type": "TV Show",
            "status": "Want to Watch",
            "rating": "8",
        },
    )

    assert response.status_code == 302
    assert calls == [
        (
            ("Example", "TV Show", "Want to Watch", 8, ""),
            {
                "tmdb_id": None,
                "tmdb_media_type": None,
                "genre_ids": [],
                "synopsis": "",
                "release_date": None,
                "metadata_source": "Manual",
                "metadata_updated_at": None,
            },
        )
    ]


def test_edit_accepts_valid_input(app, monkeypatch):
    calls = []
    monkeypatch.setattr(index, "update_entry", lambda *args: calls.append(args) or True)

    response = authenticated_client(app).post(
        "/edit/4",
        data={
            "csrf_token": "test-csrf-token",
            "status": "Watched",
            "rating": "9",
        },
    )

    assert response.status_code == 302
    assert calls == [(4, "Watched", 9)]


def test_edit_rejects_invalid_rating_before_database_call(app, monkeypatch):
    calls = []
    monkeypatch.setattr(index, "update_entry", lambda *args: calls.append(args))

    response = authenticated_client(app).post(
        "/edit/4",
        data={
            "csrf_token": "test-csrf-token",
            "status": "Watched",
            "rating": "11",
        },
    )

    assert response.status_code == 302
    assert calls == []


def test_provider_failure_preserves_add_form_for_recovery(app, monkeypatch):
    monkeypatch.setattr(
        index,
        "search_tmdb",
        lambda title: (_ for _ in ()).throw(TMDBRequestError("TMDB is unavailable.")),
    )
    monkeypatch.setattr(index, "get_all", lambda: [])

    client = authenticated_client(app)
    response = client.post(
        "/add",
        data={
            "csrf_token": "test-csrf-token",
            "title": "The Long Search",
            "entry_type": "Movie",
            "status": "Want to Watch",
            "rating": "6",
        },
    )

    assert response.status_code == 302
    with client.session_transaction() as session:
        assert session["_pending_add"]["title"] == "The Long Search"
        assert session["_add_recovery"]["kind"] == "provider"

    page = client.get("/")
    assert b'The Long Search' in page.data
    assert b"Metadata lookup failed" in page.data


def test_delete_can_be_undone_without_losing_metadata(app, monkeypatch):
    restored = []
    monkeypatch.setattr(index, "get_entry", lambda entry_id: {
        "title": "Recoverable",
        "entry_type": "Movie",
        "status": "Watched",
        "rating": 8,
        "poster_url": "",
        "added_on": "2026-08-22",
        "tmdb_id": None,
        "tmdb_media_type": None,
        "genre_ids": [],
        "synopsis": "",
        "release_date": None,
        "metadata_source": "Manual",
        "metadata_updated_at": None,
    })
    monkeypatch.setattr(index, "delete_entry", lambda entry_id: 1)
    monkeypatch.setattr(index, "restore_entry", lambda entry: restored.append(entry))

    client = authenticated_client(app)
    deleted = client.post("/delete/4", data={"csrf_token": "test-csrf-token"})
    assert deleted.status_code == 302

    restored_response = client.post("/undo", data={"csrf_token": "test-csrf-token"})

    assert restored_response.status_code == 302
    assert restored[0]["title"] == "Recoverable"


def test_delete_accepts_authenticated_request(app, monkeypatch):
    calls = []
    monkeypatch.setattr(index, "get_entry", lambda entry_id: {"title": "Example"})
    monkeypatch.setattr(index, "delete_entry", lambda entry_id: calls.append(entry_id) or True)

    response = authenticated_client(app).post(
        "/delete/4",
        data={"csrf_token": "test-csrf-token"},
    )

    assert response.status_code == 302
    assert calls == [4]
