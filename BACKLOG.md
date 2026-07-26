# Movie Tracker Backlog

This is the working source of truth for improving the project. Before starting a
task, review this file and choose the highest-priority unblocked item. After
each work session, update the checkbox, notes, evidence, and any newly exposed
follow-up work here.

## Product goal

Turn the project from a conventional TMDB watchlist CRUD app into a reliable,
security-conscious application with one genuinely non-trivial engineering
capability and evidence that people actually use it.

## Definition of done

- [ ] The deployment target, runtime entrypoint, environment variables, and
      database setup agree with the code.
- [ ] Authentication, authorization, validation, CSRF protection, and external
      API handling are implemented and tested.
- [ ] One differentiating feature is productionized, explainable, and tested;
      it is not presented as ML or data engineering without evaluation or
      historical data to support that claim.
- [ ] A dated, privacy-conscious usage summary is backed by real measurements.
- [ ] The architecture and tradeoffs are documented accurately.
- [ ] README, tests, deployment evidence, and known limitations are current.

## Current state and known gaps

- The Flask application is defined in `api/index.py`; `vercel.json` routes to
  that file and the stale Render `Procfile` has been removed.
- The README now identifies Vercel as canonical and marks the live deployment
  URL and dated verification status; the current production smoke test found a
  500 public view and a missing `/healthz` route.
- The application uses `ADMIN_PASSWORD` and a Flask signed session. It does
  not currently integrate Supabase Auth.
- The database layer uses direct `psycopg2` connections. There is no tracked
  migration establishing the claimed RLS policies, and the README example
  refers to `items` while the application table is `entries`. Tracked
  migrations now define the `entries` table and validation constraints.
- The Supabase `movie-tracker` project was restored from inactive status and is
  now healthy; its shared pooler still rejects the `postgres.<project-ref>`
  tenant used by Vercel, so database-backed production routes remain blocked.
- `init_db()` exists but is not called by the application. Deployments must
  apply the tracked migrations or provision the schema explicitly.
- There is no automated test suite.
- Rating and status values are accepted from request data with minimal
  validation; TMDB requests have no timeout, explicit status handling, or
  caching/rate limiting.

## P0 — Make the existing project truthful and reliable

### Deployment and runtime

- [x] Decide whether the canonical deployment is Vercel or Render. Vercel is
      canonical because `vercel.json`, `api/index.py`, and the latest migration
      commits are Vercel-oriented; live verification remains a separate task.
- [x] Align the deployment configuration with that decision: `vercel.json`
      routes to `api/index.py`, whose Flask configuration resolves the shared
      templates and static directories. Required environment variables remain
      a separate configuration task.
- [x] Remove or correct the stale deployment configuration for the non-canonical
      platform by deleting the broken Render `Procfile`.
- [x] Add a lightweight `/healthz` endpoint that reports application liveness
      without exposing secrets or requiring a full watchlist query. The focused
      Flask test-client check passed with HTTP 200 and `{"status":"ok"}`.
- [ ] Complete the deployed-URL smoke test covering public view, login, one
      authorized write path, and unauthorized write rejection. Partial evidence
      was collected on 2026-07-26: `/login` returned 200, invalid login showed
      the expected error, anonymous `POST /add` returned 302 to `/login`, `/`
      returned 500, and `/healthz` returned 404. The authorized write was not
      attempted because production is not healthy and no rollback fixture is
      verified.
- [x] Record deployment URL, production deployment commit SHA, verification
      date, and manual verification limits in the README. The current record is
      for `https://movie-tracker-umber-sigma.vercel.app`, source commit
      `ac5f7633577c44e046fa605f7c3bf266525faa2c`, and deployment `5112547143`.
- [ ] Repair the production deployment/database configuration, redeploy the
      repaired application, and repeat the complete smoke test with a
      reversible authorized-write fixture.
      - [x] Restored Supabase project `vgirgwxehcsxloclanhf` from inactive status.
      - [x] Provisioned `public.entries` and verified the three
            rating/type/status constraints. A direct SQL count found 9 existing
            entries; the smoke-marker query found 0 test rows, so production
            data was preserved and no smoke fixture was left behind.
      - [x] Added tracked migrations under `supabase/migrations/` and deployed
            the current branch as Vercel production deployment
            `dpl_CtQEiNgpFMwVewmvKMWpVTZkacy1`.
      - [ ] Repair or refresh the Supavisor tenant mapping/connection string;
            both local and Vercel attempts still receive
            `ENOTFOUND tenant/user postgres.vgirgwxehcsxloclanhf`. A
            read-only variant check on 2026-07-26 produced the same tenant
            error for the project-qualified user on ports 6543 and 5432;
            using plain `postgres` instead produced
            `ENOIDENTIFIER no tenant identifier provided` on both ports.
            The direct database host works locally but cannot be used by
            Vercel because its IPv6 connection fails there.
      - [ ] Repeat the public-view and reversible authorized-write checks after
            the pooler connection is healthy.

### Configuration and database setup

- [x] Add a documented `.env.example` covering `SECRET_KEY`,
      `ADMIN_PASSWORD`, `DATABASE_URL`, and `TMDB_API_KEY` without real
      credentials. `.gitignore` explicitly allows the example, and the README
      explains copying it to the ignored local `.env` file.
- [x] Fail fast when required production configuration is missing; remove the
      `dev-fallback-key` and `changeme` production fallbacks. `config.py` now
      validates `SECRET_KEY`, `ADMIN_PASSWORD`, `DATABASE_URL`, and
      `TMDB_API_KEY` before the application modules finish importing.
- [x] Choose a reproducible schema workflow: tracked Supabase SQL migrations
      created with the Supabase CLI. Remote migration-history synchronization
      remains a follow-up after the provider connection is repaired.
- [x] Define the `entries` schema with constraints for allowed status, rating
      range, non-empty title, and valid entry type. The production table and
      rating/type/status constraints were verified on 2026-07-26; non-empty
      title and nullability hardening for an existing table remain separate
      follow-up work.
- [ ] Decide whether `init_db()` should be removed in favor of migrations or
      retained as a clearly scoped local-development bootstrap.
- [ ] Add indexes and a connection strategy appropriate for the deployment
      environment; document whether direct Postgres connections or a Supabase
      API/pooler are used.
- [ ] Define failure behavior and transaction cleanup for database errors.

### Request validation and application behavior

- [ ] Validate title length and non-empty input server-side.
- [ ] Validate `entry_type`, `status`, and rating against allowlists and bounds;
      return a useful form error instead of a 500 on malformed input.
- [ ] Handle missing or invalid entry IDs consistently and return an appropriate
      response when an update/delete affects no row.
- [ ] Add user-visible error states for database and TMDB failures.
- [ ] Preserve the selected entry type correctly when TMDB returns mixed movie
      and TV results, or use TMDB's returned media type intentionally.
- [ ] Add safe escaping and length limits before introducing any free-text
      review or note fields.

### External TMDB integration

- [ ] Add a finite request timeout and call `raise_for_status()` or equivalent
      response validation.
- [ ] Handle TMDB quota, authentication, malformed JSON, and network failures
      separately enough to make operational diagnosis possible.
- [ ] Add server-side rate limiting and caching for repeated title searches;
      protect TMDB quota rather than exposing the API key to browsers.
- [ ] Store TMDB IDs and relevant metadata needed by the chosen differentiating
      feature, not only the display title and poster URL.
- [ ] Document TMDB attribution, API-key boundaries, and data-refresh behavior.

### Authentication and security baseline

- [ ] Decide between Supabase Auth and a deliberately hardened single-admin
      authentication flow.
- [ ] If using Supabase Auth, integrate identity/session verification with the
      Flask routes and make database policies use the same identity boundary.
- [ ] If retaining custom auth, store a password hash rather than a plaintext
      environment password and add secure credential rotation guidance.
- [ ] Add CSRF protection to login, logout, add, edit, and delete forms.
- [ ] Set secure, HTTP-only, and appropriate SameSite session-cookie settings in
      production; rotate the Flask secret when required.
- [ ] Add login throttling or rate limiting and avoid revealing unnecessary
      authentication details in responses.
- [ ] Add authorization tests proving public reads, rejected anonymous writes,
      and accepted authenticated writes.
- [ ] Either implement and test actual RLS policies for the chosen access path,
      or remove the RLS claim from the README until it is reproducible.
- [ ] Check dependency versions and add a repeatable dependency/update process.

### Automated verification

- [ ] Add a test runner and test layout.
- [ ] Test application import and route registration without requiring a live
      database or TMDB key.
- [ ] Test login success/failure, session logout, and authorization guards.
- [ ] Test add/edit/delete with mocked database calls and valid/invalid input.
- [ ] Test TMDB success, no-result, timeout, non-2xx, and malformed-response
      behavior.
- [ ] Add a CI job for tests, linting/format checks, and dependency failure
      visibility.

## P1 — Add one real differentiator

Choose one track. Do not implement both unless the first one is complete and
the project still has a clear product reason for the second.

### Track A: explainable content-based recommendations

- [ ] Decide the recommendation contract: recommended unseen titles, a reason
      for each recommendation, and a cold-start fallback.
- [ ] Extend the schema to retain TMDB IDs, media type, genres, keywords or
      other reproducible features, and the user's interaction/status data.
- [ ] Build a deterministic feature-extraction and normalization pipeline.
- [ ] Implement cosine similarity or an equivalent transparent baseline.
- [ ] Exclude titles already watched or already on the watchlist.
- [ ] Add an explanation such as “recommended because it shares genres with…”.
- [ ] Expose recommendations through a tested Flask route and a focused UI
      section with loading, empty, and error states.
- [ ] Add a cold-start strategy for a new or sparse watch history.
- [ ] Evaluate the recommender with a small offline holdout, precision@k, or a
      similarly stated metric; document the limitations of the evaluation.
- [ ] Add tests for feature extraction, ranking, filtering, explanations, and
      deterministic output.
- [ ] Document that this is a content-based baseline, not a claimed deep-learning
      system.

### Track B: streaming-availability history pipeline

- [ ] Choose a legitimate, documented availability data source and confirm its
      terms, regional coverage, and request limits.
- [ ] Define a time-series schema for titles, providers, regions, snapshots,
      and observed availability changes.
- [ ] Add uniqueness/idempotency rules so a repeated job does not duplicate
      snapshots.
- [ ] Implement a scheduled job with retries, exponential backoff, timeout,
      rate-limit handling, and observable failures.
- [ ] Store historical observations rather than only the latest availability.
- [ ] Add a change/history view showing when a title appeared or disappeared
      from a provider.
- [ ] Add tests for idempotent runs, partial provider failure, stale data, and
      rate-limit responses.
- [ ] Document data freshness, regional limitations, and source attribution.

## P2 — Prove real usage

- [ ] Decide which privacy-conscious usage events are necessary; do not collect
      more personal data than the project needs.
- [ ] Add measurement for meaningful events such as public visits, successful
      additions, recommendation views, or availability-history views.
- [ ] Do not call a single-admin watchlist “N registered users”; implement
      multi-user accounts first if registered-user counts are desired.
- [ ] Recruit 5–10 real testers and record structured feedback about the core
      flow and differentiating feature.
- [ ] Fix the highest-value usability issues found by testers.
- [ ] Publish a dated usage summary in the README with exact numbers and a
      short explanation of how they were measured.
- [ ] Add a privacy note and opt-out or consent behavior if analytics are
      externally hosted.
- [ ] Keep screenshots or a short demo recording that matches the verified
      deployed commit.

## P3 — Architecture, documentation, and operational evidence

- [ ] Create `docs/architecture.md` with a diagram of the actual request,
      authentication, database, and TMDB flows.
- [ ] Explain why the chosen database/auth approach fits this project and name
      one accepted tradeoff with its scaling consequence.
- [ ] Document trust boundaries: browser, Flask server, database, auth system,
      and TMDB credentials.
- [ ] Document the chosen differentiating feature's data model, algorithm or
      scheduled pipeline, and failure modes.
- [ ] Add a local setup guide that includes environment variables, schema setup,
      development start command, and test command.
- [ ] Update README features only after each feature is verified in code.
- [ ] Replace example RLS SQL with the actual tracked migration and table names,
      or remove the section until that migration exists.
- [ ] Add a known-limitations section covering single-admin versus multi-user
      scope, recommendation/data-source limits, TMDB dependency, and deployment
      constraints.
- [ ] Add a small operations/runbook section for migrations, secret rotation,
      scheduled jobs, logs, and rollback.
- [ ] Link the backlog, architecture document, verification evidence, and live
      demo from the README.

## P4 — Quality and release polish

- [ ] Check keyboard navigation, visible focus, form labels, modal behavior, and
      error announcements.
- [ ] Verify responsive behavior at narrow mobile and desktop widths.
- [ ] Add useful empty/loading/error states for the core and differentiating
      feature flows.
- [ ] Add structured logging that excludes passwords, API keys, and session
      contents.
- [ ] Add database backup/export guidance appropriate to the chosen provider.
- [ ] Run a release checklist: tests, dependency audit, secret scan, deployment
      smoke test, README accuracy, and accessibility review.
- [ ] Create a logical feature-branch commit history and open a reviewable PR;
      do not merge directly to `main` without explicit approval.

## Evidence log

Record verification here as work lands. Prefer commands, test results, commit
SHAs, URLs, dates, and screenshots over subjective claims.

| Date | Area | Evidence | Result / follow-up |
|---|---|---|---|
| 2026-07-26 | Baseline inspection | Repository review of `api/index.py`, `database.py`, `tmdb.py`, `Procfile`, `vercel.json`, and `readme.md` | Deployment, auth/RLS, schema setup, validation, and test gaps recorded above |
| 2026-07-26 | Deployment alignment | `vercel.json`, `api/index.py`, README, and removal of `Procfile` | Vercel is the only documented/configured target; live smoke verification remains open |
| 2026-07-26 | Health endpoint | `venv\\Scripts\\python.exe` Flask test client against `GET /healthz` | Passed: HTTP 200 with `{"status":"ok"}`; live deployment check remains open |
| 2026-07-26 | Production smoke test | `https://movie-tracker-umber-sigma.vercel.app`; GitHub deployment `5112547143`; source `ac5f7633577c44e046fa605f7c3bf266525faa2c` | Partial: `/login` 200, invalid login rejected, anonymous add redirected, `/` 500, `/healthz` 404; authorized write deferred until repair |
| 2026-07-26 | Production repair | Supabase project `vgirgwxehcsxloclanhf`, direct SQL verification, Vercel deployment `dpl_CtQEiNgpFMwVewmvKMWpVTZkacy1` | Project is `ACTIVE_HEALTHY`; `public.entries` exists with 9 existing rows, 0 smoke-marker rows, and the three checks; `/healthz` is 200, but database routes still 500 because Supavisor rejects the tenant/user identity |
| 2026-07-26 | Pooler diagnosis | Local tests of project-qualified/plain users on Supavisor ports 6543 and 5432; Vercel preview test with the direct database host | Project-qualified user returns `ENOTFOUND tenant/user`; plain user returns `ENOIDENTIFIER`; direct host succeeds locally but fails from Vercel on IPv6. Provider Connect settings or tenant mapping must be refreshed before another deployment attempt |
| 2026-07-26 | Environment template | `.env.example`, `.gitignore`, README local setup, `git diff --check` | Passed: all four runtime variables are documented with placeholders; the example is trackable while `.env` remains ignored |
| 2026-07-26 | Configuration fail-fast | `venv\Scripts\python.exe` compile check; configured app import; import with all four variables intentionally empty | Passed: configured Flask import succeeds; missing configuration exits with `Missing required environment variable: SECRET_KEY`; no runtime fallback values remain |

## Decisions

Record decisions that affect scope here so future work does not reopen settled
questions without new evidence.

- Canonical deployment: Vercel; live verification remains open
- Authentication model: _undecided_
- Differentiator track: _undecided_
- Usage measurement approach: _undecided_
