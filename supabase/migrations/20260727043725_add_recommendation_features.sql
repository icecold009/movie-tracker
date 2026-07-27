ALTER TABLE public.entries
    ADD COLUMN IF NOT EXISTS tmdb_id BIGINT,
    ADD COLUMN IF NOT EXISTS tmdb_media_type TEXT,
    ADD COLUMN IF NOT EXISTS genre_ids INTEGER[] NOT NULL DEFAULT '{}';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'entries_tmdb_media_type_check'
    ) THEN
        ALTER TABLE public.entries
            ADD CONSTRAINT entries_tmdb_media_type_check
            CHECK (tmdb_media_type IS NULL OR tmdb_media_type IN ('movie', 'tv'));
    END IF;
END
$$;

CREATE UNIQUE INDEX IF NOT EXISTS entries_tmdb_identity_idx
    ON public.entries (tmdb_id, tmdb_media_type)
    WHERE tmdb_id IS NOT NULL AND tmdb_media_type IS NOT NULL;
