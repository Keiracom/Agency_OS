-- FILE: supabase/migrations/038_campaign_allocation.sql
-- PURPOSE: Add campaign type and lead allocation fields
-- DATE: January 2026
-- REFERENCE: CEO vision - AI-suggested + custom campaigns with % lead allocation

-- ============================================
-- ADD CAMPAIGN TYPE AND ALLOCATION
-- ============================================

-- Campaign type (ai_suggested or custom)
ALTER TABLE campaigns
ADD COLUMN IF NOT EXISTS campaign_type VARCHAR(20) NOT NULL DEFAULT 'custom';

-- Lead allocation percentage (% of client's total leads for this campaign)
ALTER TABLE campaigns
ADD COLUMN IF NOT EXISTS lead_allocation_pct INTEGER NOT NULL DEFAULT 100;

-- Lead count (calculated from pct × client's total leads)
ALTER TABLE campaigns
ADD COLUMN IF NOT EXISTS lead_count INTEGER NOT NULL DEFAULT 0;

-- AI suggestion reason (why AI suggested this campaign, if ai_suggested)
ALTER TABLE campaigns
ADD COLUMN IF NOT EXISTS ai_suggestion_reason TEXT;

-- ============================================
-- CONSTRAINTS
-- ============================================

-- Campaign type must be valid
ALTER TABLE campaigns
ADD CONSTRAINT valid_campaign_type
CHECK (campaign_type IN ('ai_suggested', 'custom'));

-- Lead allocation must be 1-100%
ALTER TABLE campaigns
ADD CONSTRAINT valid_lead_allocation_pct
CHECK (lead_allocation_pct >= 1 AND lead_allocation_pct <= 100);

-- ============================================
-- INDEXES
-- ============================================

-- Filter by campaign type
CREATE INDEX IF NOT EXISTS idx_campaigns_type
ON campaigns(campaign_type);

-- Client + type (for counting AI vs custom)
CREATE INDEX IF NOT EXISTS idx_campaigns_client_type
ON campaigns(client_id, campaign_type);

-- ============================================
-- HELPER FUNCTION: Validate client campaign allocation
-- ============================================

-- Ensure client's total campaign allocation <= 100%
CREATE OR REPLACE FUNCTION validate_client_campaign_allocation()
RETURNS TRIGGER AS $$
DECLARE
    total_allocation INTEGER;
BEGIN
    -- Calculate total allocation for this client (excluding current campaign if updating)
    SELECT COALESCE(SUM(lead_allocation_pct), 0)
    INTO total_allocation
    FROM campaigns
    WHERE client_id = NEW.client_id
    AND status IN ('draft', 'active', 'paused')
    AND deleted_at IS NULL
    AND id != COALESCE(NEW.id, '00000000-0000-0000-0000-000000000000'::uuid);

    -- Add new/updated allocation
    total_allocation := total_allocation + NEW.lead_allocation_pct;

    IF total_allocation > 100 THEN
        RAISE EXCEPTION 'Total campaign allocation (%) exceeds 100%% for client', total_allocation;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger
DROP TRIGGER IF EXISTS check_campaign_allocation ON campaigns;
CREATE TRIGGER check_campaign_allocation
    BEFORE INSERT OR UPDATE ON campaigns
    FOR EACH ROW
    EXECUTE FUNCTION validate_client_campaign_allocation();

-- ============================================
-- COMMENTS
-- ============================================

COMMENT ON COLUMN campaigns.campaign_type IS 'ai_suggested (from ICP analysis) or custom (user created)';
COMMENT ON COLUMN campaigns.lead_allocation_pct IS 'Percentage of client''s total leads allocated to this campaign (1-100)';
COMMENT ON COLUMN campaigns.lead_count IS 'Actual lead count (calculated from allocation_pct × client tier leads)';
COMMENT ON COLUMN campaigns.ai_suggestion_reason IS 'Explanation of why AI suggested this campaign segment';

-- ============================================
-- VERIFICATION CHECKLIST
-- ============================================
-- [x] Added campaign_type column
-- [x] Added lead_allocation_pct column
-- [x] Added lead_count column
-- [x] Added ai_suggestion_reason column
-- [x] Added constraints for valid values
-- [x] Added indexes for performance
-- [x] Added trigger to validate total allocation <= 100%
