import hmac
import logging
import os
import secrets
import sys
import time
from datetime import datetime, timezone
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from flask import Flask, abort, jsonify, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash

from config import ADMIN_PASSWORD_HASH, SECRET_KEY
from database import (
    DatabaseError,
    add_entry,
    delete_entry,
    get_all,
    get_entry,
    record_usage_event,
    restore_entry,
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
_login_attempts = {}
PENDING_ADD_SESSION_KEY = "_pending_add"
ADD_RECOVERY_SESSION_KEY = "_add_recovery"
UNDO_ENTRY_SESSION_KEY = "_undo_entry"
UNDO_TTL_SECONDS = 30


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


def _login_attempts_for(client_key, now):
    recent = [
        attempt
        for attempt in _login_attempts.get(client_key, [])
        if now - attempt < LOGIN_ATTEMPT_WINDOW_SECONDS
    ]
    _login_attempts[client_key] = recent
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


def _pending_add_values(values):
    return {
        "title": values.get("title", ""),
        "entry_type": values.get("entry_type", "Movie"),
        "status": values.get("status", "Watched"),
        "rating": values.get("rating") or 7,
    }


def _clear_add_recovery():
    session.pop(PENDING_ADD_SESSION_KEY, None)
    session.pop(ADD_RECOVERY_SESSION_KEY, None)


def _set_add_recovery(values, message, kind="provider"):
    session[PENDING_ADD_SESSION_KEY] = _pending_add_values(values)
    session[ADD_RECOVERY_SESSION_KEY] = {"message": message, "kind": kind}


def _set_undo_entry(entry):
    if not entry:
        session.pop(UNDO_ENTRY_SESSION_KEY, None)
        return
    recoverable = {
        key: entry.get(key)
        for key in (
            "title",
            "entry_type",
            "status",
            "rating",
            "poster_url",
            "added_on",
            "tmdb_id",
            "tmdb_media_type",
            "genre_ids",
            "synopsis",
            "release_date",
            "metadata_source",
            "metadata_updated_at",
        )
    }
    if isinstance(recoverable.get("metadata_updated_at"), datetime):
        recoverable["metadata_updated_at"] = recoverable["metadata_updated_at"].isoformat()
    session[UNDO_ENTRY_SESSION_KEY] = {
        "expires_at": time.time() + UNDO_TTL_SECONDS,
        "entry": recoverable,
    }


def _get_undo_entry():
    undo = session.get(UNDO_ENTRY_SESSION_KEY)
    if not isinstance(undo, dict) or undo.get("expires_at", 0) <= time.time():
        session.pop(UNDO_ENTRY_SESSION_KEY, None)
        return None
    return undo.get("entry")


@app.route("/healthz")
def healthz():
    return jsonify(status="ok")


@app.route("/recommendations")
def recommendations():
    try:
        entries = get_all()
    except DatabaseError as error:
        _record_usage_event("recommendation_view")
        return render_template(
            "recommendations.html",
            recommendations=[],
            error=str(error),
            generated_at=None,
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
            generated_at=None,
        ), 503

    _record_usage_event("recommendation_view")
    return render_template(
        "recommendations.html",
        recommendations=results,
        error=None,
        generated_at=datetime.now(timezone.utc).isoformat(),
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
            pending_add=session.get(PENDING_ADD_SESSION_KEY, {}),
            add_recovery=session.get(ADD_RECOVERY_SESSION_KEY),
            undo_entry=_get_undo_entry(),
        ), 503
    _record_usage_event("public_view")
    return render_template(
        "index.html",
        entries=entries,
        logged_in=session.get("logged_in", False),
        pending_add=session.get(PENDING_ADD_SESSION_KEY, {}),
        add_recovery=session.get(ADD_RECOVERY_SESSION_KEY),
        undo_entry=_get_undo_entry(),
    )


@app.route("/search")
def search():
    if not session.get("logged_in"):
        return jsonify(error="Authentication required."), 401
    query = request.args.get("q", "").strip()
    if len(query) < 2:
        return jsonify(result=None)
    try:
        result = search_tmdb(query)
    except TMDBError as error:
        return jsonify(error=str(error)), 503
    return jsonify(result=result)


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
        _set_add_recovery(values or {"title": request.form.get("title", "")}, "", kind="validation")
        session.pop(ADD_RECOVERY_SESSION_KEY, None)
        for error in errors:
            flash(error)
        return redirect(url_for("index"))
    title = values["title"]
    entry_type = values["entry_type"]
    status = values["status"]
    rating = values["rating"]
    lookup_mode = request.form.get("lookup_mode", "tmdb")
    if lookup_mode == "manual":
        result = None
    else:
        try:
            result = search_tmdb(title)
        except TMDBError as error:
            _set_add_recovery(values, str(error), kind="provider")
            flash(str(error), "provider")
            return redirect(url_for("index"))
    if result:
        full_title = result["full_title"]
        poster_url = result["poster_url"]
        tmdb_id = result.get("tmdb_id")
        tmdb_media_type = result.get("media_type")
        genre_ids = result.get("genre_ids", [])
        synopsis = result.get("synopsis", "")
        release_date = result.get("release_date")
        metadata_source = "TMDB"
        metadata_updated_at = datetime.now(timezone.utc).isoformat()
    else:
        full_title = title
        poster_url = ""
        tmdb_id = None
        tmdb_media_type = None
        genre_ids = []
        synopsis = ""
        release_date = None
        metadata_source = "Manual"
        metadata_updated_at = None
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
            synopsis=synopsis,
            release_date=release_date,
            metadata_source=metadata_source,
            metadata_updated_at=metadata_updated_at,
        )
    except DatabaseError as error:
        _set_add_recovery(values, str(error), kind="database")
        flash(str(error), "database")
    else:
        _clear_add_recovery()
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
        entry = get_entry(entry_id)
        deleted = delete_entry(entry_id)
    except DatabaseError as error:
        flash(str(error), "database")
        return redirect(url_for("index"))
    if not deleted:
        flash("Entry not found.")
    elif entry:
        _set_undo_entry(entry)
        flash(f'Deleted “{entry.get("title", "entry")}”. You can undo this for 30 seconds.', "success")
    else:
        session.pop(UNDO_ENTRY_SESSION_KEY, None)
        flash("Entry deleted. Recovery details were unavailable.", "success")
    return redirect(url_for("index"))


@app.route("/undo", methods=["POST"])
def undo():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    _require_csrf_token()
    entry = _get_undo_entry()
    if not entry:
        flash("That recovery window has expired. You can add the title again manually.", "error")
        return redirect(url_for("index"))
    try:
        restore_entry(entry)
    except DatabaseError as error:
        flash(str(error), "database")
        return redirect(url_for("index"))
    session.pop(UNDO_ENTRY_SESSION_KEY, None)
    flash(f'Restored “{entry.get("title", "entry")}”.', "success")
    return redirect(url_for("index"))
