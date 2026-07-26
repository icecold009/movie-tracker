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
