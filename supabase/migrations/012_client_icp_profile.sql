-- FILE: supabase/migrations/012_client_icp_profile.sql
-- PURPOSE: Add ICP (Ideal Customer Profile) fields to clients and portfolio tracking
-- PHASE: 11 (ICP Discovery System)
-- TASK: ICP-001
-- DEPENDENCIES: 002_clients_users_memberships.sql
-- RULES APPLIED:
--   - Rule 1: Follow blueprint exactly
--   - Rule 14: Soft deletes only (deleted_at column)

-- ============================================
-- ALTER CLIENTS: Add ICP Fields
-- ============================================

-- About the Agency
ALTER TABLE clients ADD COLUMN IF NOT EXISTS website_url TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS company_description TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS services_offered TEXT[];
ALTER TABLE clients ADD COLUMN IF NOT EXISTS years_in_business INTEGER;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS team_size INTEGER;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS value_proposition TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS default_offer TEXT;

-- ICP Configuration
ALTER TABLE clients ADD COLUMN IF NOT EXISTS icp_industries TEXT[];
ALTER TABLE clients ADD COLUMN IF NOT EXISTS icp_company_sizes TEXT[];
ALTER TABLE clients ADD COLUMN IF NOT EXISTS icp_revenue_range TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS icp_locations TEXT[];
ALTER TABLE clients ADD COLUMN IF NOT EXISTS icp_titles TEXT[];
ALTER TABLE clients ADD COLUMN IF NOT EXISTS icp_pain_points TEXT[];
ALTER TABLE clients ADD COLUMN IF NOT EXISTS icp_keywords TEXT[];
ALTER TABLE clients ADD COLUMN IF NOT EXISTS icp_exclusions TEXT[];

-- Custom ALS weights (overrides defaults)
-- Format: {"data_quality": 20, "authority": 25, "company_fit": 25, "timing": 15, "risk": 15}
ALTER TABLE clients ADD COLUMN IF NOT EXISTS als_weights JSONB DEFAULT '{}';

-- ICP extraction status
ALTER TABLE clients ADD COLUMN IF NOT EXISTS icp_extracted_at TIMESTAMPTZ;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS icp_extraction_source TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS icp_confirmed_at TIMESTAMPTZ;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS icp_extraction_job_id TEXT;

-- ============================================
-- CLIENT_PORTFOLIO: Discovered clients/case studies
-- ============================================

CREATE TABLE IF NOT EXISTS client_portfolio (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,

    -- Company info
    company_name TEXT NOT NULL,
    company_domain TEXT,
    company_industry TEXT,
    company_size TEXT,
    company_location TEXT,
    company_linkedin_url TEXT,

    -- How discovered
    source TEXT NOT NULL,  -- 'logo', 'case_study', 'testimonial', 'manual'
    source_url TEXT,

    -- Enriched data from Apollo
    enriched_data JSONB DEFAULT '{}',
    enriched_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ  -- Soft delete (Rule 14)
);

-- Trigger for updated_at
CREATE TRIGGER client_portfolio_updated_at
    BEFORE UPDATE ON client_portfolio
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ============================================
-- ICP_EXTRACTION_JOBS: Track async extraction jobs
-- ============================================

CREATE TABLE IF NOT EXISTS icp_extraction_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,

    -- Job status
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, running, completed, failed
    website_url TEXT NOT NULL,

    -- Progress tracking
    current_step TEXT,
    total_steps INTEGER DEFAULT 8,
    completed_steps INTEGER DEFAULT 0,

    -- Results
    raw_html TEXT,
    parsed_content JSONB,
    extracted_icp JSONB,
    error_message TEXT,

    -- Timestamps
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- INDEXES
-- ============================================

CREATE INDEX IF NOT EXISTS idx_client_portfolio_client ON client_portfolio(client_id)
    WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_client_portfolio_domain ON client_portfolio(company_domain)
    WHERE company_domain IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_client_portfolio_source ON client_portfolio(client_id, source)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_icp_extraction_jobs_client ON icp_extraction_jobs(client_id);
CREATE INDEX IF NOT EXISTS idx_icp_extraction_jobs_status ON icp_extraction_jobs(status)
    WHERE status IN ('pending', 'running');

-- Index on clients for ICP-related queries
CREATE INDEX IF NOT EXISTS idx_clients_icp_extracted ON clients(icp_extracted_at)
    WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_clients_icp_confirmed ON clients(icp_confirmed_at)
    WHERE deleted_at IS NULL;

-- ============================================
-- RLS POLICIES FOR NEW TABLES
-- ============================================

-- Enable RLS
ALTER TABLE client_portfolio ENABLE ROW LEVEL SECURITY;
ALTER TABLE icp_extraction_jobs ENABLE ROW LEVEL SECURITY;

-- client_portfolio: Users can view/manage portfolio for their clients
CREATE POLICY client_portfolio_select ON client_portfolio
    FOR SELECT
    USING (client_id IN (SELECT get_user_client_ids()));

CREATE POLICY client_portfolio_insert ON client_portfolio
    FOR INSERT
    WITH CHECK (client_id IN (SELECT get_user_client_ids()));

CREATE POLICY client_portfolio_update ON client_portfolio
    FOR UPDATE
    USING (client_id IN (SELECT get_user_client_ids()))
    WITH CHECK (client_id IN (SELECT get_user_client_ids()));

CREATE POLICY client_portfolio_delete ON client_portfolio
    FOR DELETE
    USING (client_id IN (SELECT get_user_client_ids()));

-- icp_extraction_jobs: Users can view jobs for their clients
CREATE POLICY icp_extraction_jobs_select ON icp_extraction_jobs
    FOR SELECT
    USING (client_id IN (SELECT get_user_client_ids()));

CREATE POLICY icp_extraction_jobs_insert ON icp_extraction_jobs
    FOR INSERT
    WITH CHECK (client_id IN (SELECT get_user_client_ids()));

CREATE POLICY icp_extraction_jobs_update ON icp_extraction_jobs
    FOR UPDATE
    USING (client_id IN (SELECT get_user_client_ids()));

-- ============================================
-- HELPER FUNCTION: Update ICP from extraction
-- ============================================

CREATE OR REPLACE FUNCTION update_client_icp_from_extraction(
    p_client_id UUID,
    p_extraction_data JSONB
)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE clients
    SET
        website_url = COALESCE(p_extraction_data->>'website_url', website_url),
        company_description = COALESCE(p_extraction_data->>'company_description', company_description),
        services_offered = COALESCE(
            (SELECT array_agg(x)::TEXT[] FROM jsonb_array_elements_text(p_extraction_data->'services_offered') AS x),
            services_offered
        ),
        value_proposition = COALESCE(p_extraction_data->>'value_proposition', value_proposition),
        team_size = COALESCE((p_extraction_data->>'team_size')::INTEGER, team_size),
        icp_industries = COALESCE(
            (SELECT array_agg(x)::TEXT[] FROM jsonb_array_elements_text(p_extraction_data->'icp_industries') AS x),
            icp_industries
        ),
        icp_company_sizes = COALESCE(
            (SELECT array_agg(x)::TEXT[] FROM jsonb_array_elements_text(p_extraction_data->'icp_company_sizes') AS x),
            icp_company_sizes
        ),
        icp_locations = COALESCE(
            (SELECT array_agg(x)::TEXT[] FROM jsonb_array_elements_text(p_extraction_data->'icp_locations') AS x),
            icp_locations
        ),
        icp_titles = COALESCE(
            (SELECT array_agg(x)::TEXT[] FROM jsonb_array_elements_text(p_extraction_data->'icp_titles') AS x),
            icp_titles
        ),
        icp_pain_points = COALESCE(
            (SELECT array_agg(x)::TEXT[] FROM jsonb_array_elements_text(p_extraction_data->'icp_pain_points') AS x),
            icp_pain_points
        ),
        als_weights = COALESCE(p_extraction_data->'als_weights', als_weights),
        icp_extracted_at = NOW(),
        icp_extraction_source = 'ai_extraction',
        updated_at = NOW()
    WHERE id = p_client_id
    AND deleted_at IS NULL;

    RETURN FOUND;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- VERIFICATION CHECKLIST
-- ============================================
-- [x] ICP fields added to clients table
-- [x] client_portfolio table created with all fields
-- [x] icp_extraction_jobs table for async tracking
-- [x] Soft delete columns (deleted_at) where applicable (Rule 14)
-- [x] updated_at trigger on client_portfolio
-- [x] Indexes for performance on all new tables
-- [x] RLS policies for multi-tenant security
-- [x] Helper function for ICP update
-- [x] No hardcoded credentials
