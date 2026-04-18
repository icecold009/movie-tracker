import hmac
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
from database import add_entry, get_all, delete_entry, update_entry
from tmdb import search_tmdb

load_dotenv()

_secret_key = os.getenv("SECRET_KEY")
_admin_password = os.getenv("ADMIN_PASSWORD")

if not _secret_key:
    raise RuntimeError("SECRET_KEY environment variable is not set")
if not _admin_password:
    raise RuntimeError("ADMIN_PASSWORD environment variable is not set")

app = Flask(__name__)
app.secret_key = _secret_key
ADMIN_PASSWORD = _admin_password

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    # Use Redis in production (set REDIS_URL env var) for cross-process rate limiting.
    # Falls back to in-memory storage for local development (limits are per-process only).
    storage_uri=os.getenv("REDIS_URL", "memory://"),
)


@app.route("/")
def index():
    entries = get_all()
    return render_template("index.html", entries=entries, logged_in=session.get("logged_in", False))


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if session.get("logged_in"):
        return redirect(url_for("index"))
    if request.method == "POST":
        typed = request.form.get("password", "")
        if hmac.compare_digest(typed.encode(), ADMIN_PASSWORD.encode()):
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
    title = request.form.get("title", "").strip()
    entry_type = request.form.get("entry_type", "Movie")
    status = request.form.get("status", "Watched")
    rating = int(request.form.get("rating", 7))
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
    status = request.form.get("status", "Watched")
    rating = int(request.form.get("rating", 7))
    update_entry(entry_id, status, rating)
    return redirect(url_for("index"))


@app.route("/delete/<int:entry_id>", methods=["POST"])
def delete(entry_id):
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    delete_entry(entry_id)
    return redirect(url_for("index"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)