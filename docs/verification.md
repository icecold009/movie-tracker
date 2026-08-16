# Verification record

## Current audit — 2026-08-16

- Canonical live URL: https://movie-tracker-umber-sigma.vercel.app
- Canonical production deployment: `dpl_AD1kFbNeNY3A6WrkurMKRpJLVHge`
- Canonical production commit: `38d462dfd102000927a8b9f1d59aa7bc7810142c`
  from `main`.
- Audit branch: `codex/release-audit-2026-08-16`; local HEAD before the audit
  edits was `055aa8e8857f529f55a8e7f4a88929f2786168ac`. Its Vercel deployment
  is a preview, not the canonical production deployment.
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
  `20260727051707`, and `20260727051928`. The branch tracks five migration
  files, including `20260726165458` and `20260726165844`; migration parity is
  unresolved.
- `public.entries` has 10 rows, all 10 marked watched, but only 1 row has
  complete `tmdb_id`, `tmdb_media_type`, and `genre_ids`. A real chronological
  production-derived precision@k holdout is therefore not meaningful yet.
- RLS is enabled on `entries` and `usage_daily`; the only `entries` policy is a
  public SELECT policy. There is no Flask-session-aligned row policy for
  mutations, so the application remains a single-admin/server-boundary design
  and does not claim RLS authorization.
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
  mobile widths. Labels, visible focus styling, modal markup in the source,
  recommendation `aria-live`, and empty/skeleton/error states have automated
  coverage. A manual admin-session keyboard/screen-reader/modal pass was not
  completed; the browser keyboard driver did not reliably advance focus.

## Historical evidence

The 2026-07-27 authorized add/delete smoke test and the earlier 47-test and
59-test local runs remain historical records. They are not evidence for the
current audit branch or the current production deployment unless re-run against
the exact commit and environment.
