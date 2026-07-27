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
- The README now identifies Vercel as canonical and records the 2026-07-27 live
  smoke check: `/healthz`, `/`, and `/login` return 200 and anonymous writes
  redirect to `/login`.
- The application uses `ADMIN_PASSWORD_HASH` and a Flask signed session. It
  does not currently integrate Supabase Auth.
- The database layer uses direct `psycopg2` connections. There is no tracked
  migration establishing RLS policies aligned with the Flask session; the
  README now makes no RLS claim. Tracked migrations define the `entries` table
  and validation constraints.
- The Supabase `movie-tracker` project was restored from inactive status and is
  now healthy; the current transaction-pooler configuration is working in the
  Vercel production deployment.
- Schema creation is owned by the tracked migrations; deployments must apply
  them or provision the schema explicitly before serving database-backed
  routes.
- A pytest suite and CI workflow are tracked. Local `pip check`, compilation,
  Ruff, and pytest now pass with 41 tests; PR #3 checks also passed across
  Python 3.10, 3.12, and 3.14.
- TMDB requests now have bounded timeout, HTTP/JSON validation, safe error
  handling, five-minute caching, and per-warm-instance rate limiting.

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
- [x] Complete the deployed-URL smoke test covering public view, login, one
      authorized write path, and unauthorized write rejection. On 2026-07-27,
      `/healthz`, `/`, and `/login` returned 200, anonymous `POST /add` returned
      302 to `/login`, and the user confirmed a reversible authorized add/delete
      check.
- [x] Record deployment URL, production deployment commit SHA, verification
      date, and manual verification limits in the README. The current record is
      for `https://movie-tracker-umber-sigma.vercel.app`, source commit
      `ac5f7633577c44e046fa605f7c3bf266525faa2c`, and deployment `5112547143`.
- [x] Repair the production deployment/database configuration, redeploy the
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
      - [x] Refresh the production environment with the current Supabase
            transaction-pooler connection string and required
            `ADMIN_PASSWORD_HASH`; the post-merge production smoke check passed.
      - [x] Repeat the public-view and reversible authorized-write checks after
            the pooler connection is healthy.

### Configuration and database setup

- [x] Add a documented `.env.example` covering `SECRET_KEY`,
      `ADMIN_PASSWORD_HASH`, `DATABASE_URL`, and `TMDB_API_KEY` without real
      credentials. `.gitignore` explicitly allows the example, and the README
      explains copying it to the ignored local `.env` file.
- [x] Fail fast when required production configuration is missing; remove the
      `dev-fallback-key` and `changeme` production fallbacks. `config.py` now
      validates `SECRET_KEY`, `ADMIN_PASSWORD_HASH`, `DATABASE_URL`, and
      `TMDB_API_KEY` before the application modules finish importing.
- [x] Choose a reproducible schema workflow: tracked Supabase SQL migrations
      created with the Supabase CLI. Remote migration-history synchronization
      remains a follow-up after the provider connection is repaired.
- [x] Define the `entries` schema with constraints for allowed status, rating
      range, non-empty title, and valid entry type. The production table and
      rating/type/status constraints were verified on 2026-07-26; non-empty
      title and nullability hardening for an existing table remain separate
      follow-up work.
- [x] Remove the obsolete `init_db()` bootstrap in favor of the tracked
      migrations. This prevents local or deployment code from creating a weaker
      competing `entries` schema; fresh environments must apply the migration
      files before serving database-backed routes.
- [x] Add indexes and a connection strategy appropriate for the deployment
      environment; document whether direct Postgres connections or a Supabase
      API/pooler are used.
      - [x] Reviewed the current query shape: `get_all()` orders by the primary
            key and templates perform the type split in memory, so no redundant
            secondary index is justified yet.
      - [x] Added a five-second `psycopg2` connect timeout and documented the
            intended Supabase Shared Pooler transaction-mode URL for Vercel.
      - [x] Resolve the provider-side pooler tenant mapping before declaring
            the deployed connection strategy complete; the current production
            pooler configuration is verified by the live smoke check.
- [x] Define failure behavior and transaction cleanup for database errors.
      All database operations now run through a shared context manager that
      commits on success, rolls back and re-raises on failure, and closes the
      cursor and connection in all cases.

### Request validation and application behavior

- [x] Validate title length and non-empty input server-side. The add form now
      rejects blank titles and titles over 200 characters before TMDB/database
      work.
- [x] Validate `entry_type`, `status`, and rating against allowlists and bounds;
      malformed input now flashes a user-visible error instead of raising a
      conversion error or reaching the database.
- [x] Handle missing or invalid entry IDs consistently and return an appropriate
      response when an update/delete affects no row. Update/delete now use
      affected-row counts and flash `Entry not found.` when no row exists.
- [x] Add user-visible validation error states for these malformed request
      cases through the shared flash-message display on the index page.
- [x] Add user-visible error states for database and TMDB failures.
      - [x] TMDB timeout, network, authentication, rate-limit, and malformed
            response failures now flash safe messages during add.
      - [x] Database failures now produce a safe HTTP 503 public-read state or
            a retryable flash message for authorized mutations.
- [x] Preserve the selected entry type correctly when TMDB returns mixed movie
      and TV results by treating the admin's explicit form selection as
      authoritative; TMDB media type remains lookup metadata.
- [ ] Add safe escaping and length limits before introducing any free-text
      review or note fields.

### External TMDB integration

- [x] Add a finite request timeout and call `raise_for_status()` or equivalent
      response validation. TMDB requests use a five-second timeout and validate
      HTTP status plus JSON shape.
- [x] Handle TMDB quota, authentication, malformed JSON, and network failures
      separately enough to make operational diagnosis possible. Safe user
      messages and log categories distinguish these cases without credentials.
- [x] Add server-side rate limiting and caching for repeated title searches;
      protect TMDB quota rather than exposing the API key to browsers. The
      current five-minute cache and 30-uncached-requests-per-minute limiter are
      in-process protections; a shared store is still needed for global limits
      across scaled Vercel instances.
- [x] Store TMDB IDs and relevant metadata needed by the chosen differentiating
      feature, not only the display title and poster URL. The recommendation
      migration and add flow now persist TMDB ID, media type, and genre IDs;
      existing rows without metadata remain a documented cold-start limitation.
- [x] Document TMDB attribution, API-key boundaries, and data-refresh behavior.
      README and the rendered pages identify TMDB as the source, keep the key
      server-side, and document caching, discovery, and refresh limitations.

### Authentication and security baseline

- [x] Decide between Supabase Auth and a deliberately hardened single-admin
      authentication flow. Retain the custom single-admin flow for this
      single-owner application; its Flask session and direct database access
      are already the active boundary, while Supabase Auth would require a
      broader identity/session and database-policy migration.
- [ ] If using Supabase Auth, integrate identity/session verification with the
      Flask routes and make database policies use the same identity boundary.
- [x] If retaining custom auth, store a password hash rather than a plaintext
      environment password and add secure credential rotation guidance.
      `config.py` rejects values that are not Werkzeug-style hashes, and the
      README documents interactive generation and replacement during rotation.
- [x] Add CSRF protection to login, logout, add, edit, and delete forms.
      State-changing routes require a session-bound token, and successful login
      rotates the session and token. Focused runtime coverage remains part of
      the separate authentication-test task.
- [x] Set secure, HTTP-only, and appropriate SameSite session-cookie settings in
      production; rotate the Flask secret when required. `api/index.py` sets
      `HttpOnly` and `SameSite=Lax` everywhere and enables `Secure` for Vercel
      or `FLASK_ENV=production`; the README records secret rotation behavior.
- [x] Add login throttling or rate limiting and avoid revealing unnecessary
      authentication details in responses. Failed logins are limited to five
      attempts per client address per 60-second window on each warm instance;
      the response remains generic and includes `Retry-After` when limited.
- [x] Add authorization tests proving public reads, rejected anonymous writes,
      accepted authenticated writes, and CSRF rejection. The focused tests
      mock TMDB/database calls and keep production data untouched; execution is
      pending in an environment with Python dependencies installed.
- [x] Remove the unverified RLS claim from the README until policies are
      implemented and tested against the chosen direct-Postgres access path.
- [x] Check dependency versions and add a repeatable dependency/update process.
      Direct pins were reviewed against PyPI on 2026-07-27; the update and
      fresh-environment verification workflow is documented in
      `docs/dependency-update.md`.

### Automated verification

- [x] Add a test runner and test layout. `pytest.ini`, `tests/conftest.py`, and
      an app-import/route-registration smoke test now provide the foundation
      for focused behavior tests; the local pinned environment passes the full
      40-test suite.
- [x] Test application import and route registration without requiring a live
      database or TMDB key. `tests/test_app.py` exercises import, route
      registration, and `/healthz`; included in the passing 40-test suite.
- [x] Test login success/failure, session logout, and authorization guards.
      `tests/test_auth.py` covers the password-hash flow, CSRF-backed logout,
      session clearing, and anonymous edit/delete rejection; execution remains
      covered by the passing 40-test suite.
- [x] Test add/edit/delete with mocked database calls and valid/invalid input.
      `tests/test_mutations.py` covers validation short-circuiting, valid add and
      edit/delete requests, database-call isolation, and metadata keyword
      handling; covered by the passing 40-test suite.
- [x] Test TMDB success, no-result, timeout, non-2xx, and malformed-response
      behavior. `tests/test_tmdb.py` isolates cache/rate-limit state and mocks
      requests; covered by the passing 40-test suite.
- [x] Add a CI job for tests, linting/format checks, and dependency failure
      visibility. `.github/workflows/tests.yml` installs pinned dependencies,
      runs `pip check`, compiles sources, runs Ruff, and executes pytest across
      Python 3.10, 3.12, and 3.14; GitHub Actions run `30239984101` passed.

## P1 — Add one real differentiator

Choose one track. Do not implement both unless the first one is complete and
the project still has a clear product reason for the second.

### Track A: explainable content-based recommendations

- [x] Decide the recommendation contract: return up to 10 recommended unseen
      titles, a human-readable reason for every result, and a deterministic
      cold-start fallback of popular TMDB search results when the watchlist has
      no usable feature data. Recommendations never include titles already in
      the watchlist or marked `Watched`.
- [x] Extend the schema to retain TMDB IDs, media type, genre IDs, and the
      user's interaction/status data. Migration
      `20260727043725_add_recommendation_features.sql` adds nullable TMDB
      identity fields, a constrained media type, genre-ID arrays, and a partial
      unique identity index. Supabase project `vgirgwxehcsxloclanhf` applied
      migration version `20260727043725`, and read-only verification confirmed
      all three columns and the index.
- [x] Build a deterministic feature-extraction and normalization pipeline.
      `recommendations.py` normalizes positive genre IDs, accepts only TMDB
      movie/TV media types, and emits stable binary feature tokens; focused
      unit tests cover invalid values and deterministic output.
- [x] Implement cosine similarity or an equivalent transparent baseline.
      `recommendations.py` uses binary feature-token vectors and deterministic
      score/title/ID tie-breaking; focused tests cover empty and partial vectors.
- [x] Exclude titles already watched or already on the watchlist. Candidate
      filtering removes matching TMDB identity pairs and normalized titles,
      covering rows with and without stored TMDB metadata.
- [x] Add a deterministic explanation such as “recommended because it shares
      genres with…”. `explain_recommendation()` selects the strongest overlap,
      uses stable title tie-breaking, and returns a safe no-overlap fallback.
- [x] Expose recommendations through a tested Flask route and focused UI page
      with empty and error states. `/recommendations` uses the database,
      discovery provider, deterministic ranking, and escaped Jinja output;
      focused route tests cover empty, success, and provider-error states.
- [x] Add a cold-start strategy for a new or sparse watch history. When no
      usable feature profile exists, the service preserves the discovery
      provider's popularity order, filters seen titles, and explains the
      fallback as a popular pick.
- [ ] Evaluate the recommender with a small offline holdout, precision@k, or a
      similarly stated metric; document the limitations of the evaluation.
      `recommendations.py` now provides a precision@k holdout evaluator and
      `docs/recommendations.md` defines the protocol, but a real dated holdout
      is blocked until production entries accumulate feature metadata.
- [x] Add tests for feature extraction, ranking, filtering, explanations, and
      deterministic output. `tests/test_recommendations.py` covers normalization,
      feature extraction, similarity, stable ranking, seen-title filtering,
      cold-start output, precision@k validation, and explanation selection;
      runtime execution remains pending because the local Python interpreter is
      unavailable.
- [x] Document that this is a content-based baseline, not a claimed deep-learning
      system. `docs/recommendations.md` describes the binary-feature approach,
      chronological holdout protocol, and the absence of a real production
      precision claim.

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

- [x] Decide which privacy-conscious usage events are necessary; do not collect
      more personal data than the project needs. `docs/usage-measurement.md`
      selects three aggregate counters only: public views, successful adds, and
      recommendation views; no identifiers or external analytics are collected.
- [x] Add measurement for meaningful events such as public visits, successful
      additions, recommendation views, or availability-history views. The Flask
      routes increment the three selected daily counters; production summary
      evidence remains pending until the database-backed deployment is healthy.
- [x] Do not call a single-admin watchlist “N registered users”; implement
      multi-user accounts first if registered-user counts are desired. README
      and usage-measurement documentation explicitly define counters as
      aggregate activity, not registered-user counts.
- [ ] Recruit 5–10 real testers and record structured feedback about the core
      flow and differentiating feature.
- [ ] Fix the highest-value usability issues found by testers.
- [ ] Publish a dated usage summary in the README with exact numbers and a
      short explanation of how they were measured.
- [x] Add a privacy note and opt-out or consent behavior if analytics are
      externally hosted. No external analytics provider is used; README now
      documents the aggregate-only, identifier-free measurement boundary.
- [ ] Keep screenshots or a short demo recording that matches the verified
      deployed commit.

## P3 — Architecture, documentation, and operational evidence

- [x] Create `docs/architecture.md` with a diagram of the actual request,
      authentication, database, and TMDB flows.
- [x] Explain why the chosen database/auth approach fits this project and name
      one accepted tradeoff with its scaling consequence. The architecture
      document records the single-admin and direct-connection tradeoffs.
- [x] Document trust boundaries: browser, Flask server, database, auth system,
      and TMDB credentials. The architecture document records each boundary and
      the current no-RLS claim.
- [x] Document the chosen differentiating feature's data model, algorithm or
      scheduled pipeline, and failure modes. The architecture document covers
      recommendation metadata, binary features, fallback behavior, and errors.
- [x] Add a local setup guide that includes environment variables, schema setup,
      development start command, and test command. `docs/local-development.md`
      records the pinned-dependency, migration, Flask, and check commands.
- [x] Update README features only after each feature is verified in code. The
      recommendation feature is described as an implemented baseline with
      runtime and production usage verification still explicitly pending.
- [x] Remove the unsupported example RLS SQL until a tracked policy matches the
      actual Flask session and direct-Postgres access path.
- [x] Add a known-limitations section covering single-admin versus multi-user
      scope, recommendation/data-source limits, TMDB dependency, and deployment
      constraints. The README now links the dated verification record.
- [x] Add a small operations/runbook section for migrations, secret rotation,
      scheduled jobs, logs, and rollback. `docs/operations.md` records the
      current procedures and the fact that no scheduled jobs exist.
- [x] Link the backlog, architecture document, verification evidence, and live
      demo from the README. The README links the architecture, local setup,
      operations, and verification documents; the live URL is recorded there.

## P4 — Quality and release polish

- [ ] Check keyboard navigation, visible focus, form labels, modal behavior, and
      error announcements.
      - [x] Added explicit labels, focus-visible outlines, alert roles, modal
            dialog semantics, Escape-to-close, and focus return behavior.
      - [ ] Manual keyboard and screen-reader verification remains open because
            the in-app browser is unavailable in this environment.
- [ ] Verify responsive behavior at narrow mobile and desktop widths.
      - [x] Added narrow-screen header wrapping and attribution styling; visual
            responsive verification remains open.
- [x] Add useful empty/loading/error states for the core and differentiating
      feature flows. The core page has per-section empty states and safe database
      errors; recommendations has empty, provider/database error, and escaped
      result states. Loading is not a separate state because these are
      synchronous server-rendered requests.
- [x] Add structured logging that excludes passwords, API keys, and session
      contents. `observability.py` emits JSON events with an allowlisted field
      set, with focused redaction coverage; included in the passing 40-test
      suite.
- [x] Add database backup/export guidance appropriate to the chosen provider.
      `docs/operations.md` covers Supabase plan-aware backups, CLI logical
      exports, secret handling, disposable restore validation, and limitations.
- [ ] Run a release checklist: tests, dependency audit, secret scan, deployment
      smoke test, README accuracy, and accessibility review.
      - [x] Added `docs/release-checklist.md` with explicit commands, evidence,
            and current blockers; automated checks are now complete, while
            deployment and browser review remain open.
- [x] Create a logical feature-branch commit history and open a reviewable PR;
      do not merge directly to `main` without explicit approval. Draft PR #3
      contains the scoped commits from `project-backlog` and remains unmerged.

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
| 2026-07-26 | Schema bootstrap decision | `rg -n "init_db"` usage search; `database.py`; tracked files under `supabase/migrations/` | Passed: removed the unused weaker bootstrap; migrations are the only tracked schema-creation path |
| 2026-07-26 | Database connection strategy | Query review, `database.py`, README, and AGENTS guidance | At the time, no redundant index was warranted; connection attempts now time out after 5 seconds and Vercel is documented for Supabase transaction pooling. The provider mapping was later resolved through the production Connect-string update |
| 2026-07-26 | Database transaction cleanup | `database.py` transaction context and fake-connection success/failure verification | Passed: successful operations commit and close resources; raised operation errors roll back, re-raise, and close resources |
| 2026-07-26 | Request validation | Flask test-client checks with mocked TMDB/database functions; `api/index.py`, `database.py`, and index template | Passed: blank/overlong titles, invalid type/status, and malformed/out-of-range ratings are rejected with flash errors; unknown update/delete IDs report `Entry not found.` |
| 2026-07-26 | TMDB boundary handling | Mocked `requests.get` success, timeout, network, 401/403, 429, non-2xx, and malformed JSON cases; Flask add-route error check | Passed: requests use a five-second timeout, HTTP/JSON failures raise categorized safe errors, and the add flow flashes the user-safe message; caching/rate limiting remain open |
| 2026-07-26 | Database error states and media classification | Fake `psycopg2.Error` plus Flask test-client checks for public read/add/edit/delete; mocked mixed TMDB result | Passed: database driver failures become safe 503/flash states, and the selected Movie/TV type is preserved independently of TMDB `media_type` |
| 2026-07-26 | TMDB cache and rate limit | Mocked request counter with normalized repeated titles, uncached request window, and route-level rate-limit exception | Passed: repeated searches within five minutes reuse the in-process cache; uncached requests are limited to 30 per 60 seconds per warm instance; distributed enforcement remains a documented limitation |
| 2026-07-27 | Live health recheck | Read-only request to `https://movie-tracker-umber-sigma.vercel.app/healthz` and `/` | `/healthz` returned HTTP 200 with `{"status":"ok"}`; `/` returned HTTP 500, so the database-backed smoke test remains blocked |
| 2026-07-27 | Database connection failure handling | Vercel invocation `rhcxm-1785133247133-1e39b1cf1bad`; `database.py`; new `tests/test_database.py`; 41 local tests | Fixed connection errors occurring before transaction setup so they become the intended safe `DatabaseError` response; production remains blocked pending a fresh deployment and pooler configuration verification |
| 2026-07-27 | Authentication model decision | Current Flask routes/session, direct `psycopg2` database path, and Supabase connection/auth boundary review | Chose a hardened custom single-admin flow; password hashing, CSRF, cookie settings, throttling, and tests remain separate implementation tasks |
| 2026-07-27 | Password-hash authentication | `config.py`, `api/index.py`, `.env.example`, README rotation guidance, and `git diff --check` | Implemented hash-only configuration and `check_password_hash`; runtime login and authentication tests remain pending because the local Python environment is unavailable |
| 2026-07-27 | CSRF protection | `api/index.py`, login/index templates, and `git diff --check` | Implemented session-bound tokens for login, logout, add, edit, and delete; successful login rotates the session; runtime tests remain pending because the local Python environment is unavailable |
| 2026-07-27 | Session-cookie security | `api/index.py`, README cookie/rotation guidance, and `git diff --check` | Configured HTTP-only and `SameSite=Lax` cookies; `Secure` is enabled for Vercel or production mode; browser/runtime verification remains pending |
| 2026-07-27 | Login throttling | `api/index.py` and `git diff --check` | Added a five-attempt/60-second per-warm-instance limiter keyed by client address with generic failure messaging; distributed enforcement and runtime tests remain pending |
| 2026-07-27 | Test runner foundation | `requirements.txt`, `pytest.ini`, `tests/conftest.py`, `tests/test_app.py`, README test command, and `git diff --check` | Added pytest configuration and app-import/health-route smoke tests; execution is blocked because the local Python interpreter is unavailable |
| 2026-07-27 | Authorization tests | `tests/test_authorization.py` with mocked TMDB/database calls and `git diff --check` | Added public-read, anonymous-write, authenticated-write, and CSRF-rejection coverage; execution remains blocked because the local Python interpreter is unavailable |
| 2026-07-27 | RLS documentation correction | README, tracked migrations, Supabase security guidance, and `git diff --check` | Removed the unsupported RLS claim and stale `items`/`auth.role()` example; no RLS policy is claimed until it matches the Flask session boundary |
| 2026-07-27 | Authentication tests | `tests/test_auth.py` with hash, CSRF, session, and anonymous-guard coverage plus `git diff --check` | Added login success/failure, logout, and anonymous edit/delete tests; execution remains blocked because the local Python interpreter is unavailable |
| 2026-07-27 | Mutation tests | `tests/test_mutations.py` with mocked TMDB/database calls and `git diff --check` | Added valid/invalid add, edit, and delete coverage without production database access; execution remains blocked because the local Python interpreter is unavailable |
| 2026-07-27 | TMDB tests | `tests/test_tmdb.py` with mocked responses/exceptions and `git diff --check` | Added search and discovery success/filtering, unsupported-type, no-result, timeout, non-2xx, and malformed-JSON coverage; execution remains blocked because the local Python interpreter is unavailable |
| 2026-07-27 | Dependency process | PyPI release pages, pinned `requirements.txt`, `docs/dependency-update.md`, and `git diff --check` | Pinned Flask 3.1.3, Werkzeug 3.1.8, Requests 2.34.2, python-dotenv 1.2.2, psycopg2-binary 2.9.12, and pytest 9.1.1; fresh-install and test execution remain blocked by the unavailable local Python interpreter |
| 2026-07-27 | CI verification | `.github/workflows/tests.yml`, `ruff.toml`, pinned Ruff 0.15.22, local `venv`, and PR #3 checks | Passed: dependency consistency, compilation, Ruff linting, and 41 pytest tests locally; the Python 3.10/3.12/3.14 matrix also passed remotely |
| 2026-07-27 | App import coverage | `tests/test_app.py` and `git diff --check` | Added import, route-registration, and health endpoint coverage without live database/TMDB calls; execution remains blocked by the unavailable local Python interpreter |
| 2026-07-27 | Differentiator track decision | Existing watchlist/TMDB integration, backlog scope, and provider/data-source risk review | Selected Track A: deterministic content-based recommendations with explanations and offline evaluation; Track B is deferred |
| 2026-07-27 | Recommendation contract | Track A scope review | Defined a top-10 unseen-title response, required explanation text, and deterministic cold-start fallback; implementation and evaluation remain open |
| 2026-07-27 | Recommendation feature schema | Tracked migration `20260727043725_add_recommendation_features.sql`, `database.py`, `tmdb.py`, `api/index.py`, focused test updates, and Supabase project `vgirgwxehcsxloclanhf` | Added TMDB ID/media type/genre-ID persistence with a partial unique index; migration history and read-only column/index queries verified the remote schema, while application runtime tests remain pending |
| 2026-07-27 | Recommendation feature normalization | `recommendations.py`, `tests/test_recommendations.py`, and `git diff --check` | Added deterministic genre/media feature extraction with invalid-value filtering; runtime test execution remains pending because the local Python interpreter is unavailable |
| 2026-07-27 | Recommendation similarity baseline | `recommendations.py`, `tests/test_recommendations.py`, and `git diff --check` | Added binary-vector cosine similarity and stable candidate ranking with focused tests; runtime execution remains pending because the local Python interpreter is unavailable |
| 2026-07-27 | Recommendation seen-title filtering | `recommendations.py`, `tests/test_recommendations.py`, and `git diff --check` | Excluded candidates matching stored TMDB identity or normalized watchlist titles; runtime execution remains pending because the local Python interpreter is unavailable |
| 2026-07-27 | Recommendation explanations | `recommendations.py`, `tests/test_recommendations.py`, and `git diff --check` | Added deterministic shared-genre explanations and a no-overlap fallback; runtime execution remains pending because the local Python interpreter is unavailable |
| 2026-07-27 | Recommendation route and UI | `api/index.py`, `tmdb.py`, `recommendations.py`, `templates/recommendations.html`, `templates/index.html`, `tests/test_recommendations_route.py`, and `git diff --check` | Added `/recommendations`, TMDB discovery, escaped result rendering, empty/error states, and navigation; runtime execution remains pending because the local Python interpreter is unavailable |
| 2026-07-27 | Recommendation cold start | `recommendations.py`, `tests/test_recommendations.py`, and `git diff --check` | Added popular-provider-order fallback for empty/sparse feature profiles with seen-title filtering and explicit explanation text; runtime execution remains pending because the local Python interpreter is unavailable |
| 2026-07-27 | Recommendation evaluation harness | `recommendations.py`, `tests/test_recommendations.py`, `docs/recommendations.md`, and `git diff --check` | Added precision@k holdout computation and documented the real-data protocol; no metric is claimed because current production rows lack feature history |
| 2026-07-27 | Recommendation test coverage | `tests/test_recommendations.py` and `git diff --check` | Added focused coverage for feature normalization, ranking, filtering, cold-start behavior, precision@k validation, explanations, and deterministic output; runtime execution remains pending because the local Python interpreter is unavailable |
| 2026-07-27 | TMDB metadata and attribution | `tmdb.py`, `database.py`, `readme.md`, templates, and `git diff --check` | Documented server-side API-key handling, TMDB attribution, cache/discovery refresh behavior, and persisted recommendation metadata; direct runtime verification remains pending |
| 2026-07-27 | Architecture and local setup | `docs/architecture.md`, `docs/local-development.md`, and `git diff --check` | Documented actual request flow, trust boundaries, auth/database tradeoffs, recommendation failure modes, migration workflow, development server, and local checks |
| 2026-07-27 | Operational evidence and limitations | `docs/operations.md`, `docs/verification.md`, `readme.md`, and `git diff --check` | Added rollback/rotation/migration procedures, dated live limitations, cross-links, and an accurately qualified recommendation feature description |
| 2026-07-27 | Accessibility and responsive baseline | `templates/index.html`, `templates/login.html`, `static/style.css`, and `git diff --check` | Added form labels, alert roles, visible focus styles, modal semantics/focus return, and narrow-screen header wrapping; browser-based verification remains open because no browser is available |
| 2026-07-27 | Release polish baseline | `observability.py`, `tests/test_observability.py`, `docs/operations.md`, `docs/release-checklist.md`, and `git diff --check` | Added safe JSON event logging, state coverage notes, Supabase backup/export guidance, and a release checklist with current blockers; runtime execution remains pending |
| 2026-07-27 | Privacy-conscious usage counters | `docs/usage-measurement.md`, `database.py`, `api/index.py`, Supabase migrations `20260727051707` and `20260727051928`, read-only SQL/advisor checks, and `git diff --check` | Added daily aggregate counters for public views, successful adds, and recommendation views with no identifiers; API roles are revoked and a deny policy protects the table; production measurement remains pending |
| 2026-07-27 | CI failure repair | `tests/test_recommendations.py`, `tests/test_mutations.py`, local `pip check`, `compileall`, Ruff, pytest, and GitHub Actions run `30239984101` | Fixed the invalid hyphen in a test function name and updated a stale mock for metadata keyword arguments; local checks pass with 40 tests and the pushed Python 3.10/3.12/3.14 matrix is green |
| 2026-07-27 | Usage privacy documentation | `readme.md`, `docs/usage-measurement.md`, and `git diff --check` | Explicitly separated aggregate activity counters from registered-user counts and documented that no external analytics provider or user identifiers are collected |
| 2026-07-27 | Draft PR handoff | GitHub draft PR #3, `project-backlog`, and clean worktree | Opened `https://github.com/icecold009/movie-tracker/pull/3` against `main`; merge remains user-controlled |

## Decisions

Record decisions that affect scope here so future work does not reopen settled
questions without new evidence.

- Canonical deployment: Vercel; live verification remains open
- Authentication model: hardened custom single-admin flow; Supabase Auth is
  out of scope unless the project becomes multi-user
- Differentiator track: Track A, explainable content-based recommendations;
  it fits the existing watchlist and TMDB integration without introducing a
  second availability provider or unsupported historical-data claims
- Usage measurement approach: _undecided_

Track A is selected because it can be deterministic, explainable, and evaluated
with the existing personal watchlist. Track B remains out of scope unless a
legitimate availability source and historical snapshot terms are established.
