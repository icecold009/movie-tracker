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
Ruff, and 40 pytest tests pass locally; GitHub Actions run `30239984101` also
passes. Browser review, secret-scan evidence, and the full deployment smoke
test remain open because the Vercel database route is blocked by Supavisor
tenant mapping.
