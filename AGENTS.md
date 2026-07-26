# Repository guidance

## Project

Movie Tracker is a small Flask application for publicly viewing a personal
movie/TV watchlist. The current implementation stores entries in PostgreSQL,
looks up titles and posters through TMDB, and uses server-rendered Jinja
templates.

Current application locations:

- Flask app and routes: `api/index.py`
- Database access: `database.py`
- TMDB integration: `tmdb.py`
- Templates: `templates/`
- Styles: `static/style.css`
- Vercel configuration: `vercel.json`
- Work source of truth: `BACKLOG.md`

## Working protocol

- Review `BACKLOG.md` before starting work and select the highest-priority
  unblocked task.
- Work on one backlog change at a time. Update the backlog with status and
  evidence when that task is complete.
- Use a separate feature branch for repository work.
- Do not commit or merge directly into `main` without explicit approval.
- Keep commits logical and scoped; do not combine unrelated backlog items.
- Do not claim deployment, usage, authentication, RLS, or test results without
  current evidence.

## Current decisions and boundaries

- Vercel is the canonical deployment target. `vercel.json` routes requests to
  `api/index.py`.
- The stale Render `Procfile` has been removed. Do not reintroduce a second
  deployment target without updating the canonical-deployment decision.
- The current application uses `ADMIN_PASSWORD` and a Flask signed session. It
  does not currently integrate Supabase Auth.
- The database layer uses direct `psycopg2` connections with a five-second
  connect timeout. Vercel is intended to use the Supabase Shared Pooler
  transaction-mode URL; Supabase RLS is documented but not yet reproducibly
  established by a tracked migration or proven to align with the Flask
  session. Database operations use a shared transaction context that commits
  on success and rolls back/closes resources on failure.
- Database failures are converted to a safe `DatabaseError`; public reads use
  HTTP 503 with an empty-state message, while authorized mutations flash a
  retryable error without exposing driver details.
- Schema creation is owned by the tracked migrations under
  `supabase/migrations/`; the obsolete `init_db()` bootstrap was removed so it
  cannot create a weaker competing `entries` schema. Do not assume a fresh
  deployment has applied the migrations.
- The Supabase `movie-tracker` project was restored from inactive status and its
  database is healthy, but the shared pooler currently rejects the
  `postgres.<project-ref>` tenant used by Vercel. Treat this as a provider-side
  connection configuration blocker until the current Connect-string identity is
  verified.
- There is currently no automated test suite. New behavior should include tests
  before being described as verified.

## Environment and security

Expected environment variables are `SECRET_KEY`, `ADMIN_PASSWORD`,
`DATABASE_URL`, and `TMDB_API_KEY`. Keep real values in the local ignored `.env`
or deployment secret store; never commit them or copy them into documentation.

The existing fallback values for the Flask secret and admin password are not
acceptable production configuration. Future work must remove them or fail fast
when required production secrets are missing.

When changing request-handling code, preserve or add:

- server-side validation and allowlists for title, type, status, and rating;
- authorization checks on every mutating route;
- CSRF protection for state-changing forms;
- secure HTTP-only and appropriate SameSite session-cookie settings;
- TMDB timeouts, response validation, caching, and quota protection; and
- error handling that does not expose credentials or session contents.

## Data model notes

The current database code expects an `entries` table with fields for `id`,
`title`, `entry_type`, `status`, `rating`, `poster_url`, and `added_on`.
Schema creation is represented by tracked migrations under `supabase/migrations/`.
Any future schema change should add constraints, indexes, and a reproducible
migration path rather than relying on `init_db()` or an undocumented dashboard
operation.

## Verification expectations

For code changes, use the narrowest relevant checks and report what was and was
not verified. At minimum, inspect `git diff --check`; when tests exist, run the
focused tests before broader checks. Separate automated checks from live,
browser, accessibility, and production evidence.

For deployment or documentation claims, record the relevant URL, commit SHA,
date, command or test output, and known limitations in `BACKLOG.md` or the
appropriate documentation.
