-- FILE: supabase/migrations/037_lead_pool_client_ownership.sql
-- PURPOSE: Add client ownership and campaign assignment directly to lead_pool
-- DATE: January 2026
-- CHANGE: Simplify architecture - leads are sourced FOR a client, owned by them
-- REFERENCE: CEO vision - "we just assign a client id column that allocates that lead to a client id"

-- ============================================
-- ADD CLIENT OWNERSHIP TO LEAD POOL
-- ============================================

-- Client ownership (nullable = unassigned/available for sourcing)
ALTER TABLE lead_pool
ADD COLUMN IF NOT EXISTS client_id UUID REFERENCES clients(id) ON DELETE SET NULL;

-- Campaign assignment (which campaign within the client)
ALTER TABLE lead_pool
ADD COLUMN IF NOT EXISTS campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL;

-- ============================================
-- ADD ALS SCORING TO LEAD POOL
-- ============================================
-- Previously only in lead_assignments, now on lead_pool for direct access

ALTER TABLE lead_pool
ADD COLUMN IF NOT EXISTS als_score INTEGER;

ALTER TABLE lead_pool
ADD COLUMN IF NOT EXISTS als_tier TEXT;

ALTER TABLE lead_pool
ADD COLUMN IF NOT EXISTS als_components JSONB;

ALTER TABLE lead_pool
ADD COLUMN IF NOT EXISTS scored_at TIMESTAMPTZ;

-- ============================================
-- ADD OUTREACH TRACKING TO LEAD POOL
-- ============================================
-- Simplify by tracking directly on lead

ALTER TABLE lead_pool
ADD COLUMN IF NOT EXISTS first_contacted_at TIMESTAMPTZ;

ALTER TABLE lead_pool
ADD COLUMN IF NOT EXISTS last_contacted_at TIMESTAMPTZ;

ALTER TABLE lead_pool
ADD COLUMN IF NOT EXISTS total_touches INTEGER DEFAULT 0;

ALTER TABLE lead_pool
ADD COLUMN IF NOT EXISTS channels_used TEXT[] DEFAULT '{}';

ALTER TABLE lead_pool
ADD COLUMN IF NOT EXISTS has_replied BOOLEAN DEFAULT FALSE;

ALTER TABLE lead_pool
ADD COLUMN IF NOT EXISTS replied_at TIMESTAMPTZ;

ALTER TABLE lead_pool
ADD COLUMN IF NOT EXISTS reply_intent TEXT;

-- ============================================
-- ADD CONSTRAINTS
-- ============================================

-- ALS tier must be valid
ALTER TABLE lead_pool
ADD CONSTRAINT valid_als_tier
CHECK (als_tier IS NULL OR als_tier IN ('hot', 'warm', 'cool', 'cold', 'dead'));

-- ALS score must be 0-100
ALTER TABLE lead_pool
ADD CONSTRAINT valid_als_score
CHECK (als_score IS NULL OR (als_score >= 0 AND als_score <= 100));

-- ============================================
-- ADD INDEXES FOR NEW COLUMNS
-- ============================================

-- Client ownership lookups
CREATE INDEX IF NOT EXISTS idx_pool_client_id
ON lead_pool(client_id) WHERE client_id IS NOT NULL;

-- Client + available leads (for sourcing)
CREATE INDEX IF NOT EXISTS idx_pool_client_available
ON lead_pool(client_id, pool_status) WHERE pool_status = 'available';

-- Campaign lookups
CREATE INDEX IF NOT EXISTS idx_pool_campaign_id
ON lead_pool(campaign_id) WHERE campaign_id IS NOT NULL;

-- ALS tier queries
CREATE INDEX IF NOT EXISTS idx_pool_als_tier
ON lead_pool(als_tier) WHERE als_tier IS NOT NULL;

-- Hot leads by client
CREATE INDEX IF NOT EXISTS idx_pool_client_hot
ON lead_pool(client_id, als_score DESC) WHERE als_tier = 'hot';

-- Client + campaign composite
CREATE INDEX IF NOT EXISTS idx_pool_client_campaign
ON lead_pool(client_id, campaign_id) WHERE client_id IS NOT NULL;

-- Outreach scheduling
CREATE INDEX IF NOT EXISTS idx_pool_last_contacted
ON lead_pool(last_contacted_at DESC NULLS LAST);

-- Leads needing contact
CREATE INDEX IF NOT EXISTS idx_pool_not_contacted
ON lead_pool(client_id, created_at)
WHERE client_id IS NOT NULL AND first_contacted_at IS NULL;

-- ============================================
-- MIGRATE EXISTING DATA FROM LEAD_ASSIGNMENTS
-- ============================================

-- Copy client_id, campaign_id, and ALS data from lead_assignments to lead_pool
UPDATE lead_pool lp
SET
    client_id = la.client_id,
    campaign_id = la.campaign_id,
    als_score = la.als_score,
    als_tier = la.als_tier,
    als_components = la.als_components,
    scored_at = la.scored_at,
    first_contacted_at = la.first_contacted_at,
    last_contacted_at = la.last_contacted_at,
    total_touches = la.total_touches,
    channels_used = la.channels_used::text[],
    has_replied = la.has_replied,
    replied_at = la.replied_at,
    reply_intent = la.reply_intent
FROM lead_assignments la
WHERE lp.id = la.lead_pool_id
AND la.status = 'active';

-- ============================================
-- UPDATE POOL STATUS BASED ON CLIENT_ID
-- ============================================

-- Leads with client_id should be 'assigned'
UPDATE lead_pool
SET pool_status = 'assigned'
WHERE client_id IS NOT NULL
AND pool_status = 'available';

-- ============================================
-- UPDATED FUNCTIONS
-- ============================================

-- Updated function to check lead availability (now checks client_id on lead_pool)
CREATE OR REPLACE FUNCTION is_lead_available_v2(p_lead_pool_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    v_pool_status pool_status;
    v_client_id UUID;
BEGIN
    SELECT pool_status, client_id INTO v_pool_status, v_client_id
    FROM lead_pool
    WHERE id = p_lead_pool_id;

    -- Must be in available status AND not assigned to a client
    RETURN v_pool_status = 'available' AND v_client_id IS NULL;
END;
$$ LANGUAGE plpgsql STABLE;

-- New function to assign lead directly in lead_pool
CREATE OR REPLACE FUNCTION assign_lead_to_client_v2(
    p_lead_pool_id UUID,
    p_client_id UUID,
    p_campaign_id UUID DEFAULT NULL
)
RETURNS BOOLEAN AS $$
BEGIN
    -- Check if lead is available
    IF NOT is_lead_available_v2(p_lead_pool_id) THEN
        RAISE EXCEPTION 'Lead % is not available for assignment', p_lead_pool_id;
    END IF;

    -- Update lead_pool directly
    UPDATE lead_pool
    SET
        client_id = p_client_id,
        campaign_id = p_campaign_id,
        pool_status = 'assigned',
        updated_at = NOW()
    WHERE id = p_lead_pool_id;

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- New function to get client's leads with ALS filtering
CREATE OR REPLACE FUNCTION get_client_leads_by_tier(
    p_client_id UUID,
    p_tier TEXT DEFAULT NULL,
    p_limit INTEGER DEFAULT 100
)
RETURNS TABLE (
    lead_id UUID,
    email TEXT,
    first_name TEXT,
    last_name TEXT,
    company_name TEXT,
    als_score INTEGER,
    als_tier TEXT,
    campaign_id UUID
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        lp.id,
        lp.email,
        lp.first_name,
        lp.last_name,
        lp.company_name,
        lp.als_score,
        lp.als_tier,
        lp.campaign_id
    FROM lead_pool lp
    WHERE lp.client_id = p_client_id
    AND lp.pool_status = 'assigned'
    AND (p_tier IS NULL OR lp.als_tier = p_tier)
    ORDER BY lp.als_score DESC NULLS LAST
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================
-- UPDATED VIEWS
-- ============================================

-- Client lead stats (direct from lead_pool)
CREATE OR REPLACE VIEW v_client_lead_stats AS
SELECT
    lp.client_id,
    c.name AS client_name,
    COUNT(*) AS total_leads,
    COUNT(*) FILTER (WHERE lp.als_tier = 'hot') AS hot_leads,
    COUNT(*) FILTER (WHERE lp.als_tier = 'warm') AS warm_leads,
    COUNT(*) FILTER (WHERE lp.als_tier = 'cool') AS cool_leads,
    COUNT(*) FILTER (WHERE lp.als_tier = 'cold') AS cold_leads,
    COUNT(*) FILTER (WHERE lp.als_tier = 'dead') AS dead_leads,
    COUNT(*) FILTER (WHERE lp.first_contacted_at IS NOT NULL) AS contacted_leads,
    COUNT(*) FILTER (WHERE lp.has_replied = TRUE) AS replied_leads,
    AVG(lp.als_score) AS avg_als_score,
    SUM(lp.total_touches) AS total_touches
FROM lead_pool lp
JOIN clients c ON c.id = lp.client_id
WHERE lp.client_id IS NOT NULL
GROUP BY lp.client_id, c.company_name;

-- ============================================
-- COMMENTS
-- ============================================

COMMENT ON COLUMN lead_pool.client_id IS 'Client who owns this lead. NULL = available for sourcing.';
COMMENT ON COLUMN lead_pool.campaign_id IS 'Campaign this lead is assigned to within the client.';
COMMENT ON COLUMN lead_pool.als_score IS 'Agency Lead Score (0-100). Higher = better fit.';
COMMENT ON COLUMN lead_pool.als_tier IS 'ALS tier: hot (85+), warm (60-84), cool (35-59), cold (20-34), dead (<20).';
COMMENT ON COLUMN lead_pool.als_components IS 'Breakdown of ALS score components (data_quality, authority, company_fit, timing, risk).';

-- ============================================
-- NOTE ON LEAD_ASSIGNMENTS
-- ============================================
-- The lead_assignments table is NOT dropped in this migration.
-- It's kept for:
--   1. Historical data (past assignments)
--   2. Backward compatibility during transition
--   3. Future multi-campaign support if needed
--
-- New code should use lead_pool.client_id and lead_pool.campaign_id directly.
-- Old code using lead_assignments will continue to work but should be migrated.

-- ============================================
-- VERIFICATION CHECKLIST
-- ============================================
-- [x] Added client_id column to lead_pool
-- [x] Added campaign_id column to lead_pool
-- [x] Added als_score, als_tier, als_components columns
-- [x] Added outreach tracking columns
-- [x] Added constraints for ALS values
-- [x] Added indexes for all new columns
-- [x] Migrated existing data from lead_assignments
-- [x] Created v2 functions for new architecture
-- [x] Created v_client_lead_stats view
-- [x] Preserved lead_assignments for backward compatibility
