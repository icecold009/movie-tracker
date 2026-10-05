# Verification record

## Current status check — 2026-10-05

- Current `main` is `778e0031d6ffec99b69dd0422a4f176b702c73e5`.
- Latest production deployment `dpl_2KPyLrvSThXB7R6C75nR1yXXw1Ls` is
  `READY` from that `main` commit. A READY deployment is not route or
  database-health evidence.
- Supabase project `vgirgwxehcsxloclanhf` is `INACTIVE`. Read-only migration
  history and role-privilege queries timed out; current live schema, migration
  parity, grants, and database-backed routes are unverified.
- The grouped seven-day Vercel runtime-status query returned no rows. It was not
  an HTTP route probe and does not establish application health.
- The exact encrypted Vercel `DATABASE_URL` identity remains unverified. The
  connector returned variable metadata but no secret value; no credential was
  read.
- No database or production mutation was performed. All August 16 route,
  database, grant, and deployment observations below are historical.

## Historical audit — 2026-08-16

- Canonical live URL: https://movie-tracker-umber-sigma.vercel.app
- Canonical production deployment: `dpl_AD1kFbNeNY3A6WrkurMKRpJLVHge`
- Canonical production commit: `38d462dfd102000927a8b9f1d59aa7bc7810142c`
  from `main`.
- Audit branch: `codex/release-audit-2026-08-16`; local HEAD before the audit
  edits was `055aa8e8857f529f55a8e7f4a88929f2786168ac`. This branch is
  local-only and has not been deployed. The earlier preview deployment for
  the baseline branch is not the canonical production deployment.
- `/healthz`: HTTP 200 with `{"status":"ok"}`.
- `/`: HTTP 200 and rendered 10 database-backed entries.
- `/login`: HTTP 200; the live response cookie was `Secure; HttpOnly;
  SameSite=Lax`.
- `/recommendations`: HTTP 200 with 10 rendered recommendation cards.
- Anonymous `POST /add`: HTTP 302 to `/login` using a synthetic marker; no
  authorized mutation was attempted.
- Vercel runtime error aggregation reported no runtime errors in the selected
  seven-day window. A successful Vercel build/deployment is not treated as
  database or route-health proof; the route probes above are the relevant
  evidence.

### Current database evidence and open gates

- Supabase project `vgirgwxehcsxloclanhf` is `ACTIVE_HEALTHY`.
- A current project SQL check reported database user `postgres` on server port
  5432. This verifies the connected project query, not the exact encrypted
  Vercel `DATABASE_URL` pooler identity; that identity still needs a current
  Connect-settings/Vercel environment check.
- Remote migration history contains `20260726165817`, `20260727043725`,
  `20260727051707`, `20260727051928`, `20260816060348`, and
  `20260816090126`. The branch now tracks six migration files with those same
  versions; the initial/constraint history was normalized to the remote
  `20260726165817_add_entries_constraints` version.
- `public.entries` has 10 rows, all 10 marked watched, but only 1 row has
  complete `tmdb_id`, `tmdb_media_type`, and `genre_ids`. A real chronological
  production-derived precision@k holdout is therefore not meaningful yet.
- RLS is enabled on `entries` and `usage_daily`; the only `entries` policy is a
  public SELECT policy. There is no Flask-session-aligned row policy for
  mutations, so the application remains a single-admin/server-boundary design
  and does not claim RLS authorization.
- The Flask app uses direct PostgreSQL and no Supabase REST or GraphQL client.
  The production grant fix leaves `postgres` able to SELECT `public.entries`
  while `PUBLIC`, `anon`, and `authenticated` cannot; Supabase security
  advisors returned no security lints after the fix.
- The schema-alignment migration verified 10 entries with zero incomplete rows;
  the live columns now match the tracked non-null/default expectations.
- The live cookie flags are verified, and source plus local tests cover CSRF,
  session rotation, hash-only configuration, and five-attempt/60-second login
  throttling. A full live check of those behaviors still requires an admin
  session and controlled production credential access.
- Authorized production add/edit/delete, backup restore, historical credential
  rotation, and exact deployed pooler identity remain unverified in this audit.

### Local and browser evidence

- On the audit branch, 61 pytest tests, Ruff, Python compilation, `pip check`,
  JavaScript syntax checks, and `git diff --check` passed.
- Focused recommender/route/evaluation tests: 24 passed. TMDB boundary tests:
  11 passed, including timeout, malformed response, provider quota, and
  warm-instance rate-limit behavior.
- The live public home and login pages were inspected at desktop and 390px
  mobile widths. Public navigation was keyboard-checked; focus advanced to
  `Admin Login` and exposed the visible focus outline. Labels, landmarks,
  recommendation explanations, modal markup in the source, recommendation
  `aria-live`, and empty/skeleton/error states have automated coverage. A
  manual admin-session keyboard, screen-reader, modal Escape, and focus-return
  pass remains open.

## Historical evidence

The 2026-07-27 authorized add/delete smoke test and the earlier 47-test and
59-test local runs remain historical records. They are not evidence for the
current audit branch or the current production deployment unless re-run against
the exact commit and environment.

## UI evidence and release — Package 6

This record keeps local checks, browser evidence, accessibility evidence,
preview deployment, and production evidence separate. The browser runner
refuses a dirty worktree and records the branch and exact HEAD in its JSON
report. Set UI_EVIDENCE_DIR to save screenshots and the report outside Git.

- **Local Python checks:** pytest, Ruff, Python compilation, and pip check
  run in the repository environment. They do not establish hosted CI status.
- **Browser checks:** scripts/ui_browser_matrix.cjs launches
  scripts/ui_fixture_server.py on loopback. The fixture process replaces all
  database reads/writes and TMDB calls with synthetic data or in-memory
  behavior. The browser blocks every non-local request.
- **Accessibility checks:** the runner checks visible control names, one main
  landmark, image alt attributes, ARIA ID references, mobile target sizes,
  keyboard order/focus visibility, dialog isolation, Escape, and focus return.
  These are targeted DOM/keyboard checks; they are not axe results or a
  screen-reader pass.
- **Visual baselines:** the runner writes PNGs and verification-report.json
  to UI_EVIDENCE_DIR or a temporary external folder. Do not add these outputs
  to the repository.
- **Preview deployment:** record only a Vercel deployment proven to use this
  branch's exact commit and the preview target. A local browser run is not
  preview evidence.
- **Production:** record only a separately user-approved production release
  and runtime check. A preview or local test is not production evidence.

Package 6 final verification was captured on 2026-10-05 against source commit
`9b828537a9041a2c3fcdbe2106978fdbd21823f8` on
`codex/ui-release-evidence-20261004`.

- **Local checks:** 75 pytest tests passed; Ruff, compileall, pip check,
  `node --check static/app.js`, `node --check scripts/ui_browser_matrix.cjs`,
  and `git diff --check` passed.
- **Browser matrix:** 12 route/viewport captures across 390x844, 768x1024,
  1024x900, and 1440x1000; 12 named states; 28 DOM/accessibility records;
  five interaction checks; and 27 screenshots. All viewport audits passed:
  exactly one main landmark, zero horizontal overflow, and no unnamed controls,
  missing image alternatives, broken ARIA references, undersized targets, or
  overlays.
  There were zero external requests, console errors, or page errors. Three
  expected HTTP 503 responses represented synthetic provider/database errors.
- **Interaction coverage:** server-rendered no-JavaScript form; keyboard order
  and visible focus; dialog isolation, focus trap, Escape, and focus return;
  coarse-pointer hover behavior; and reduced-motion behavior all passed.
- **Evidence artifact:** `verification-report.json` and 27 screenshots were
  saved under the configured external UI evidence directory, outside Git. The
  report identifies source SHA `9b828537a9041a2c3fcdbe2106978fdbd21823f8`.
- **Jev:** plan and diff reviews are advisory. The plan review returned a
  generic revise advisory without naming a source defect or user decision;
  the diff review batches and their exact coverage are recorded in the final
  PR and task handoff.
- **Preview:** Vercel deployment
  `dpl_9k7NNpWXREX5aceoVV8dCQNoE6GA` is READY at
  [movie-tracker-4nttj6hmk-shaurya-s-projects11.vercel.app](https://movie-tracker-4nttj6hmk-shaurya-s-projects11.vercel.app).
  Vercel metadata confirms branch
  `codex/ui-release-evidence-20261004` and exact source SHA
  `9b828537a9041a2c3fcdbe2106978fdbd21823f8`; target is null, identifying
  this as a preview deployment.
- **Limits:** browser evidence uses only the local synthetic Flask fixture
  server, with provider/database access replaced and external requests blocked.
  The targeted DOM/keyboard checks are not axe results or a human screen-reader
  pass. This record does not represent production deployment or production data.
