import hmac
import logging
import os
import secrets
import sys
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from flask import Flask, abort, jsonify, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash

from config import ADMIN_PASSWORD_HASH, SECRET_KEY
from database import (
    DatabaseError,
    add_entry,
    delete_entry,
    get_all,
    record_usage_event,
    update_entry,
)
from observability import log_event
from recommendations import build_recommendations
from tmdb import TMDBError, discover_tmdb, search_tmdb

app = Flask(__name__,
    template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'),
    static_folder=os.path.join(os.path.dirname(__file__), '..', 'static')
)

app.secret_key = SECRET_KEY
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=(
        os.getenv("VERCEL") == "1"
        or os.getenv("FLASK_ENV", "").lower() == "production"
    ),
)

ALLOWED_ENTRY_TYPES = {"Movie", "TV Show"}
ALLOWED_STATUSES = {"Watched", "Want to Watch"}
MIN_RATING = 1
MAX_RATING = 10
MAX_TITLE_LENGTH = 200
CSRF_SESSION_KEY = "_csrf_token"
LOGIN_ATTEMPT_WINDOW_SECONDS = 60
MAX_LOGIN_ATTEMPTS = 5
MAX_TRACKED_LOGIN_CLIENTS = 4096
_login_attempts = {}


def _record_usage_event(event_name):
    if app.testing:
        return
    try:
        record_usage_event(event_name)
    except (DatabaseError, ValueError):
        log_event(
            app.logger,
            logging.WARNING,
            "usage.record_failed",
            operation=event_name,
        )


def _get_csrf_token():
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def _require_csrf_token():
    expected = session.get(CSRF_SESSION_KEY)
    submitted = request.form.get("csrf_token", "")
    if not expected or not submitted or not hmac.compare_digest(expected, submitted):
        abort(400)


def _prune_login_attempts(now, preserve_key=None):
    stale_keys = [
        key
        for key, attempts in _login_attempts.items()
        if key != preserve_key
        and (not attempts or now - attempts[-1] >= LOGIN_ATTEMPT_WINDOW_SECONDS)
    ]
    for key in stale_keys:
        _login_attempts.pop(key, None)

    overflow = len(_login_attempts) - MAX_TRACKED_LOGIN_CLIENTS
    if overflow <= 0:
        return

    evictable = [
        (key, attempts[-1] if attempts else float("-inf"))
        for key, attempts in _login_attempts.items()
        if key != preserve_key
    ]
    for key, _ in sorted(evictable, key=lambda item: item[1])[:overflow]:
        _login_attempts.pop(key, None)


def _login_attempts_for(client_key, now):
    recent = [
        attempt
        for attempt in _login_attempts.get(client_key, [])
        if now - attempt < LOGIN_ATTEMPT_WINDOW_SECONDS
    ]
    _login_attempts[client_key] = recent
    _prune_login_attempts(now, preserve_key=client_key)
    return recent


@app.context_processor
def inject_csrf_token():
    return {"csrf_token": _get_csrf_token}


def _validated_entry_form(include_title=False):
    values = {}
    errors = []

    if include_title:
        title = request.form.get("title", "").strip()
        if not title:
            errors.append("Title is required.")
        elif len(title) > MAX_TITLE_LENGTH:
            errors.append(f"Title must be {MAX_TITLE_LENGTH} characters or fewer.")
        values["title"] = title

    entry_type = request.form.get("entry_type", "Movie")
    if entry_type not in ALLOWED_ENTRY_TYPES:
        errors.append("Choose a valid entry type.")
    values["entry_type"] = entry_type

    status = request.form.get("status", "Watched")
    if status not in ALLOWED_STATUSES:
        errors.append("Choose a valid status.")
    values["status"] = status

    raw_rating = request.form.get("rating", "7")
    try:
        rating = int(raw_rating)
    except (TypeError, ValueError):
        rating = None
        errors.append("Rating must be a whole number from 1 to 10.")
    if rating is not None and not MIN_RATING <= rating <= MAX_RATING:
        errors.append("Rating must be a whole number from 1 to 10.")
    values["rating"] = rating

    return (None, errors) if errors else (values, [])


@app.route("/healthz")
def healthz():
    return jsonify(status="ok")


@app.route("/recommendations")
def recommendations():
    try:
        entries = get_all()
    except DatabaseError as error:
        return render_template(
            "recommendations.html",
            recommendations=[],
            error=str(error),
        ), 503

    try:
        candidates = discover_tmdb("movie") + discover_tmdb("tv")
        results = build_recommendations(entries, candidates)
    except TMDBError as error:
        _record_usage_event("recommendation_view")
        return render_template(
            "recommendations.html",
            recommendations=[],
            error=str(error),
        ), 503

    _record_usage_event("recommendation_view")
    return render_template(
        "recommendations.html",
        recommendations=results,
        error=None,
    )


@app.route("/")
def index():
    try:
        entries = get_all()
    except DatabaseError as error:
        flash(str(error))
        return render_template(
            "index.html",
            entries=[],
            logged_in=session.get("logged_in", False),
        ), 503
    _record_usage_event("public_view")
    return render_template("index.html", entries=entries, logged_in=session.get("logged_in", False))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("index"))
    if request.method == "POST":
        _require_csrf_token()
        now = time.monotonic()
        client_key = request.remote_addr or "unknown"
        recent_attempts = _login_attempts_for(client_key, now)
        if len(recent_attempts) >= MAX_LOGIN_ATTEMPTS:
            flash("Too many login attempts. Try again later.")
            retry_after = max(
                1,
                int(LOGIN_ATTEMPT_WINDOW_SECONDS - (now - recent_attempts[0])),
            )
            return render_template("login.html"), 429, {
                "Retry-After": str(retry_after),
            }
        typed = request.form.get("password", "")
        try:
            password_matches = bool(typed) and check_password_hash(
                ADMIN_PASSWORD_HASH,
                typed,
            )
        except (TypeError, ValueError):
            log_event(
                app.logger,
                logging.ERROR,
                "auth.invalid_password_hash",
                route="/login",
            )
            password_matches = False
        if password_matches:
            _login_attempts.pop(client_key, None)
            session.clear()
            session["logged_in"] = True
            return redirect(url_for("index"))
        recent_attempts.append(now)
        flash("Incorrect password.")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    _require_csrf_token()
    session.clear()
    return redirect(url_for("index"))


@app.route("/add", methods=["POST"])
def add():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    _require_csrf_token()
    values, errors = _validated_entry_form(include_title=True)
    if errors:
        for error in errors:
            flash(error)
        return redirect(url_for("index"))
    title = values["title"]
    entry_type = values["entry_type"]
    status = values["status"]
    rating = values["rating"]
    try:
        result = search_tmdb(title)
    except TMDBError as error:
        flash(str(error))
        return redirect(url_for("index"))
    if result:
        full_title = result["full_title"]
        poster_url = result["poster_url"]
        tmdb_id = result.get("tmdb_id")
        tmdb_media_type = result.get("media_type")
        genre_ids = result.get("genre_ids", [])
    else:
        full_title = title
        poster_url = ""
        tmdb_id = None
        tmdb_media_type = None
        genre_ids = []
    # The admin's explicit Movie/TV Show selection is authoritative. TMDB's
    # mixed-search media_type is used for lookup metadata, not classification.
    try:
        add_entry(
            full_title,
            entry_type,
            status,
            rating,
            poster_url,
            tmdb_id=tmdb_id,
            tmdb_media_type=tmdb_media_type,
            genre_ids=genre_ids,
        )
    except DatabaseError as error:
        flash(str(error))
    else:
        _record_usage_event("successful_add")
    return redirect(url_for("index"))


@app.route("/edit/<int:entry_id>", methods=["POST"])
def edit(entry_id):
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    _require_csrf_token()
    values, errors = _validated_entry_form()
    if errors:
        for error in errors:
            flash(error)
        return redirect(url_for("index"))
    try:
        updated = update_entry(entry_id, values["status"], values["rating"])
    except DatabaseError as error:
        flash(str(error))
        return redirect(url_for("index"))
    if not updated:
        flash("Entry not found.")
    return redirect(url_for("index"))


@app.route("/delete/<int:entry_id>", methods=["POST"])
def delete(entry_id):
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    _require_csrf_token()
    try:
        deleted = delete_entry(entry_id)
    except DatabaseError as error:
        flash(str(error))
        return redirect(url_for("index"))
    if not deleted:
        flash("Entry not found.")
    return redirect(url_for("index"))
