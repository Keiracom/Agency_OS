-- ============================================================================
-- Migration 081: CIS Negative Signal Learning (Gap 2 - Directive #157)
-- ============================================================================
-- Adds timestamp columns for negative signals (bounce, complaint, unsubscribe)
-- and updates the final_outcome constraint to include new outcome types.
-- 
-- Negative signals are critical learning data:
-- - bounced → data_quality_failure (bad enrichment, not bad targeting)
-- - complained → targeting_failure (wrong ICP or wrong message)  
-- - unsubscribed → soft_rejection (low fit, not hard rejection)
-- ============================================================================

-- Add timestamp columns for negative events
ALTER TABLE cis_outreach_outcomes 
ADD COLUMN IF NOT EXISTS bounced_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS complained_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS unsubscribed_at TIMESTAMPTZ;

-- Update the final_outcome CHECK constraint to include new negative signal types
-- First drop the existing constraint
ALTER TABLE cis_outreach_outcomes 
DROP CONSTRAINT IF EXISTS cis_outreach_outcomes_final_outcome_check;

-- Add new constraint with expanded outcome types
ALTER TABLE cis_outreach_outcomes 
ADD CONSTRAINT cis_outreach_outcomes_final_outcome_check 
CHECK (final_outcome IN (
    -- Positive/neutral outcomes
    'no_response', 'opened_only', 'clicked_only', 
    'replied_positive', 'replied_negative', 'replied_neutral',
    'meeting_booked', 'converted',
    -- Legacy negative outcomes (keep for backward compat)
    'unsubscribed', 'bounced',
    -- New CIS Learning outcome types (Gap 2 fix)
    'data_quality_failure',   -- bounced: signals bad enrichment data
    'targeting_failure',      -- complained/spam: wrong ICP or message
    'soft_rejection'          -- unsubscribed: low fit, not hard rejection
));

-- Add indexes for negative signal analysis
CREATE INDEX IF NOT EXISTS idx_cis_outcomes_bounced ON cis_outreach_outcomes(bounced_at) WHERE bounced_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_cis_outcomes_complained ON cis_outreach_outcomes(complained_at) WHERE complained_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_cis_outcomes_unsubscribed ON cis_outreach_outcomes(unsubscribed_at) WHERE unsubscribed_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_cis_outcomes_negative ON cis_outreach_outcomes(final_outcome) 
    WHERE final_outcome IN ('data_quality_failure', 'targeting_failure', 'soft_rejection');

COMMENT ON COLUMN cis_outreach_outcomes.bounced_at IS 'Timestamp when email bounced - signals data_quality_failure';
COMMENT ON COLUMN cis_outreach_outcomes.complained_at IS 'Timestamp when recipient marked as spam - signals targeting_failure';
COMMENT ON COLUMN cis_outreach_outcomes.unsubscribed_at IS 'Timestamp when recipient unsubscribed - signals soft_rejection';
