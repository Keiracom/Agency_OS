-- 092_discovery_log.sql
-- Directive #217: Location tracking for quota loop
CREATE TABLE IF NOT EXISTS campaign_discovery_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID REFERENCES campaigns(id),
    location TEXT NOT NULL,
    state TEXT NOT NULL,
    swept_at TIMESTAMPTZ DEFAULT NOW(),
    leads_found INTEGER DEFAULT 0,
    leads_qualified INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_discovery_log_campaign ON campaign_discovery_log(campaign_id);
CREATE INDEX IF NOT EXISTS idx_discovery_log_location ON campaign_discovery_log(campaign_id, location);
