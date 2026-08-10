import re

from api import index


def login_csrf_token(client):
    response = client.get("/login")
    match = re.search(
        r'name="csrf_token" value="([^"]+)"',
        response.get_data(as_text=True),
    )
    assert match
    return match.group(1)


def test_login_uses_clean_password_panel(app):
    response = app.test_client().get("/login")

    assert response.status_code == 200
    assert b"Welcome back." in response.data
    assert b"data-password-input" in response.data
    assert b"data-password-toggle" in response.data
    assert b'autocomplete="current-password"' in response.data


def test_login_success_sets_authenticated_session(app, monkeypatch):
    monkeypatch.setattr(index, "get_all", lambda: [])
    client = app.test_client()
    token = login_csrf_token(client)

    response = client.post(
        "/login",
        data={"csrf_token": token, "password": "test-password"},
    )

    assert response.status_code == 302
    with client.session_transaction() as session:
        assert session["logged_in"] is True
        assert "_csrf_token" not in session


def test_login_failure_does_not_authenticate(app):
    client = app.test_client()
    token = login_csrf_token(client)

    response = client.post(
        "/login",
        data={"csrf_token": token, "password": "wrong-password"},
    )

    assert response.status_code == 200
    assert b"Incorrect password." in response.data
    with client.session_transaction() as session:
        assert session.get("logged_in") is not True


def test_logout_clears_authenticated_session(app):
    client = app.test_client()
    with client.session_transaction() as session:
        session["logged_in"] = True
        session["_csrf_token"] = "test-csrf-token"

    response = client.post(
        "/logout",
        data={"csrf_token": "test-csrf-token"},
    )

    assert response.status_code == 302
    with client.session_transaction() as session:
        assert dict(session) == {}


def test_anonymous_edit_and_delete_redirect_to_login(app):
    client = app.test_client()

    edit_response = client.post("/edit/1", data={})
    delete_response = client.post("/delete/1", data={})

    assert edit_response.status_code == 302
    assert edit_response.headers["Location"].endswith("/login")
    assert delete_response.status_code == 302
    assert delete_response.headers["Location"].endswith("/login")


def test_login_attempt_state_evicts_stale_clients(app):
    index._login_attempts.clear()
    index._login_attempts["stale-client"] = [0]

    index._login_attempts_for(
        "current-client",
        index.LOGIN_ATTEMPT_WINDOW_SECONDS + 1,
    )

    assert "stale-client" not in index._login_attempts
    index._login_attempts.clear()
