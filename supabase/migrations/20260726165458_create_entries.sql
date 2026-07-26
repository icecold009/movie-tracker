CREATE TABLE IF NOT EXISTS public.entries (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    entry_type TEXT NOT NULL DEFAULT 'Movie',
    status TEXT NOT NULL DEFAULT 'Watched',
    rating INTEGER NOT NULL DEFAULT 7,
    poster_url TEXT NOT NULL DEFAULT '',
    added_on TEXT NOT NULL
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'entries_entry_type_check'
    ) THEN
        ALTER TABLE public.entries
            ADD CONSTRAINT entries_entry_type_check
            CHECK (entry_type IN ('Movie', 'TV Show'));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'entries_status_check'
    ) THEN
        ALTER TABLE public.entries
            ADD CONSTRAINT entries_status_check
            CHECK (status IN ('Watched', 'Want to Watch'));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'entries_rating_check'
    ) THEN
        ALTER TABLE public.entries
            ADD CONSTRAINT entries_rating_check
            CHECK (rating BETWEEN 1 AND 10);
    END IF;
END
$$;
