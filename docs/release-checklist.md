# Release checklist

Run this checklist against the exact commit intended for deployment and record
the result in `BACKLOG.md` or `docs/verification.md`.

## Current status — 2026-10-05

This release is not currently verified. Supabase project
`vgirgwxehcsxloclanhf` is `INACTIVE`; migration-history and role-privilege
queries timed out. Current database-backed routes, live grants, and schema
parity are unverified. The latest Vercel production deployment is `READY` on
`main` at `778e0031d6ffec99b69dd0422a4f176b702c73e5`, which does not prove
route or database health. The checked items and run results below are from the
2026-08-16 audit and must not be treated as current evidence until rerun.

- [x] `git diff --check` is clean.
- [x] The 2026-08-16 audit branch recorded 61 pytest tests passing, plus
      Ruff, `compileall`, `pip check`, JavaScript syntax checks, and
      `git diff --check`.
- [x] Dependency pins and a tracked-file secret scan are reviewed. The scan
      found only documented placeholders and test fixtures; no external secret
      scanner is installed locally.
- [x] The 2026-08-16 audit recorded six matching migration versions. The
      reviewed `20260816060348_lock_down_entries_api_grants` and
      `20260816090126_align_entries_schema` migrations were reported applied;
      live schema verification then found 10 entries and zero incomplete rows.
      Current remote migration history and schema could not be rechecked because
      Supabase is inactive.
- [ ] The encrypted deployed connection identity is not verified. The
      connector returned metadata but no decrypted secret value.
- [x] The 2026-08-16 audit reported clean Supabase security advisors after
      revoking `SELECT` on `public.entries` from `PUBLIC`, `anon`, and
      `authenticated`. Current live grants and advisor results are unverified
      while the project is inactive.
- [x] The 2026-08-16 route probe recorded HTTP 200 for `/healthz`, `/`,
      `/login`, and `/recommendations`; anonymous `POST /add` returned 302
      to `/login`. Those historical responses do not establish current route
      health.
- [ ] A reversible authorized add/edit/delete smoke test is still pending
      because no production admin credential was supplied to this audit.
- [ ] Live CSRF rejection, session rotation, password-hash acceptance, and
      login-throttling behavior are not fully verified without an admin session;
      source/tests pass and the live cookie flags were observed.
- [x] README, backlog, architecture, operations, and known limitations now
      distinguish the current deployment from historical evidence.
- [ ] Admin-session keyboard, screen-reader, modal, Escape/focus-return, and
      full authenticated responsive browser review remain open. Public
      production desktop and 390x844 mobile screenshots, labels, landmarks,
      visible keyboard focus, and recommendation explanations were checked
      against deployment commit `38d462dfd102000927a8b9f1d59aa7bc7810142c`.

Historical local verification recorded for branch `codex/release-audit-2026-08-16` on
**2026-08-16**: 61 pytest tests, Ruff, compilation, pip dependency validation,
JavaScript syntax checks, and `git diff --check` passed. These are local checks
for the audit branch. The exact production deployment is `main` commit
`38d462dfd102000927a8b9f1d59aa7bc7810142c`. This audit branch is local-only;
`055aa8e8857f529f55a8e7f4a88929f2786168ac` is its pre-audit baseline, not a
deployment of the current branch. Production evidence must not be treated as
evidence that this branch has been deployed.
