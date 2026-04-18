# 🎬 My Watch Tracker

A personal web app to track movies and TV shows I've watched or want to watch.
Movies and TV Shows are displayed in separate sections. Cover art is auto-fetched from TMDB using an API.
Built with Flask + PostgreSQL, hosted publicly on Render and only I can add, edit, or delete entries.

https://movie-tracker-uynj.onrender.com

## Features

- 🎨 Rate 1–10 with a colour-coded bar (red → yellow → green)
- 📋 Track status: **Watched** or **Want to Watch**
- 🎬 Movies and 📺 TV Shows displayed in separate sections
- ✎ Edit rating and status on any entry
- ✕ Delete any entry
- 🌐 Public view - anyone can see the watchlist
- 🔐 Password-protected admin - only the owner can add, edit, or delete
- 🛡️ **Row Level Security (RLS)** - Database-level protection ensuring only authenticated requests can modify data

## Tech Stack

| Layer | Tool |
|---|---|
| Language | Python 3.10+ |
| Framework | Flask |
| Database | PostgreSQL (Supabase) + **Row Level Security (RLS)** |
| Cover Art | TMDB API (free) |
| Hosting | Render (free web service) |
| Server | Gunicorn |

## Local Setup

```bash
git clone https://github.com/icecold009/movie-tracker.git
cd movie-tracker

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

## 🛡️ Database Security (RLS)

I recently implemented **Row Level Security** on the PostgreSQL database to add an extra layer of protection. This ensures that even if the API keys were exposed, the database itself restricts who can modify the records.

I used the following SQL logic to manage access:
* **SELECT:** Allowed for everyone (public access).
* **INSERT/UPDATE/DELETE:** Restricted to the `authenticated` role only.

```sql
-- Example of the policy used
ALTER TABLE items ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read-only" 
ON items FOR SELECT USING (true);

CREATE POLICY "Allow admin to edit" 
ON items FOR ALL 
TO authenticated 
USING (auth.role() = 'authenticated');
