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

Local focused tests and CI are tracked, but runtime execution has not been
claimed from this checkout because its available Python interpreter is
inaccessible. Supabase migration history and the recommendation columns/index
were verified separately with read-only checks; that does not establish a
healthy deployed application route.
