-- Migration: coordinator_claims RLS
-- GOV-PHASE1-TRACK-C2 / F7
-- DO NOT apply automatically — deploy via separate directive.

ALTER TABLE public.coordinator_claims ENABLE ROW LEVEL SECURITY;

-- service_role retains full access (bypasses RLS by design)
-- authenticated role: can SELECT all, INSERT/UPDATE only own callsign
CREATE POLICY claims_select_all ON public.coordinator_claims FOR SELECT TO authenticated USING (true);
CREATE POLICY claims_insert_own ON public.coordinator_claims FOR INSERT TO authenticated WITH CHECK (callsign = current_setting('request.jwt.claims', true)::jsonb->>'callsign');
CREATE POLICY claims_update_own ON public.coordinator_claims FOR UPDATE TO authenticated USING (callsign = current_setting('request.jwt.claims', true)::jsonb->>'callsign');

-- anon role: read-only (no write)
REVOKE INSERT, UPDATE, DELETE ON public.coordinator_claims FROM anon;
GRANT SELECT ON public.coordinator_claims TO anon;
