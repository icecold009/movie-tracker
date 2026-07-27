# Verification record

Last recorded live probe: 2026-07-27.

- Canonical live URL: https://movie-tracker-umber-sigma.vercel.app
- `/healthz`: HTTP 200 with `{"status":"ok"}`.
- `/`: HTTP 200.
- `/login`: HTTP 200.
- `/recommendations`: HTTP 200.
- Anonymous `POST /add`: HTTP 302 to `/login`.
- Authorized production add/delete: user-confirmed reversible smoke check
  passed.
- Production `DATABASE_URL` uses the current Supabase transaction pooler and
  `ADMIN_PASSWORD_HASH` is configured without recording either secret.

Local verification on 2026-07-27 passed the focused accessibility tests and
the full 46-test pytest suite using the pinned environment. The follow-up UI
change adds explicit dialog state, keyboard focus trapping, focus return, and
polite live announcements for rating changes. Browser accessibility,
responsive visual review, and recommender-quality measurement remain open
because no browser surface is available and the watchlist is still too small
for a real holdout metric.
