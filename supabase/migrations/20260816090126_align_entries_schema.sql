ALTER TABLE public.entries
    ALTER COLUMN entry_type SET DEFAULT 'Movie',
    ALTER COLUMN entry_type SET NOT NULL,
    ALTER COLUMN status SET DEFAULT 'Watched',
    ALTER COLUMN status SET NOT NULL,
    ALTER COLUMN rating SET DEFAULT 7,
    ALTER COLUMN rating SET NOT NULL,
    ALTER COLUMN poster_url SET DEFAULT '',
    ALTER COLUMN poster_url SET NOT NULL,
    ALTER COLUMN added_on SET NOT NULL;
