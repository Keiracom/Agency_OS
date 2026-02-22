-- Migration: 065_campaign_channel_metrics.sql
-- Purpose: Add channel metrics JSONB and targeting filter columns for campaigns
-- Sprint: Step 5/8 - Campaign Targeting Filters + ICP Auto-Populate

-- Add channel_metrics JSONB to campaigns for per-channel performance tracking
ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS channel_metrics JSONB DEFAULT '{}';
-- Structure: {"email": {"sent": 0, "opened": 0, "clicked": 0}, "linkedin": {...}, "sms": {...}, "voice": {...}}

-- Add targeting filter columns to campaigns (matches lead data fields)
ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS target_als_tiers TEXT[] DEFAULT ARRAY['Hot', 'Warm', 'Cool', 'Cold'];
ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS target_hiring_only BOOLEAN DEFAULT false;
ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS target_revenue_min_aud NUMERIC DEFAULT NULL;
ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS target_revenue_max_aud NUMERIC DEFAULT NULL;
ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS target_funding_stages TEXT[] DEFAULT NULL;
-- Options: Seed, Series A, Series B, Series C+, Bootstrapped, Unknown

-- Add revenue and funding_stage columns to leads table (copy from lead_pool)
ALTER TABLE leads ADD COLUMN IF NOT EXISTS organization_revenue_aud NUMERIC DEFAULT NULL;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS organization_funding_stage TEXT DEFAULT NULL;

-- Add ICP-prefilled flag to track Maya suggestions
ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS icp_prefilled BOOLEAN DEFAULT false;
ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS icp_source_profile_id UUID REFERENCES agency_service_profile(id);

-- Index for efficient filtering
CREATE INDEX IF NOT EXISTS idx_leads_als_tier ON leads(als_tier);
CREATE INDEX IF NOT EXISTS idx_leads_org_hiring ON leads(organization_is_hiring);
CREATE INDEX IF NOT EXISTS idx_leads_org_revenue ON leads(organization_revenue_aud);
CREATE INDEX IF NOT EXISTS idx_leads_funding_stage ON leads(organization_funding_stage);
CREATE INDEX IF NOT EXISTS idx_campaigns_als_tiers ON campaigns USING GIN (target_als_tiers);
CREATE INDEX IF NOT EXISTS idx_campaigns_funding_stages ON campaigns USING GIN (target_funding_stages);

COMMENT ON COLUMN campaigns.channel_metrics IS 'Per-channel performance metrics: {channel: {sent, opened, clicked, replied, converted}}';
COMMENT ON COLUMN campaigns.target_als_tiers IS 'Filter leads by ALS tier: Hot, Warm, Cool, Cold';
COMMENT ON COLUMN campaigns.target_hiring_only IS 'Only include companies actively hiring';
COMMENT ON COLUMN campaigns.target_revenue_min_aud IS 'Minimum company revenue in AUD';
COMMENT ON COLUMN campaigns.target_revenue_max_aud IS 'Maximum company revenue in AUD';
COMMENT ON COLUMN campaigns.target_funding_stages IS 'Filter by funding stage: Seed, Series A, Series B, Series C+, Bootstrapped, Unknown';
COMMENT ON COLUMN campaigns.icp_prefilled IS 'Whether Maya auto-populated from ICP';
COMMENT ON COLUMN campaigns.icp_source_profile_id IS 'Source agency_service_profile for ICP prefill';
