-- Migration: 035_sdk_enrichment_fields.sql
-- Purpose: Add SDK enrichment fields to leads table for Hot lead processing
-- Date: 2026-01-19
-- Phase: SDK Integration for Hot Leads

-- ============================================
-- SDK ENRICHMENT FIELDS ON LEADS TABLE
-- ============================================

-- SDK enrichment data (funding, hiring, news, pain points, etc.)
ALTER TABLE leads
ADD COLUMN IF NOT EXISTS sdk_enrichment JSONB;

-- Priority signals that triggered SDK enrichment
-- Examples: recent_funding_30d, hiring_5_roles, tech_match_90pct
ALTER TABLE leads
ADD COLUMN IF NOT EXISTS sdk_signals TEXT[];

-- SDK cost tracking (AUD)
ALTER TABLE leads
ADD COLUMN IF NOT EXISTS sdk_cost_aud DECIMAL(10, 4);

-- When SDK enrichment was last run
ALTER TABLE leads
ADD COLUMN IF NOT EXISTS sdk_enriched_at TIMESTAMPTZ;

-- SDK voice knowledge base (for voice calls)
ALTER TABLE leads
ADD COLUMN IF NOT EXISTS sdk_voice_kb JSONB;

-- SDK email content (generated email subject/body)
ALTER TABLE leads
ADD COLUMN IF NOT EXISTS sdk_email_content JSONB;

-- ============================================
-- INDEXES FOR SDK ANALYTICS
-- ============================================

-- Index for querying leads by SDK signals (GIN for array containment queries)
CREATE INDEX IF NOT EXISTS idx_leads_sdk_signals
ON leads USING GIN (sdk_signals);

-- Index for finding SDK-enriched leads
CREATE INDEX IF NOT EXISTS idx_leads_sdk_enriched
ON leads (sdk_enriched_at)
WHERE sdk_enriched_at IS NOT NULL;

-- Index for SDK cost tracking
CREATE INDEX IF NOT EXISTS idx_leads_sdk_cost
ON leads (sdk_cost_aud)
WHERE sdk_cost_aud IS NOT NULL;

-- ============================================
-- SDK USAGE LOG TABLE (extends existing)
-- ============================================
-- Note: sdk_usage_log table already exists in migration 018

-- Add columns to track specific agent types
ALTER TABLE sdk_usage_log
ADD COLUMN IF NOT EXISTS agent_type VARCHAR(50);

ALTER TABLE sdk_usage_log
ADD COLUMN IF NOT EXISTS signals_used TEXT[];

ALTER TABLE sdk_usage_log
ADD COLUMN IF NOT EXISTS output_schema VARCHAR(100);

-- Index for agent type queries
CREATE INDEX IF NOT EXISTS idx_sdk_usage_log_agent_type
ON sdk_usage_log (agent_type);

-- ============================================
-- LEAD POOL SDK FIELDS
-- ============================================

-- Add SDK fields to lead_pool table for pool-first architecture
ALTER TABLE lead_pool
ADD COLUMN IF NOT EXISTS sdk_enrichment JSONB;

ALTER TABLE lead_pool
ADD COLUMN IF NOT EXISTS sdk_signals TEXT[];

ALTER TABLE lead_pool
ADD COLUMN IF NOT EXISTS sdk_cost_aud DECIMAL(10, 4);

ALTER TABLE lead_pool
ADD COLUMN IF NOT EXISTS sdk_enriched_at TIMESTAMPTZ;

-- Index for lead pool SDK signals
CREATE INDEX IF NOT EXISTS idx_lead_pool_sdk_signals
ON lead_pool USING GIN (sdk_signals);

-- ============================================
-- SDK ANALYTICS VIEW
-- ============================================

CREATE OR REPLACE VIEW v_sdk_usage_by_client AS
SELECT
    l.client_id,
    c.name as client_name,
    COUNT(*) FILTER (WHERE l.sdk_enrichment IS NOT NULL) as sdk_enriched_count,
    COUNT(*) FILTER (WHERE l.sdk_voice_kb IS NOT NULL) as sdk_voice_kb_count,
    COUNT(*) FILTER (WHERE l.sdk_email_content IS NOT NULL) as sdk_email_count,
    COALESCE(SUM(l.sdk_cost_aud), 0) as total_sdk_cost_aud,
    COUNT(*) FILTER (WHERE l.als_score >= 85) as hot_leads_count,
    COUNT(*) FILTER (WHERE l.als_score >= 85 AND l.sdk_enrichment IS NOT NULL) as hot_leads_sdk_enriched
FROM leads l
JOIN clients c ON l.client_id = c.id
WHERE l.deleted_at IS NULL
GROUP BY l.client_id, c.name;

-- View for SDK signal distribution
CREATE OR REPLACE VIEW v_sdk_signal_distribution AS
SELECT
    signal,
    COUNT(*) as lead_count,
    AVG(l.als_score) as avg_als_score,
    COALESCE(SUM(l.sdk_cost_aud), 0) as total_cost_aud
FROM leads l,
     unnest(l.sdk_signals) as signal
WHERE l.deleted_at IS NULL
  AND l.sdk_signals IS NOT NULL
GROUP BY signal
ORDER BY lead_count DESC;

-- ============================================
-- COMMENTS
-- ============================================

COMMENT ON COLUMN leads.sdk_enrichment IS 'SDK enrichment data including funding, hiring, news, pain points';
COMMENT ON COLUMN leads.sdk_signals IS 'Priority signals that triggered SDK enrichment (recent_funding, hiring, etc.)';
COMMENT ON COLUMN leads.sdk_cost_aud IS 'Cost of SDK enrichment in AUD';
COMMENT ON COLUMN leads.sdk_enriched_at IS 'When SDK enrichment was last performed';
COMMENT ON COLUMN leads.sdk_voice_kb IS 'SDK-generated voice knowledge base for AI calls';
COMMENT ON COLUMN leads.sdk_email_content IS 'SDK-generated email content (subject, body)';
