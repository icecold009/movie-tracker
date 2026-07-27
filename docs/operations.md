# Operations runbook

## Migrations

1. Review the SQL file under `supabase/migrations/` and confirm it is scoped to
   the intended schema change.
2. Use the linked Supabase project and run `supabase db push` from a reviewed
   feature branch.
3. Check migration history and the affected columns or indexes with read-only
   SQL before deploying application code that depends on them.
4. Record the migration version, verification date, and any provider limitation
   in `BACKLOG.md`.

The application must not create or silently alter the schema during startup.

## Secrets and credential rotation

- Keep local values in the ignored `.env` file and production values in Vercel's
  encrypted environment store.
- Generate a new `ADMIN_PASSWORD_HASH`, update the environment, and redeploy.
- Rotate `SECRET_KEY` when compromise is suspected; this invalidates existing
  signed sessions and requires a new login.
- Never place password values, API keys, database URLs, or session contents in
  logs, commits, screenshots, or issue descriptions.

## Logs and failure diagnosis

The Flask app emits JSON events with an allowlisted event name and safe
diagnostic fields for TMDB, database, and authentication failures; it does not
log credentials or session data. Start with the deployment log and the
corresponding safe user-facing error. `/healthz` only proves application
liveness; it does not prove database or TMDB availability. For a database
failure, verify the current Supabase Connect connection identity and pooler
tenant before changing application code.

## Rollback and deployment checks

1. Keep the previous known deployment and migration versions identifiable.
2. Run `git diff --check`, focused tests, Ruff, and dependency checks before
   publishing a branch.
3. Deploy the reviewed commit to the canonical Vercel target.
4. Probe `/healthz`, public `/`, `/login`, an anonymous rejected mutation, and a
   reversible authorized write only when a safe fixture is available.
5. If a release fails, use the previous Vercel deployment for application
   rollback and apply only reversible, reviewed database changes; never remove
   production rows as part of smoke testing.

There are no scheduled jobs in the current application. TMDB caching and rate
limiting are per warm serverless instance, so they are not a global scheduler
or quota service.

## Database backup and export

Use Supabase's Database > Backups controls according to the project's current
plan and retention settings. For an off-site logical export, use the current
Supabase CLI with a connection string from Connect settings:

```bash
supabase db dump --db-url <CONNECTION_STRING> -f data.sql --use-copy --data-only
```

Treat the connection string and resulting dump as secrets: store them outside
the repository, encrypt the backup at rest, and record its retention owner and
date. Restore into a disposable project or local environment first, validate
the migration history and row counts, and only then plan a production restore.
Do not use smoke tests as a backup or delete production rows to test recovery.
See the [Supabase backup documentation](https://supabase.com/docs/guides/platform/backups)
and [CLI backup/restore guide](https://supabase.com/docs/guides/platform/migrating-within-supabase/backup-restore)
for current plan, retention, and restore limitations.
