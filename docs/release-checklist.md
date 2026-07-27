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

Current status for this checkout: the focused accessibility tests and full 46-test
pytest suite pass locally. Production `/healthz`, `/`, `/login`, and
`/recommendations` return 200; anonymous mutation rejection returns 302 to
`/login`; the authorized reversible add/delete check remains the user-confirmed
evidence recorded in `docs/verification.md`. Browser keyboard, screen-reader,
and responsive visual review remain open because no browser surface is
available, as does recommender-quality measurement.
