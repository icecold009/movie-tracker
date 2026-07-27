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

Current status for this checkout: `git diff --check` passes, but runtime tests,
browser review, secret-scan evidence, and the full deployment smoke test remain
open because the local Python interpreter and browser are unavailable and the
Vercel database route remains blocked by Supavisor tenant mapping.
