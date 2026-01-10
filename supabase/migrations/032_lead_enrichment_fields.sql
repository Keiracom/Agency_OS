-- FILE: supabase/migrations/032_lead_enrichment_fields.sql
-- PURPOSE: Add LinkedIn enrichment and Claude analysis fields to lead_assignments
-- PHASE: 24A+ (Enhanced Lead Enrichment)
-- TASK: ENRICH-001
-- DEPENDENCIES: 024_lead_pool.sql
-- RULES APPLIED:
--   - Rule 1: Follow blueprint exactly
--   - Rule 14: Soft deletes only

-- ============================================
-- ADD ENRICHMENT FIELDS TO lead_assignments
-- ============================================

-- LinkedIn Person Enrichment
ALTER TABLE lead_assignments
ADD COLUMN IF NOT EXISTS linkedin_person_scraped_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS linkedin_person_data JSONB;

-- LinkedIn Company Enrichment
ALTER TABLE lead_assignments
ADD COLUMN IF NOT EXISTS linkedin_company_scraped_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS linkedin_company_data JSONB;

-- Claude Analysis Output
ALTER TABLE lead_assignments
ADD COLUMN IF NOT EXISTS personalization_analyzed_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS personalization_data JSONB,
ADD COLUMN IF NOT EXISTS pain_points TEXT[],
ADD COLUMN IF NOT EXISTS icebreaker_hooks JSONB,
ADD COLUMN IF NOT EXISTS best_channel channel_type,
ADD COLUMN IF NOT EXISTS personalization_confidence FLOAT;

-- ALS Score fields (if not already present)
ALTER TABLE lead_assignments
ADD COLUMN IF NOT EXISTS als_score INTEGER,
ADD COLUMN IF NOT EXISTS als_tier TEXT,
ADD COLUMN IF NOT EXISTS als_components JSONB,
ADD COLUMN IF NOT EXISTS scored_at TIMESTAMPTZ;

-- Enrichment status tracking
ALTER TABLE lead_assignments
ADD COLUMN IF NOT EXISTS enrichment_status TEXT DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS enrichment_started_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS enrichment_completed_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS enrichment_error TEXT;

-- ============================================
-- COMMENTS
-- ============================================

COMMENT ON COLUMN lead_assignments.linkedin_person_data IS
'Full LinkedIn person profile including headline, about, experience, and last 5 posts';

COMMENT ON COLUMN lead_assignments.linkedin_company_data IS
'Full LinkedIn company profile including description, specialties, and last 5 posts';

COMMENT ON COLUMN lead_assignments.personalization_data IS
'Claude analysis output: pain points, angles, hooks, topics to avoid';

COMMENT ON COLUMN lead_assignments.pain_points IS
'Extracted pain points for easy querying and display';

COMMENT ON COLUMN lead_assignments.icebreaker_hooks IS
'Per-channel icebreaker hooks: {email, linkedin, sms, voice, direct_mail}';

COMMENT ON COLUMN lead_assignments.best_channel IS
'Claude recommended best channel for outreach';

COMMENT ON COLUMN lead_assignments.enrichment_status IS
'Enrichment pipeline status: pending, in_progress, completed, failed';

-- ============================================
-- INDEXES
-- ============================================

-- Find leads needing enrichment
CREATE INDEX IF NOT EXISTS idx_assignments_enrichment_status
ON lead_assignments(enrichment_status)
WHERE enrichment_status IN ('pending', 'in_progress');

-- Find leads with completed personalization
CREATE INDEX IF NOT EXISTS idx_assignments_personalized
ON lead_assignments(personalization_analyzed_at)
WHERE personalization_analyzed_at IS NOT NULL;

-- Query by ALS tier
CREATE INDEX IF NOT EXISTS idx_assignments_als_tier
ON lead_assignments(als_tier)
WHERE als_tier IS NOT NULL;

-- Query by best channel
CREATE INDEX IF NOT EXISTS idx_assignments_best_channel
ON lead_assignments(best_channel)
WHERE best_channel IS NOT NULL;

-- ============================================
-- VERIFICATION
-- ============================================
-- [x] LinkedIn person fields added
-- [x] LinkedIn company fields added
-- [x] Claude analysis fields added
-- [x] ALS score fields added
-- [x] Enrichment status tracking added
-- [x] Indexes for common queries
-- [x] Comments for documentation
