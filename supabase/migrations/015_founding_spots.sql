-- Migration: 015_founding_spots.sql
-- Purpose: Create founding spots counter for tracking limited founding member slots
-- Date: 2026-01-04

-- Create founding spots counter table
CREATE TABLE IF NOT EXISTS public.founding_spots (
  id INT PRIMARY KEY DEFAULT 1,
  spots_taken INT DEFAULT 0 NOT NULL,
  total_spots INT DEFAULT 20 NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  CONSTRAINT check_spots_valid CHECK (spots_taken >= 0 AND spots_taken <= total_spots)
);

-- Add comment
COMMENT ON TABLE public.founding_spots IS 'Tracks founding member spots (limited to 20 total)';

-- Insert initial row
INSERT INTO public.founding_spots (id, spots_taken, total_spots)
VALUES (1, 0, 20)
ON CONFLICT (id) DO NOTHING;

-- Create function to increment spots (called by Stripe webhook)
CREATE OR REPLACE FUNCTION increment_founding_spots()
RETURNS void AS $$
BEGIN
  UPDATE public.founding_spots
  SET spots_taken = spots_taken + 1,
      updated_at = NOW()
  WHERE id = 1 AND spots_taken < total_spots;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'No founding spots available or already at maximum';
  END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create function to get remaining spots
CREATE OR REPLACE FUNCTION get_remaining_founding_spots()
RETURNS INT AS $$
DECLARE
  remaining INT;
BEGIN
  SELECT total_spots - spots_taken INTO remaining
  FROM public.founding_spots
  WHERE id = 1;
  RETURN COALESCE(remaining, 0);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create function to check if founding spots are available
CREATE OR REPLACE FUNCTION founding_spots_available()
RETURNS BOOLEAN AS $$
DECLARE
  remaining INT;
BEGIN
  SELECT total_spots - spots_taken INTO remaining
  FROM public.founding_spots
  WHERE id = 1;
  RETURN COALESCE(remaining, 0) > 0;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Enable RLS
ALTER TABLE public.founding_spots ENABLE ROW LEVEL SECURITY;

-- Allow public read access (anyone can see remaining spots)
CREATE POLICY "Allow public read access" ON public.founding_spots
  FOR SELECT USING (true);

-- Only service role can update (via Edge Functions)
CREATE POLICY "Only service role can update" ON public.founding_spots
  FOR UPDATE USING (auth.role() = 'service_role');

-- Only service role can insert
CREATE POLICY "Only service role can insert" ON public.founding_spots
  FOR INSERT WITH CHECK (auth.role() = 'service_role');

-- Enable realtime for live updates on landing page
ALTER PUBLICATION supabase_realtime ADD TABLE public.founding_spots;
