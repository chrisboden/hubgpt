-- Enable RLS
ALTER TABLE advisors ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY "Enable read access for all users" ON advisors
    FOR SELECT
    TO authenticated, anon
    USING (true);

CREATE POLICY "Enable insert for authenticated users only" ON advisors
    FOR INSERT
    TO authenticated
    WITH CHECK (true);

CREATE POLICY "Enable update for authenticated users only" ON advisors
    FOR UPDATE
    TO authenticated
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Enable delete for authenticated users only" ON advisors
    FOR DELETE
    TO authenticated
    USING (true);

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT SELECT ON public.advisors TO anon, authenticated;
GRANT ALL ON public.advisors TO authenticated; 