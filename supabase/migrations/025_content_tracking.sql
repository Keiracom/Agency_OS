-- Migration: 025_content_tracking.sql
-- Phase: 24B (Content & Template Tracking)
-- Purpose: Add template tracking and A/B testing support for CIS WHAT Detector
-- Date: 2026-01-06

-- ============================================================================
-- 1. ADD TEMPLATE TRACKING TO ACTIVITIES
-- ============================================================================

-- Template reference for tracking which template was used
ALTER TABLE activities ADD COLUMN IF NOT EXISTS template_id UUID REFERENCES email_templates(id);

-- A/B testing variant tracking
ALTER TABLE activities ADD COLUMN IF NOT EXISTS ab_variant TEXT;  -- 'A', 'B', 'control'
ALTER TABLE activities ADD COLUMN IF NOT EXISTS ab_test_id UUID;

-- Full message content (not just preview)
ALTER TABLE activities ADD COLUMN IF NOT EXISTS full_message_body TEXT;

-- Track links included in message
ALTER TABLE activities ADD COLUMN IF NOT EXISTS links_included TEXT[];

-- Track which personalization fields were available for this message
ALTER TABLE activities ADD COLUMN IF NOT EXISTS personalization_fields_used TEXT[];

-- Track AI generation metadata
ALTER TABLE activities ADD COLUMN IF NOT EXISTS ai_model_used TEXT;  -- 'gpt-4', 'claude-3', etc.
ALTER TABLE activities ADD COLUMN IF NOT EXISTS prompt_version TEXT;  -- For iterating on prompts

-- ============================================================================
-- 2. CREATE A/B TEST TRACKING TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS ab_tests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,

    -- Test definition
    name TEXT NOT NULL,
    description TEXT,
    hypothesis TEXT,
    variant_a_description TEXT,
    variant_b_description TEXT,

    -- Configuration
    metric TEXT DEFAULT 'reply_rate',  -- What we're measuring: 'reply_rate', 'open_rate', 'click_rate', 'conversion_rate'
    sample_size_target INTEGER,
    split_percentage INTEGER DEFAULT 50,  -- Percentage going to variant A (rest to B)

    -- Status
    status TEXT DEFAULT 'draft',  -- 'draft', 'running', 'paused', 'completed', 'cancelled'
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,

    -- Results
    winner TEXT,  -- 'A', 'B', 'no_difference', null (if not concluded)
    confidence FLOAT,  -- Statistical confidence (0-1)
    variant_a_count INTEGER DEFAULT 0,
    variant_b_count INTEGER DEFAULT 0,
    variant_a_success INTEGER DEFAULT 0,
    variant_b_success INTEGER DEFAULT 0,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(id),

    CONSTRAINT valid_status CHECK (status IN ('draft', 'running', 'paused', 'completed', 'cancelled')),
    CONSTRAINT valid_metric CHECK (metric IN ('reply_rate', 'open_rate', 'click_rate', 'conversion_rate', 'meeting_rate')),
    CONSTRAINT valid_split CHECK (split_percentage BETWEEN 1 AND 99)
);

-- Add foreign key constraint for ab_test_id on activities
ALTER TABLE activities
ADD CONSTRAINT fk_activities_ab_test
FOREIGN KEY (ab_test_id) REFERENCES ab_tests(id) ON DELETE SET NULL;

-- ============================================================================
-- 3. CREATE A/B TEST VARIANTS TABLE (for more than 2 variants)
-- ============================================================================

CREATE TABLE IF NOT EXISTS ab_test_variants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ab_test_id UUID NOT NULL REFERENCES ab_tests(id) ON DELETE CASCADE,

    -- Variant definition
    name TEXT NOT NULL,  -- 'A', 'B', 'C', 'control'
    description TEXT,

    -- Template/content variation
    template_id UUID REFERENCES email_templates(id),
    subject_line TEXT,
    message_body TEXT,

    -- Configuration
    weight INTEGER DEFAULT 50,  -- Traffic allocation weight

    -- Results
    send_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    success_rate FLOAT,  -- Calculated

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 4. UPDATE CONTENT_SNAPSHOT JSONB STRUCTURE DOCUMENTATION
-- ============================================================================

COMMENT ON COLUMN activities.content_snapshot IS '
Enhanced content snapshot structure:
{
  "subject": "string",
  "body_preview": "string (first 200 chars)",
  "body_full": "string (complete message)",
  "pain_points": ["array of pain points addressed"],
  "cta_type": "string (meeting, reply, link)",
  "personalization_used": ["array of fields used: first_name, company, etc"],
  "personalization_available": ["array of all available fields"],
  "word_count": "integer",
  "has_question": "boolean",
  "question_count": "integer",
  "links": ["array of URLs included"],
  "template_name": "string",
  "template_id": "uuid",
  "ai_model": "string (gpt-4, claude-3, etc)",
  "prompt_version": "string",
  "ab_variant": "string (A, B, control)",
  "ab_test_id": "uuid",
  "generation_params": {
    "temperature": "float",
    "max_tokens": "integer",
    "style": "string"
  }
}';

-- ============================================================================
-- 5. CREATE INDEXES FOR PERFORMANCE
-- ============================================================================

-- Template tracking
CREATE INDEX IF NOT EXISTS idx_activities_template_id ON activities(template_id) WHERE template_id IS NOT NULL;

-- A/B test tracking
CREATE INDEX IF NOT EXISTS idx_activities_ab_test_id ON activities(ab_test_id) WHERE ab_test_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_activities_ab_variant ON activities(ab_variant) WHERE ab_variant IS NOT NULL;

-- A/B tests lookup
CREATE INDEX IF NOT EXISTS idx_ab_tests_client_id ON ab_tests(client_id);
CREATE INDEX IF NOT EXISTS idx_ab_tests_campaign_id ON ab_tests(campaign_id);
CREATE INDEX IF NOT EXISTS idx_ab_tests_status ON ab_tests(status);

-- A/B test variants
CREATE INDEX IF NOT EXISTS idx_ab_test_variants_test_id ON ab_test_variants(ab_test_id);

-- ============================================================================
-- 6. TRIGGER TO UPDATE AB_TEST STATS
-- ============================================================================

CREATE OR REPLACE FUNCTION update_ab_test_variant_stats()
RETURNS TRIGGER AS $$
BEGIN
    -- When an activity with ab_test_id is created or updated
    IF NEW.ab_test_id IS NOT NULL AND NEW.ab_variant IS NOT NULL THEN
        -- Update variant counts
        IF NEW.ab_variant = 'A' THEN
            UPDATE ab_tests
            SET variant_a_count = variant_a_count + 1,
                updated_at = NOW()
            WHERE id = NEW.ab_test_id;
        ELSIF NEW.ab_variant = 'B' THEN
            UPDATE ab_tests
            SET variant_b_count = variant_b_count + 1,
                updated_at = NOW()
            WHERE id = NEW.ab_test_id;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER on_activity_ab_test_insert
    AFTER INSERT ON activities
    FOR EACH ROW
    WHEN (NEW.ab_test_id IS NOT NULL)
    EXECUTE FUNCTION update_ab_test_variant_stats();

-- ============================================================================
-- 7. TRIGGER TO UPDATE AB_TEST SUCCESS ON REPLY
-- ============================================================================

CREATE OR REPLACE FUNCTION update_ab_test_success_on_reply()
RETURNS TRIGGER AS $$
DECLARE
    activity_record RECORD;
BEGIN
    -- When a reply is created, find the related activity and update A/B test success
    SELECT ab_test_id, ab_variant INTO activity_record
    FROM activities
    WHERE id = NEW.activity_id;

    IF activity_record.ab_test_id IS NOT NULL AND activity_record.ab_variant IS NOT NULL THEN
        -- Only count positive replies as success
        IF NEW.intent IN ('interested', 'question', 'meeting_request') THEN
            IF activity_record.ab_variant = 'A' THEN
                UPDATE ab_tests
                SET variant_a_success = variant_a_success + 1,
                    updated_at = NOW()
                WHERE id = activity_record.ab_test_id;
            ELSIF activity_record.ab_variant = 'B' THEN
                UPDATE ab_tests
                SET variant_b_success = variant_b_success + 1,
                    updated_at = NOW()
                WHERE id = activity_record.ab_test_id;
            END IF;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER on_reply_ab_test_success
    AFTER INSERT ON replies
    FOR EACH ROW
    EXECUTE FUNCTION update_ab_test_success_on_reply();

-- ============================================================================
-- 8. HELPER FUNCTION TO CALCULATE AB TEST WINNER
-- ============================================================================

CREATE OR REPLACE FUNCTION calculate_ab_test_winner(test_id UUID)
RETURNS TABLE (
    winner TEXT,
    confidence FLOAT,
    variant_a_rate FLOAT,
    variant_b_rate FLOAT,
    is_significant BOOLEAN
) AS $$
DECLARE
    test_record RECORD;
    z_score FLOAT;
    p_pooled FLOAT;
    se FLOAT;
BEGIN
    SELECT * INTO test_record FROM ab_tests WHERE id = test_id;

    IF test_record IS NULL THEN
        RETURN;
    END IF;

    -- Calculate rates
    variant_a_rate := CASE
        WHEN test_record.variant_a_count > 0
        THEN test_record.variant_a_success::FLOAT / test_record.variant_a_count
        ELSE 0
    END;

    variant_b_rate := CASE
        WHEN test_record.variant_b_count > 0
        THEN test_record.variant_b_success::FLOAT / test_record.variant_b_count
        ELSE 0
    END;

    -- Calculate significance (simplified z-test for proportions)
    IF test_record.variant_a_count > 30 AND test_record.variant_b_count > 30 THEN
        p_pooled := (test_record.variant_a_success + test_record.variant_b_success)::FLOAT /
                    (test_record.variant_a_count + test_record.variant_b_count);

        IF p_pooled > 0 AND p_pooled < 1 THEN
            se := SQRT(p_pooled * (1 - p_pooled) * (1.0/test_record.variant_a_count + 1.0/test_record.variant_b_count));
            IF se > 0 THEN
                z_score := (variant_a_rate - variant_b_rate) / se;
                confidence := 1 - EXP(-0.5 * z_score * z_score);  -- Approximation
                is_significant := ABS(z_score) > 1.96;  -- 95% confidence
            ELSE
                confidence := 0;
                is_significant := FALSE;
            END IF;
        ELSE
            confidence := 0;
            is_significant := FALSE;
        END IF;
    ELSE
        confidence := 0;
        is_significant := FALSE;
    END IF;

    -- Determine winner
    IF is_significant THEN
        IF variant_a_rate > variant_b_rate THEN
            winner := 'A';
        ELSIF variant_b_rate > variant_a_rate THEN
            winner := 'B';
        ELSE
            winner := 'no_difference';
        END IF;
    ELSE
        winner := NULL;  -- Not enough data or not significant
    END IF;

    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 9. ROW LEVEL SECURITY FOR AB_TESTS
-- ============================================================================

ALTER TABLE ab_tests ENABLE ROW LEVEL SECURITY;
ALTER TABLE ab_test_variants ENABLE ROW LEVEL SECURITY;

-- Users can only see A/B tests for their clients
CREATE POLICY ab_tests_client_isolation ON ab_tests
    FOR ALL
    USING (
        client_id IN (
            SELECT client_id FROM memberships
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY ab_test_variants_client_isolation ON ab_test_variants
    FOR ALL
    USING (
        ab_test_id IN (
            SELECT id FROM ab_tests WHERE client_id IN (
                SELECT client_id FROM memberships
                WHERE user_id = auth.uid()
            )
        )
    );

-- ============================================================================
-- COMPLETE
-- ============================================================================
