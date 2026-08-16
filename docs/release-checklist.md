# Release checklist

Run this checklist against the exact commit intended for deployment and record
the result in `BACKLOG.md` or `docs/verification.md`.

- [x] `git diff --check` is clean.
- [x] The current audit branch passes 61 pytest tests, followed by Ruff,
      `compileall`, `pip check`, JavaScript syntax checks, and `git diff --check`.
- [x] Dependency pins and a tracked-file secret scan are reviewed. The scan
      found only documented placeholders and test fixtures; no external secret
      scanner is installed locally.
- [ ] Supabase migrations are applied with parity to the tracked files and the
      encrypted deployed connection identity is verified from current Connect
      settings. The project is healthy, and the new
      `20260816060348_lock_down_entries_api_grants` migration is applied; remote
      history has five rows while this branch tracks six files because the
      initial/constraint timestamp mismatch remains unresolved.
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
- [ ] Manual keyboard, screen-reader, modal, Escape/focus-return, and full
      responsive browser review remain open; public desktop/mobile screenshots
      and label/live-region checks were captured.

Current local verification for branch `codex/release-audit-2026-08-16` on
**2026-08-16**: 61 pytest tests, Ruff, compilation, pip dependency validation,
JavaScript syntax checks, and `git diff --check` pass. These are local checks
for the audit branch. The exact production deployment is `main` commit
`38d462dfd102000927a8b9f1d59aa7bc7810142c`, while this branch is only a preview
at `055aa8e8857f529f55a8e7f4a88929f2786168ac`; production evidence must not be
treated as evidence that this branch has been deployed.
