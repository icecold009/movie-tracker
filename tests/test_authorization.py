from api import index


def logged_in_client(app):
    client = app.test_client()
    with client.session_transaction() as session:
        session["logged_in"] = True
        session["_csrf_token"] = "test-csrf-token"
    return client


def test_public_read_does_not_require_authentication(app, monkeypatch):
    monkeypatch.setattr(index, "get_all", lambda: [])

    response = app.test_client().get("/")

    assert response.status_code == 200


def test_anonymous_write_redirects_to_login(app):
    response = app.test_client().post(
        "/add",
        data={
            "title": "Example",
            "entry_type": "Movie",
            "status": "Watched",
            "rating": "7",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_authenticated_write_accepts_valid_csrf_token(app, monkeypatch):
    added = []
    monkeypatch.setattr(index, "search_tmdb", lambda title: None)
    monkeypatch.setattr(
        index,
        "add_entry",
        lambda *args, **kwargs: added.append((args, kwargs)),
    )

    client = logged_in_client(app)
    response = client.post(
        "/add",
        data={
            "csrf_token": "test-csrf-token",
            "title": "Example",
            "entry_type": "Movie",
            "status": "Watched",
            "rating": "7",
        },
    )

    assert response.status_code == 302
    assert added == [
        (
            ("Example", "Movie", "Watched", 7, ""),
            {"tmdb_id": None, "tmdb_media_type": None, "genre_ids": []},
        )
    ]


def test_authenticated_write_rejects_missing_csrf_token(app, monkeypatch):
    writes = []
    monkeypatch.setattr(index, "add_entry", lambda *args: writes.append(args))

    client = logged_in_client(app)
    response = client.post(
        "/add",
        data={
            "title": "Example",
            "entry_type": "Movie",
            "status": "Watched",
            "rating": "7",
        },
    )

    assert response.status_code == 400
    assert writes == []
