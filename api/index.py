import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash
from config import ADMIN_PASSWORD, SECRET_KEY
from database import add_entry, get_all, delete_entry, update_entry
from tmdb import search_tmdb

app = Flask(__name__,
    template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'),
    static_folder=os.path.join(os.path.dirname(__file__), '..', 'static')
)

app.secret_key = SECRET_KEY

ALLOWED_ENTRY_TYPES = {"Movie", "TV Show"}
ALLOWED_STATUSES = {"Watched", "Want to Watch"}
MIN_RATING = 1
MAX_RATING = 10
MAX_TITLE_LENGTH = 200


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


@app.route("/")
def index():
    entries = get_all()
    return render_template("index.html", entries=entries, logged_in=session.get("logged_in", False))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("index"))
    if request.method == "POST":
        typed = request.form.get("password")
        if typed == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        flash("Incorrect password.")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/add", methods=["POST"])
def add():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    values, errors = _validated_entry_form(include_title=True)
    if errors:
        for error in errors:
            flash(error)
        return redirect(url_for("index"))
    title = values["title"]
    entry_type = values["entry_type"]
    status = values["status"]
    rating = values["rating"]
    result = search_tmdb(title)
    if result:
        full_title = result["full_title"]
        poster_url = result["poster_url"]
    else:
        full_title = title
        poster_url = ""
    add_entry(full_title, entry_type, status, rating, poster_url)
    return redirect(url_for("index"))


@app.route("/edit/<int:entry_id>", methods=["POST"])
def edit(entry_id):
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    values, errors = _validated_entry_form()
    if errors:
        for error in errors:
            flash(error)
        return redirect(url_for("index"))
    updated = update_entry(entry_id, values["status"], values["rating"])
    if not updated:
        flash("Entry not found.")
    return redirect(url_for("index"))


@app.route("/delete/<int:entry_id>", methods=["POST"])
def delete(entry_id):
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    deleted = delete_entry(entry_id)
    if not deleted:
        flash("Entry not found.")
    return redirect(url_for("index"))
