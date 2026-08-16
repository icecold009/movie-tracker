# Note on how this project was built

I built a substantial part of this project myself, including the application
structure, data-model decisions, deterministic content-based recommender, and
the password-hash plus signed-session authentication model. I also use an AI
coding agent for a significant share of implementation, but I set the rules
below and review the resulting diffs, tests, and stated limitations myself.

I wrote these rules after deciding that generated code must never be treated as
verified without current evidence. That decision taught me to separate local
tests, CI, browser checks, and live deployment claims, and to keep provider and
security boundaries explicit. The `recommendations.py` rewrite in commit
`a679899` was an AI-assisted verification and restructuring pass for the parts
I was least sure I understood; it was not an independent no-AI exercise.

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
- The current application uses `ADMIN_PASSWORD_HASH` and a Flask signed
  session. It does not currently integrate Supabase Auth.
- The database layer uses direct `psycopg2` connections with a five-second
  connect timeout. Vercel is intended to use the Supabase Shared Pooler
  transaction-mode URL. The current database has RLS enabled on public tables,
  but no tracked migration or tested policy aligns row authorization with the
  Flask session, so do not claim Flask-session-backed RLS. Database operations
  use a shared transaction context that commits on success and rolls
  back/closes resources on failure.
- Database failures are converted to a safe `DatabaseError`; public reads use
  HTTP 503 with an empty-state message, while authorized mutations flash a
  retryable error without exposing driver details.
- TMDB search uses a five-minute in-process cache and a 30-per-minute limit on
  uncached searches per warm instance; do not describe this as distributed
  quota enforcement without adding shared state.
- Schema creation is owned by the tracked migrations under
  `supabase/migrations/`; the obsolete `init_db()` bootstrap was removed so it
  cannot create a weaker competing `entries` schema. Do not assume a fresh
  deployment has applied the migrations.
- The Supabase `movie-tracker` project is currently `ACTIVE_HEALTHY`, and the
  canonical Vercel routes are database-backed and returning 200. A current
  project SQL check reports the `postgres` database role on port 5432; that is
  not proof of the encrypted Vercel `DATABASE_URL` pooler identity. Re-read the
  current Connect string and reconcile it with Vercel before claiming the
  connection configuration is fully verified.
- The current remote migration history contains four rows, while the tracked
  branch contains five migration files and uses a different timestamp for the
  initial/constraint history. Do not mark migration parity complete until that
  mismatch is explicitly reconciled.
- A pytest suite and CI workflow are tracked. The 2026-08-16 audit branch run
  passed 61 tests, Ruff, compilation, pip check, JavaScript syntax, and diff
  checks; keep later claims tied to a current branch and commit.

## Environment and security

Expected environment variables are `SECRET_KEY`, `ADMIN_PASSWORD_HASH`,
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
