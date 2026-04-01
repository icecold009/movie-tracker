# 🎬 My Watch Tracker

A personal web app to track movies and TV shows I've watched or want to watch.
Movies and TV Shows are displayed in separate sections. Cover art is auto-fetched from TMDB using an API.
Built with Flask + PostgreSQL, hosted publicly on Render — only I can add, edit, or delete entries.

![screenshot](screenshot.png)

## Features

- 🔍 Search any movie or TV show — cover art pulled automatically from TMDB
- 🎨 Rate 1–10 with a colour-coded bar (red → orange → yellow → green)
- 📋 Track status: **Watched** or **Want to Watch**
- 🎬 Movies and 📺 TV Shows displayed in separate sections
- ✎ Edit rating and status on any entry
- ✕ Delete any entry
- 🌐 Public view — anyone can see the watchlist
- 🔐 Password-protected admin — only the owner can add, edit, or delete

## Tech Stack

| Layer | Tool |
|---|---|
| Language | Python 3.10+ |
| Framework | Flask |
| Database | PostgreSQL (Supabase free tier) |
| Cover Art | TMDB API (free) |
| Hosting | Render (free web service) |
| Server | Gunicorn |

## Local Setup

```bash
git clone https://github.com/YOUR_USERNAME/movie-tracker.git
cd movie-tracker

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

Create a `.env` file:
