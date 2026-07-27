# 🎬 My Watch Tracker

A personal web app to track movies and TV shows I've watched or want to watch.
Movies and TV Shows are displayed in separate sections. Cover art is auto-fetched from TMDB using an API.
Built with Flask + PostgreSQL, with Vercel as the canonical deployment target. Only the admin session can add, edit, or delete entries.

Live deployment: https://movie-tracker-umber-sigma.vercel.app

## Deployment verification

Full smoke check: **2026-07-26** against the Vercel production alias. The latest
GitHub production deployment record points to commit `ac5f7633577c44e046fa605f7c3bf266525faa2c`
(deployment `5112547143`, created 2026-06-18).

- `/login`: HTTP 200; invalid-password handling returned the expected error.
- Anonymous `POST /add`: HTTP 302 to `/login`; no write was attempted without a
  session.
- `/`: HTTP 500; the public database-backed view is not currently healthy.
- An authorized write was not attempted because the deployed public view is
  failing and there is no verified rollback fixture for production data.

Latest live probe: **2026-07-27**. `/healthz` returned HTTP 200 with
`{"status":"ok"}`, while `/` still returned HTTP 500. This confirms liveness
but does not establish database-backed production health.

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

The implementation also includes an explainable content-based recommendation
baseline; focused tests and code review are tracked, while runtime execution
and production usage remain unverified.

- 🎨 Rate 1–10 with a colour-coded bar (red → yellow → green)
- 📋 Track status: **Watched** or **Want to Watch**
- 🎬 Movies and 📺 TV Shows displayed in separate sections
- ✎ Edit rating and status on any entry
- ✕ Delete any entry
- 🌐 Public view - anyone can see the watchlist
- 🔐 Password-protected admin - only the owner can add, edit, or delete
- Database-level authorization is not currently claimed; the Flask server is
  the only documented mutation boundary until a matching RLS policy is tested.

The current known limitations are:

- Authentication is a single-admin Flask session, not a multi-user account
  system; Supabase Auth and RLS are not integrated.
- Recommendations are a deterministic content-based baseline. They depend on
  TMDB and stored genre metadata, use a sparse-history popular fallback, and
  have no real production precision metric yet.
- TMDB caching and rate limiting are per warm serverless instance, not global.
- The Vercel database-backed routes remain blocked by the unresolved Supavisor
  tenant mapping; `/healthz` liveness does not prove the watchlist works.
- Usage counters are aggregate first-party events, not registered-user counts;
  this remains a single-admin application.

See the [backlog](BACKLOG.md), [verification record](docs/verification.md),
[architecture](docs/architecture.md), [local development guide](docs/local-development.md),
[operations runbook](docs/operations.md), and [usage measurement decision](docs/usage-measurement.md)
for current procedures and limits.
The [live deployment](https://movie-tracker-umber-sigma.vercel.app) is the
canonical demo, subject to the limitations in the verification record.

### Privacy and measurement

The application does not use an external analytics provider. It stores only
daily aggregate counts for successful public views, adds, and recommendation
views; it does not store IP addresses, user agents, referrers, account IDs, or
browser identifiers. These counters describe activity, not registered users.

## Tech Stack

| Layer | Tool |
|---|---|
| Language | Python 3.10+ |
| Framework | Flask |
| Database | PostgreSQL (Supabase) |
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

Run the automated checks with:

```bash
python -m pytest
```

Direct dependencies are pinned in `requirements.txt`; the update workflow is
documented in `docs/dependency-update.md`.

Copy `.env.example` to `.env` and replace every placeholder with a local
secret or service credential. Keep `.env` untracked; production values belong
in Vercel's encrypted environment variables.

`ADMIN_PASSWORD_HASH` must contain a Werkzeug password hash rather than the
plaintext admin password. Generate one interactively with:

```bash
python -c "from getpass import getpass; from werkzeug.security import generate_password_hash; print(generate_password_hash(getpass('Admin password: ')))"
```

For credential rotation, generate a new hash, replace `ADMIN_PASSWORD_HASH` in
the local or Vercel environment, and redeploy. Do not retain or document the
old plaintext password.

The Flask session cookie is HTTP-only and `SameSite=Lax`; Vercel and other
production environments also set the cookie `Secure` flag. Rotating
`SECRET_KEY` invalidates existing signed sessions and requires administrators
to log in again.

For Vercel, `DATABASE_URL` should use the Supabase Shared Pooler
transaction-mode connection (port `6543`) from the project's Connect settings.
The Flask database client uses a five-second connection timeout; the current
production pooler tenant-mapping issue is recorded above and in `BACKLOG.md`.

TMDB searches use a five-minute in-process cache and limit uncached searches to
30 requests per minute per warm application instance. This protects quota on a
single instance; a shared cache/rate-limit store would be required for global
enforcement across scaled serverless instances.

### TMDB attribution and data boundaries

This product uses the [TMDB API](https://www.themoviedb.org/) but is not
endorsed or certified by TMDB. TMDB supplies title metadata and poster images;
the application does not expose `TMDB_API_KEY` to browsers. Search and discovery
responses are cached for five minutes per warm application instance, and newly
added entries persist the selected TMDB ID, media type, and genre IDs for the
recommendation baseline. Existing entries are not silently refreshed, so stale
or missing metadata can leave recommendations in the documented cold-start
state. See TMDB's [API FAQ](https://developer.themoviedb.org/docs/faq) for the
current attribution and API-use requirements.

## Database Security

RLS is not currently claimed for this Flask session and direct-Postgres access
path. Add and test a policy that matches the actual identity boundary before
documenting database-level row authorization.
