-- ============================================================================
-- Migration 014: Conversion Intelligence System
-- Phase: 16
-- Purpose: Schema changes to support pattern detection and learning
-- ============================================================================

-- 1. Add ALS component snapshot to leads (for learning)
-- Stores the raw component scores before weighting
ALTER TABLE leads ADD COLUMN IF NOT EXISTS als_components JSONB;
-- Stores the weights that were applied when scoring
ALTER TABLE leads ADD COLUMN IF NOT EXISTS als_weights_used JSONB;
-- Timestamp when the lead was scored
ALTER TABLE leads ADD COLUMN IF NOT EXISTS scored_at TIMESTAMPTZ;

-- Example als_components:
-- {
--   "data_quality": 16,
--   "authority": 22,
--   "company_fit": 18,
--   "timing": 9,
--   "risk": 0
-- }

-- Example als_weights_used:
-- {
--   "data_quality": 0.20,
--   "authority": 0.25,
--   "company_fit": 0.25,
--   "timing": 0.15
-- }

-- 2. Add converting touch tracking to activities
-- Marks the activity that led to a booking
ALTER TABLE activities ADD COLUMN IF NOT EXISTS led_to_booking BOOLEAN DEFAULT FALSE;
-- Snapshot of content sent for pattern analysis
ALTER TABLE activities ADD COLUMN IF NOT EXISTS content_snapshot JSONB;

-- Example content_snapshot (stored when activity created):
-- {
--   "subject": "Quick question about {company}",
--   "body": "Hi {first_name}, I noticed...",
--   "word_count": 78,
--   "char_count": 412,
--   "pain_points_used": ["leads", "scaling"],
--   "cta_used": "open to a quick chat",
--   "has_company_mention": true,
--   "has_first_name": true,
--   "has_recent_news": false,
--   "has_mutual_connection": false,
--   "has_industry_specific": true,
--   "touch_number": 2,
--   "sequence_id": "uuid",
--   "sent_at": "2025-12-27T10:00:00Z",
--   "day_of_week": 4,
--   "hour_of_day": 10
-- }

-- 3. Add learned weights to clients
-- Stores optimized ALS weights derived from historical outcomes
ALTER TABLE clients ADD COLUMN IF NOT EXISTS als_learned_weights JSONB;
-- When the weights were last updated
ALTER TABLE clients ADD COLUMN IF NOT EXISTS als_weights_updated_at TIMESTAMPTZ;
-- Count of conversion outcomes used to derive weights
ALTER TABLE clients ADD COLUMN IF NOT EXISTS conversion_sample_count INTEGER DEFAULT 0;

-- 4. Create conversion_patterns table
-- Stores computed patterns for each detector type (who/what/when/how)
CREATE TABLE IF NOT EXISTS conversion_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    pattern_type TEXT NOT NULL CHECK (pattern_type IN ('who', 'what', 'when', 'how')),
    patterns JSONB NOT NULL,
    sample_size INTEGER NOT NULL,
    confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Each client can only have one active pattern per type
    CONSTRAINT unique_client_pattern_type UNIQUE (client_id, pattern_type)
);

-- Comments for documentation
COMMENT ON TABLE conversion_patterns IS 'Stores computed conversion patterns from detectors';
COMMENT ON COLUMN conversion_patterns.pattern_type IS 'Type of pattern: who (lead attrs), what (content), when (timing), how (channels)';
COMMENT ON COLUMN conversion_patterns.patterns IS 'Type-specific pattern data as JSONB';
COMMENT ON COLUMN conversion_patterns.confidence IS 'Confidence score 0.0-1.0 based on sample size';
COMMENT ON COLUMN conversion_patterns.valid_until IS 'Pattern expiry (typically +14 days from computed_at)';

-- 5. Indexes for conversion_patterns
CREATE INDEX IF NOT EXISTS idx_conversion_patterns_client ON conversion_patterns(client_id);
CREATE INDEX IF NOT EXISTS idx_conversion_patterns_type ON conversion_patterns(pattern_type);
CREATE INDEX IF NOT EXISTS idx_conversion_patterns_valid ON conversion_patterns(valid_until);

-- Index for efficient pattern lookups by client
CREATE INDEX IF NOT EXISTS idx_conversion_patterns_client_type ON conversion_patterns(client_id, pattern_type);

-- 6. Indexes on leads for pattern analysis
CREATE INDEX IF NOT EXISTS idx_leads_als_components ON leads USING GIN (als_components);
CREATE INDEX IF NOT EXISTS idx_leads_scored_at ON leads(scored_at) WHERE scored_at IS NOT NULL;

-- 7. Indexes on activities for pattern analysis
CREATE INDEX IF NOT EXISTS idx_activities_led_to_booking ON activities(led_to_booking) WHERE led_to_booking = TRUE;
CREATE INDEX IF NOT EXISTS idx_activities_content_snapshot ON activities USING GIN (content_snapshot);

-- 8. Create pattern history table (for tracking pattern evolution)
CREATE TABLE IF NOT EXISTS conversion_pattern_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    pattern_type TEXT NOT NULL,
    patterns JSONB NOT NULL,
    sample_size INTEGER NOT NULL,
    confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE conversion_pattern_history IS 'Historical record of pattern evolution over time';

CREATE INDEX IF NOT EXISTS idx_pattern_history_client ON conversion_pattern_history(client_id, pattern_type, computed_at DESC);

-- 9. RLS Policies for conversion_patterns
ALTER TABLE conversion_patterns ENABLE ROW LEVEL SECURITY;

-- Tenant isolation policy - users can only see patterns for their clients
CREATE POLICY tenant_isolation_patterns ON conversion_patterns
    FOR ALL USING (
        client_id IN (
            SELECT client_id FROM memberships
            WHERE user_id = auth.uid() AND accepted_at IS NOT NULL
        )
    );

-- 10. RLS Policies for conversion_pattern_history
ALTER TABLE conversion_pattern_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_pattern_history ON conversion_pattern_history
    FOR ALL USING (
        client_id IN (
            SELECT client_id FROM memberships
            WHERE user_id = auth.uid() AND accepted_at IS NOT NULL
        )
    );

-- 11. Function to mark converting touch
-- When a lead converts, mark the most recent outbound activity as led_to_booking
CREATE OR REPLACE FUNCTION mark_converting_touch()
RETURNS TRIGGER AS $$
BEGIN
    -- When a lead status changes to 'converted'
    IF NEW.status = 'converted' AND (OLD.status IS NULL OR OLD.status != 'converted') THEN
        -- Find the most recent outbound activity before conversion and mark it
        UPDATE activities
        SET led_to_booking = TRUE
        WHERE lead_id = NEW.id
        AND action IN ('email_sent', 'sms_sent', 'linkedin_sent', 'voice_completed')
        AND created_at = (
            SELECT MAX(created_at) FROM activities
            WHERE lead_id = NEW.id
            AND action IN ('email_sent', 'sms_sent', 'linkedin_sent', 'voice_completed')
            AND created_at < NOW()
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop existing trigger if it exists
DROP TRIGGER IF EXISTS trigger_mark_converting_touch ON leads;

-- Create trigger
CREATE TRIGGER trigger_mark_converting_touch
    AFTER UPDATE ON leads
    FOR EACH ROW
    EXECUTE FUNCTION mark_converting_touch();

COMMENT ON FUNCTION mark_converting_touch() IS 'Automatically marks the converting touch when a lead status changes to converted';

-- 12. Function to copy patterns to history before update
CREATE OR REPLACE FUNCTION archive_pattern_history()
RETURNS TRIGGER AS $$
BEGIN
    -- When updating a pattern, archive the old version
    IF TG_OP = 'UPDATE' THEN
        INSERT INTO conversion_pattern_history (
            client_id,
            pattern_type,
            patterns,
            sample_size,
            confidence,
            computed_at
        ) VALUES (
            OLD.client_id,
            OLD.pattern_type,
            OLD.patterns,
            OLD.sample_size,
            OLD.confidence,
            OLD.computed_at
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop existing trigger if it exists
DROP TRIGGER IF EXISTS trigger_archive_pattern_history ON conversion_patterns;

-- Create trigger
CREATE TRIGGER trigger_archive_pattern_history
    BEFORE UPDATE ON conversion_patterns
    FOR EACH ROW
    EXECUTE FUNCTION archive_pattern_history();

COMMENT ON FUNCTION archive_pattern_history() IS 'Archives old patterns to history table before updating';

-- ============================================================================
-- VERIFICATION CHECKLIST
-- ============================================================================
-- [x] als_components column on leads
-- [x] als_weights_used column on leads
-- [x] scored_at column on leads
-- [x] led_to_booking column on activities
-- [x] content_snapshot column on activities
-- [x] als_learned_weights column on clients
-- [x] als_weights_updated_at column on clients
-- [x] conversion_sample_count column on clients
-- [x] conversion_patterns table with UNIQUE constraint
-- [x] conversion_pattern_history table
-- [x] Indexes for efficient queries
-- [x] RLS policies for tenant isolation
-- [x] mark_converting_touch trigger function
-- [x] archive_pattern_history trigger function
