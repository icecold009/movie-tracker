REVOKE ALL ON TABLE public.usage_daily FROM anon, authenticated;

CREATE POLICY usage_daily_no_api_access
    ON public.usage_daily
    FOR ALL
    TO anon, authenticated
    USING (false)
    WITH CHECK (false);
