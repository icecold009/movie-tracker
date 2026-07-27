from api import index


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
    monkeypatch.setattr(index, "add_entry", lambda *args: calls.append(args))

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
            {"tmdb_id": None, "tmdb_media_type": None, "genre_ids": []},
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


def test_delete_accepts_authenticated_request(app, monkeypatch):
    calls = []
    monkeypatch.setattr(index, "delete_entry", lambda entry_id: calls.append(entry_id) or True)

    response = authenticated_client(app).post(
        "/delete/4",
        data={"csrf_token": "test-csrf-token"},
    )

    assert response.status_code == 302
    assert calls == [4]
