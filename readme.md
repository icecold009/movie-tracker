# 🎬 My Watch Tracker

A personal web app to track movies and TV shows I've watched or want to watch.
Movies and TV Shows are displayed in separate sections. Cover art is auto-fetched from TMDB using an API.
Built with Flask + PostgreSQL, with Vercel as the canonical deployment target. Only the admin session can add, edit, or delete entries.

Live deployment: https://movie-tracker-umber-sigma.vercel.app

## Deployment verification

Last checked: **2026-07-26** against the Vercel production alias. The latest
GitHub production deployment record points to commit `ac5f7633577c44e046fa605f7c3bf266525faa2c`
(deployment `5112547143`, created 2026-06-18).

- `/login`: HTTP 200; invalid-password handling returned the expected error.
- Anonymous `POST /add`: HTTP 302 to `/login`; no write was attempted without a
  session.
- `/`: HTTP 500; the public database-backed view is not currently healthy.
- `/healthz`: HTTP 404; the deployed version predates the health endpoint on the
  current branch.
- An authorized write was not attempted because the deployed public view is
  failing and there is no verified rollback fixture for production data.

The deployment is therefore **not release-ready**. Repeat the full smoke test
after redeploying the repaired application, including a reversible authorized
write check.

### Latest repair attempt — 2026-07-26

The Supabase project was restored from inactive status, and the `entries` table
plus rating/type/status constraints were provisioned. The current branch was
deployed as Vercel production deployment `dpl_CtQEiNgpFMwVewmvKMWpVTZkacy1`;
`/healthz` now returns HTTP 200. Database-backed routes still return HTTP 500
because Supavisor rejects tenant/user `postgres.vgirgwxehcsxloclanhf`. The
provider connection identity must be refreshed or repaired before the full
smoke test can pass.

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
| Hosting | Vercel (Python function) |
| Runtime | Vercel Python runtime |

## Local Setup

```bash
git clone https://github.com/YOUR_USERNAME/movie-tracker.git
cd movie-tracker

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

Copy `.env.example` to `.env` and replace every placeholder with a local
secret or service credential. Keep `.env` untracked; production values belong
in Vercel's encrypted environment variables.

For Vercel, `DATABASE_URL` should use the Supabase Shared Pooler
transaction-mode connection (port `6543`) from the project's Connect settings.
The Flask database client uses a five-second connection timeout; the current
production pooler tenant-mapping issue is recorded above and in `BACKLOG.md`.

TMDB searches use a five-minute in-process cache and limit uncached searches to
30 requests per minute per warm application instance. This protects quota on a
single instance; a shared cache/rate-limit store would be required for global
enforcement across scaled serverless instances.

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
