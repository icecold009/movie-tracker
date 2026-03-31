import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from dotenv import load_dotenv
from database import add_entry, get_all, delete_entry, update_entry
from tmdb import search_tmdb

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-fallback-key")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")


@app.route("/")
def index():
    entries = get_all()
    return render_template("index.html", entries=entries, logged_in=session.get("logged_in", False))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("index"))
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
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