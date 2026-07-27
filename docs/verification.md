# Verification record

Last recorded live probe: 2026-07-27.

- Canonical live URL: https://movie-tracker-umber-sigma.vercel.app
- `/healthz`: HTTP 200 with `{"status":"ok"}`.
- `/`: HTTP 500; database-backed production health is unresolved.
- `/login`: previously returned HTTP 200; invalid-login handling was checked.
- Anonymous `POST /add`: previously redirected HTTP 302 to `/login`.
- Authorized production write: not attempted because no reversible fixture and
  the public database-backed view is failing.
- Current blocker: the Vercel database route uses a Supavisor tenant identity
  that the provider rejects; the current Connect-string identity must be
  refreshed before a complete smoke test.

Local verification on 2026-07-27 passed `pip check`, compilation, Ruff, and 40
pytest tests using the pinned environment. GitHub Actions run
`30239984101` passed its Python 3.10, 3.12, and 3.14 matrix. Supabase migration
history and the recommendation/usage schema were verified separately with
read-only checks; this still does not establish a healthy deployed application
route.
