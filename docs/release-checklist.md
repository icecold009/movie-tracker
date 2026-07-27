# Release checklist

Run this checklist against the exact commit intended for deployment and record
the result in `BACKLOG.md` or `docs/verification.md`.

- [x] `git diff --check` is clean.
- [x] Focused pytest suite passes, followed by Ruff, `compileall`, and
      `pip check`.
- [x] Dependency pins and a tracked-file secret scan are reviewed. The scan
      found only documented placeholders and test fixtures; no external secret
      scanner is installed locally.
- [ ] Supabase migrations are applied and the deployed connection identity is
      verified from current Connect settings. Production database-backed routes
      are healthy, but the provider Connect identity was not re-read in this
      run.
- [x] Vercel `/healthz`, public `/`, `/login`, anonymous mutation rejection,
      and a reversible authorized write are smoke-tested.
- [ ] README, backlog, architecture, operations, and known limitations match
      the deployed commit.
- [ ] Keyboard, screen-reader, and narrow-screen behavior are reviewed in a
      browser.

Current status for branch tip `4ef1e5f`: `git diff --check`, 47 pytest tests,
Ruff, compilation, pip dependency validation, and JavaScript syntax checks pass.
Production `/healthz`, `/`, `/login`, and
`/recommendations` return 200; anonymous mutation rejection returns 302 to
`/login`; the authorized reversible add/delete fixture passed and was removed,
as recorded in `docs/verification.md`. Browser keyboard, screen-reader,
and responsive visual review remain open because no browser surface is
available, as does recommender-quality measurement.
