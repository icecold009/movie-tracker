# Local development

## Prerequisites

Use Python 3.10 or newer and a PostgreSQL-compatible database. The tracked
schema is maintained in `supabase/migrations/`; do not recreate it through an
application startup hook.

## Environment

Copy `.env.example` to the ignored `.env` file and provide:

- `SECRET_KEY`: a long random Flask session-signing key.
- `ADMIN_PASSWORD_HASH`: a Werkzeug password hash generated with the command
  in the README.
- `DATABASE_URL`: a TLS-enabled PostgreSQL connection string. Local direct
  connections may be used for development; Vercel should use the current
  Supabase Shared Pooler transaction-mode URL from Connect settings.
- `TMDB_API_KEY`: a server-only TMDB API key.

Install the pinned dependencies:

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Schema and development server

Install the Supabase CLI separately, authenticate to the intended project, and
apply tracked migrations with:

```bash
supabase link --project-ref <project-ref>
supabase db push
```

Start Flask locally with:

```bash
flask --app api.index run --debug
```

The application is also compatible with the Vercel entrypoint configured in
`vercel.json`; local Flask is the simpler development server.

## Checks

Run the automated checks from the repository root:

```bash
python -m pytest
python -m ruff check .
python -m compileall -q api config.py database.py recommendations.py tmdb.py
python -m pip check
```

These commands provide local evidence only. Production readiness additionally
requires current Vercel route smoke tests, provider connection verification,
and confirmation that the deployed commit has the tracked migrations applied.
