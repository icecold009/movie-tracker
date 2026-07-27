# Verification record

Last recorded live probe: 2026-07-27.

- Canonical live URL: https://movie-tracker-umber-sigma.vercel.app
- `/healthz`: HTTP 200 with `{"status":"ok"}`.
- `/`: HTTP 200.
- `/login`: HTTP 200.
- Anonymous `POST /add`: HTTP 302 to `/login`.
- Authorized production add/delete: user-confirmed reversible smoke check
  passed.
- Production `DATABASE_URL` uses the current Supabase transaction pooler and
  `ADMIN_PASSWORD_HASH` is configured without recording either secret.

Local verification on 2026-07-27 passed `pip check`, compilation, Ruff, and 41
pytest tests using the pinned environment. PR #3 checks passed across Python
3.10, 3.12, and 3.14, plus Vercel and GitGuardian. Browser accessibility review
and recommender-quality measurement remain open.
