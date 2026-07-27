# Release checklist

Run this checklist against the exact commit intended for deployment and record
the result in `BACKLOG.md` or `docs/verification.md`.

- [ ] `git diff --check` is clean.
- [ ] Focused pytest suite passes, followed by Ruff, `compileall`, and
      `pip check`.
- [ ] Dependency pins and a secret scan are reviewed.
- [ ] Supabase migrations are applied and the deployed connection identity is
      verified from current Connect settings.
- [ ] Vercel `/healthz`, public `/`, `/login`, anonymous mutation rejection,
      and a reversible authorized write are smoke-tested.
- [ ] README, backlog, architecture, operations, and known limitations match
      the deployed commit.
- [ ] Keyboard, screen-reader, and narrow-screen behavior are reviewed in a
      browser.

Current status for this checkout: `git diff --check`, `pip check`, compilation,
Ruff, and 41 pytest tests pass locally. PR #3 passed its Python 3.10/3.12/3.14,
Vercel, and GitGuardian checks. Production `/healthz`, `/`, `/login`, anonymous
mutation rejection, and a user-confirmed reversible authorized add/delete
smoke check all pass. Browser accessibility review and recommender-quality
measurement remain open.
