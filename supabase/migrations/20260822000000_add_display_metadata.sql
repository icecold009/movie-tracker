ALTER TABLE public.entries
    ADD COLUMN IF NOT EXISTS synopsis TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS release_date TEXT,
    ADD COLUMN IF NOT EXISTS metadata_source TEXT NOT NULL DEFAULT 'Manual',
    ADD COLUMN IF NOT EXISTS metadata_updated_at TIMESTAMPTZ;

ALTER TABLE public.entries
    DROP CONSTRAINT IF EXISTS entries_metadata_source_check;

ALTER TABLE public.entries
    ADD CONSTRAINT entries_metadata_source_check
    CHECK (metadata_source IN ('TMDB', 'Manual'));
