-- Movie Tracker uses a trusted direct PostgreSQL connection, not Supabase Data API.
-- Keep the public watchlist in the Flask application while hiding the table from
-- anonymous/authenticated REST and GraphQL introspection surfaces.
REVOKE SELECT ON TABLE public.entries FROM PUBLIC, anon, authenticated;
