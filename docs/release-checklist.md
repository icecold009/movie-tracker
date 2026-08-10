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
- [ ] Vercel `/healthz`, public `/`, `/login`, anonymous mutation rejection,
      and a reversible authorized write are smoke-tested for the exact current
      branch. Historical evidence is recorded in `docs/verification.md`.
- [ ] README, backlog, architecture, operations, and known limitations match
      the deployed commit.
- [ ] Keyboard, screen-reader, and narrow-screen behavior are reviewed in a
      browser.

Current local verification for branch `codex/review-fixes` on **2026-08-10**:
`git diff --check`, 59 pytest tests, Ruff, compilation, pip dependency
validation, and JavaScript syntax checks pass. These are local checks for this
branch; the production routes, applied migrations, and browser keyboard,
screen-reader, and responsive behavior still require separate current
verification before release. Historical production evidence remains in
`docs/verification.md` and must not be treated as evidence for this branch.
