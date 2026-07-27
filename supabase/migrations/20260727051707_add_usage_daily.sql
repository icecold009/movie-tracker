CREATE TABLE IF NOT EXISTS public.usage_daily (
    event_date DATE NOT NULL DEFAULT CURRENT_DATE,
    event_name TEXT NOT NULL,
    event_count INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT usage_daily_pkey PRIMARY KEY (event_date, event_name),
    CONSTRAINT usage_daily_event_name_check CHECK (
        event_name IN ('public_view', 'successful_add', 'recommendation_view')
    ),
    CONSTRAINT usage_daily_event_count_check CHECK (event_count >= 0)
);

ALTER TABLE public.usage_daily ENABLE ROW LEVEL SECURITY;
