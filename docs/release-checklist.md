# Release checklist

Run this checklist against the exact commit intended for deployment and record
the result in `BACKLOG.md` or `docs/verification.md`.

- [x] `git diff --check` is clean.
- [x] The current audit branch passes 61 pytest tests, followed by Ruff,
      `compileall`, `pip check`, JavaScript syntax checks, and `git diff --check`.
- [x] Dependency pins and a tracked-file secret scan are reviewed. The scan
      found only documented placeholders and test fixtures; no external secret
      scanner is installed locally.
- [x] Supabase migration versions now match the six tracked files and the six
      remote history rows. The reviewed `20260816060348_lock_down_entries_api_grants`
      and `20260816090126_align_entries_schema` migrations are applied; live
      schema verification found 10 entries and zero incomplete rows.
- [ ] The encrypted deployed connection identity is still not verified from
      current Connect settings because no Vercel environment-variable connector
      is exposed in this session.
- [x] Supabase security advisors are clean after revoking `SELECT` on
      `public.entries` from `PUBLIC`, `anon`, and `authenticated`. The Flask
      application uses its trusted direct PostgreSQL connection and does not
      depend on Supabase REST or GraphQL access.
- [x] The canonical Vercel deployment currently returns 200 for `/healthz`,
      `/`, `/login`, and `/recommendations`; anonymous `POST /add` returns 302
      to `/login`.
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

Current local verification for branch `codex/release-audit-2026-08-16` on
**2026-08-16**: 61 pytest tests, Ruff, compilation, pip dependency validation,
JavaScript syntax checks, and `git diff --check` pass. These are local checks
for the audit branch. The exact production deployment is `main` commit
`38d462dfd102000927a8b9f1d59aa7bc7810142c`. This audit branch is local-only;
`055aa8e8857f529f55a8e7f4a88929f2786168ac` is its pre-audit baseline, not a
deployment of the current branch. Production evidence must not be treated as
evidence that this branch has been deployed.
