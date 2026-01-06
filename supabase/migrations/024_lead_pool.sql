-- FILE: supabase/migrations/024_lead_pool.sql
-- PURPOSE: Centralised Lead Pool with exclusive assignment for CIS data completeness
-- PHASE: 24A (Lead Pool Architecture)
-- TASK: POOL-001, POOL-002, POOL-003
-- DEPENDENCIES: 004_leads_suppression.sql
-- RULES APPLIED:
--   - Rule 1: Follow blueprint exactly
--   - Rule 14: Soft deletes only
--   - Rule 17: Platform-wide lead ownership

-- ============================================
-- ENUMS: Pool-specific types
-- ============================================

-- Pool lead status
CREATE TYPE pool_status AS ENUM (
    'available',      -- Not assigned to any client
    'assigned',       -- Assigned to a client
    'converted',      -- Lead has converted (stays with client)
    'bounced',        -- Email bounced globally
    'unsubscribed',   -- Lead requested no contact
    'invalid'         -- Bad data, do not use
);

-- Assignment status
CREATE TYPE assignment_status AS ENUM (
    'active',         -- Currently assigned to client
    'released',       -- Released back to pool
    'converted',      -- Lead converted for this client
    'expired'         -- Assignment expired (not contacted)
);

-- Email verification status
CREATE TYPE email_status_type AS ENUM (
    'verified',       -- Confirmed deliverable
    'guessed',        -- Inferred, not confirmed
    'invalid',        -- Known bad
    'catch_all',      -- Domain accepts all
    'unknown'         -- Not checked
);

-- ============================================
-- LEAD POOL: Platform-wide lead repository
-- ============================================

CREATE TABLE lead_pool (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- ===== UNIQUE IDENTIFIERS =====
    apollo_id TEXT UNIQUE,              -- Apollo's internal ID (primary dedup key)
    email TEXT NOT NULL,
    linkedin_url TEXT,

    -- ===== PERSON DATA =====
    first_name TEXT,
    last_name TEXT,
    title TEXT,
    seniority TEXT,                     -- c_suite, vp, director, manager, senior, entry
    linkedin_headline TEXT,             -- Rich personalisation signal
    photo_url TEXT,
    twitter_url TEXT,
    phone TEXT,
    personal_email TEXT,

    -- Person Location
    city TEXT,
    state TEXT,
    country TEXT,
    timezone TEXT,                      -- Calculated from location

    -- Departments
    departments TEXT[],                 -- Marketing, Sales, Engineering, etc.

    -- Employment History (full context)
    employment_history JSONB,           -- [{company, title, start_date, end_date, is_current}]
    current_role_start_date DATE,       -- Extracted for easy querying

    -- ===== ORGANISATION DATA =====
    company_name TEXT,
    company_domain TEXT,
    company_website TEXT,
    company_linkedin_url TEXT,
    company_description TEXT,           -- Apollo's short_description
    company_logo_url TEXT,

    -- Company Firmographics
    company_industry TEXT,
    company_sub_industry TEXT,
    company_employee_count INTEGER,
    company_revenue BIGINT,
    company_revenue_range TEXT,
    company_founded_year INTEGER,
    company_country TEXT,
    company_city TEXT,
    company_state TEXT,
    company_postal_code TEXT,

    -- Company Signals
    company_is_hiring BOOLEAN,
    company_latest_funding_stage TEXT,
    company_latest_funding_date DATE,
    company_total_funding BIGINT,
    company_technologies TEXT[],        -- Tech stack
    company_keywords TEXT[],            -- Business keywords

    -- ===== ENRICHMENT METADATA =====
    email_status email_status_type DEFAULT 'unknown',
    enrichment_source TEXT,             -- apollo, clay, apify
    enrichment_confidence FLOAT,
    enriched_at TIMESTAMPTZ,
    last_enriched_at TIMESTAMPTZ,
    enrichment_data JSONB,              -- Raw enrichment response for reference

    -- DataForSEO Metrics
    dataforseo_domain_rank INTEGER,
    dataforseo_organic_traffic INTEGER,
    dataforseo_backlinks INTEGER,
    dataforseo_spam_score FLOAT,
    dataforseo_enriched_at TIMESTAMPTZ,

    -- ===== POOL STATUS =====
    pool_status pool_status DEFAULT 'available',

    -- Global flags (applies across all clients)
    is_bounced BOOLEAN DEFAULT FALSE,
    bounced_at TIMESTAMPTZ,
    bounce_reason TEXT,
    is_unsubscribed BOOLEAN DEFAULT FALSE,
    unsubscribed_at TIMESTAMPTZ,
    unsubscribe_reason TEXT,

    -- Compliance
    dncr_checked BOOLEAN DEFAULT FALSE,
    dncr_result BOOLEAN,
    dncr_checked_at TIMESTAMPTZ,

    -- ===== TIMESTAMPS =====
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- ===== CONSTRAINTS =====
    CONSTRAINT unique_email_in_pool UNIQUE (email)
);

-- Trigger for updated_at
CREATE TRIGGER lead_pool_updated_at
    BEFORE UPDATE ON lead_pool
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ============================================
-- LEAD POOL INDEXES
-- ============================================

-- Primary lookups
CREATE INDEX idx_pool_apollo_id ON lead_pool(apollo_id) WHERE apollo_id IS NOT NULL;
CREATE INDEX idx_pool_email ON lead_pool(email);
CREATE INDEX idx_pool_linkedin ON lead_pool(linkedin_url) WHERE linkedin_url IS NOT NULL;

-- Domain/Company lookups
CREATE INDEX idx_pool_domain ON lead_pool(company_domain) WHERE company_domain IS NOT NULL;
CREATE INDEX idx_pool_company ON lead_pool(company_name) WHERE company_name IS NOT NULL;

-- Pool status filtering
CREATE INDEX idx_pool_status ON lead_pool(pool_status);
CREATE INDEX idx_pool_available ON lead_pool(pool_status) WHERE pool_status = 'available';

-- ICP matching queries
CREATE INDEX idx_pool_industry ON lead_pool(company_industry) WHERE company_industry IS NOT NULL;
CREATE INDEX idx_pool_country ON lead_pool(company_country) WHERE company_country IS NOT NULL;
CREATE INDEX idx_pool_employee_count ON lead_pool(company_employee_count) WHERE company_employee_count IS NOT NULL;
CREATE INDEX idx_pool_seniority ON lead_pool(seniority) WHERE seniority IS NOT NULL;

-- Email quality filtering
CREATE INDEX idx_pool_email_status ON lead_pool(email_status);
CREATE INDEX idx_pool_verified ON lead_pool(email_status) WHERE email_status = 'verified';

-- Tech stack search (GIN for array)
CREATE INDEX idx_pool_technologies ON lead_pool USING GIN(company_technologies)
    WHERE company_technologies IS NOT NULL AND array_length(company_technologies, 1) > 0;

-- Enrichment tracking
CREATE INDEX idx_pool_enriched_at ON lead_pool(enriched_at DESC NULLS LAST);
CREATE INDEX idx_pool_not_enriched ON lead_pool(created_at) WHERE enriched_at IS NULL;

-- ============================================
-- LEAD ASSIGNMENTS: Client ownership tracking
-- ============================================

CREATE TABLE lead_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Links
    lead_pool_id UUID NOT NULL REFERENCES lead_pool(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,

    -- Assignment Details
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    assigned_by TEXT DEFAULT 'allocator',  -- allocator, manual, import, migration
    assignment_reason TEXT,                 -- Why this lead was assigned

    -- Status
    status assignment_status DEFAULT 'active',
    released_at TIMESTAMPTZ,
    release_reason TEXT,                    -- client_cancelled, lead_request, manual, reallocation

    -- Outcome Tracking
    converted_at TIMESTAMPTZ,
    conversion_type TEXT,                   -- meeting_booked, deal_closed, replied_interested

    -- Contact History Summary (denormalised for performance)
    first_contacted_at TIMESTAMPTZ,
    last_contacted_at TIMESTAMPTZ,
    total_touches INTEGER DEFAULT 0,
    channels_used channel_type[] DEFAULT '{}',

    -- Response Tracking
    has_replied BOOLEAN DEFAULT FALSE,
    replied_at TIMESTAMPTZ,
    reply_intent TEXT,                      -- interested, not_interested, out_of_office, etc.

    -- Email engagement (denormalised)
    emails_sent INTEGER DEFAULT 0,
    emails_opened INTEGER DEFAULT 0,
    emails_clicked INTEGER DEFAULT 0,

    -- Assignment constraints
    max_touches INTEGER DEFAULT 10,         -- Maximum allowed touches
    cooling_until TIMESTAMPTZ,              -- If set, no outreach until this time

    -- ===== TIMESTAMPS =====
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- CRITICAL: One lead can only be assigned to one client at a time
    CONSTRAINT unique_active_assignment UNIQUE (lead_pool_id)
);

-- Trigger for updated_at
CREATE TRIGGER lead_assignments_updated_at
    BEFORE UPDATE ON lead_assignments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ============================================
-- LEAD ASSIGNMENTS INDEXES
-- ============================================

-- Primary lookups
CREATE INDEX idx_assignments_client ON lead_assignments(client_id);
CREATE INDEX idx_assignments_lead ON lead_assignments(lead_pool_id);
CREATE INDEX idx_assignments_campaign ON lead_assignments(campaign_id) WHERE campaign_id IS NOT NULL;

-- Status filtering
CREATE INDEX idx_assignments_status ON lead_assignments(status);
CREATE INDEX idx_assignments_active ON lead_assignments(client_id, status) WHERE status = 'active';

-- Outreach scheduling
CREATE INDEX idx_assignments_last_contact ON lead_assignments(last_contacted_at DESC NULLS LAST);
CREATE INDEX idx_assignments_cooling ON lead_assignments(cooling_until) WHERE cooling_until IS NOT NULL;

-- Performance queries
CREATE INDEX idx_assignments_converted ON lead_assignments(client_id, converted_at)
    WHERE status = 'converted';
CREATE INDEX idx_assignments_replied ON lead_assignments(client_id, replied_at)
    WHERE has_replied = TRUE;

-- ============================================
-- UPDATE EXISTING LEADS TABLE
-- ============================================

-- Add pool references to existing leads table
ALTER TABLE leads ADD COLUMN IF NOT EXISTS lead_pool_id UUID REFERENCES lead_pool(id);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS assignment_id UUID REFERENCES lead_assignments(id);

-- Index for pool lookups
CREATE INDEX IF NOT EXISTS idx_leads_pool ON leads(lead_pool_id) WHERE lead_pool_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_leads_assignment ON leads(assignment_id) WHERE assignment_id IS NOT NULL;

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Check if a lead is available for assignment
CREATE OR REPLACE FUNCTION is_lead_available(p_lead_pool_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    v_pool_status pool_status;
    v_has_assignment BOOLEAN;
BEGIN
    -- Get pool status
    SELECT pool_status INTO v_pool_status
    FROM lead_pool
    WHERE id = p_lead_pool_id;

    -- Must be in available status
    IF v_pool_status != 'available' THEN
        RETURN FALSE;
    END IF;

    -- Check for existing active assignment
    SELECT EXISTS (
        SELECT 1 FROM lead_assignments
        WHERE lead_pool_id = p_lead_pool_id
        AND status = 'active'
    ) INTO v_has_assignment;

    RETURN NOT v_has_assignment;
END;
$$ LANGUAGE plpgsql STABLE;

-- Assign a lead to a client (atomic operation)
CREATE OR REPLACE FUNCTION assign_lead_to_client(
    p_lead_pool_id UUID,
    p_client_id UUID,
    p_campaign_id UUID DEFAULT NULL,
    p_assigned_by TEXT DEFAULT 'allocator',
    p_reason TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_assignment_id UUID;
BEGIN
    -- Check if lead is available
    IF NOT is_lead_available(p_lead_pool_id) THEN
        RAISE EXCEPTION 'Lead % is not available for assignment', p_lead_pool_id;
    END IF;

    -- Create assignment
    INSERT INTO lead_assignments (
        lead_pool_id,
        client_id,
        campaign_id,
        assigned_by,
        assignment_reason
    ) VALUES (
        p_lead_pool_id,
        p_client_id,
        p_campaign_id,
        p_assigned_by,
        p_reason
    )
    RETURNING id INTO v_assignment_id;

    -- Update pool status
    UPDATE lead_pool
    SET pool_status = 'assigned',
        updated_at = NOW()
    WHERE id = p_lead_pool_id;

    RETURN v_assignment_id;
END;
$$ LANGUAGE plpgsql;

-- Release a lead back to pool
CREATE OR REPLACE FUNCTION release_lead(
    p_assignment_id UUID,
    p_reason TEXT DEFAULT 'manual'
)
RETURNS BOOLEAN AS $$
DECLARE
    v_lead_pool_id UUID;
BEGIN
    -- Get lead_pool_id and update assignment
    UPDATE lead_assignments
    SET status = 'released',
        released_at = NOW(),
        release_reason = p_reason,
        updated_at = NOW()
    WHERE id = p_assignment_id
    AND status = 'active'
    RETURNING lead_pool_id INTO v_lead_pool_id;

    IF v_lead_pool_id IS NULL THEN
        RETURN FALSE;
    END IF;

    -- Update pool status
    UPDATE lead_pool
    SET pool_status = 'available',
        updated_at = NOW()
    WHERE id = v_lead_pool_id;

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Get assignment for a lead (active only)
CREATE OR REPLACE FUNCTION get_lead_assignment(p_lead_pool_id UUID)
RETURNS TABLE (
    assignment_id UUID,
    client_id UUID,
    assigned_at TIMESTAMPTZ,
    total_touches INTEGER,
    has_replied BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        la.id,
        la.client_id,
        la.assigned_at,
        la.total_touches,
        la.has_replied
    FROM lead_assignments la
    WHERE la.lead_pool_id = p_lead_pool_id
    AND la.status = 'active';
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================
-- JIT VALIDATION FUNCTION
-- ============================================

CREATE OR REPLACE FUNCTION jit_validate_lead(
    p_lead_pool_id UUID,
    p_client_id UUID,
    p_channel channel_type
)
RETURNS TABLE (
    is_valid BOOLEAN,
    block_reason TEXT,
    block_code TEXT
) AS $$
DECLARE
    v_pool_lead lead_pool%ROWTYPE;
    v_assignment lead_assignments%ROWTYPE;
BEGIN
    -- Get pool lead
    SELECT * INTO v_pool_lead
    FROM lead_pool
    WHERE id = p_lead_pool_id;

    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, 'Lead not found in pool', 'lead_not_found';
        RETURN;
    END IF;

    -- Pool-level checks
    IF v_pool_lead.is_bounced THEN
        RETURN QUERY SELECT FALSE, 'Email has bounced globally', 'bounced_globally';
        RETURN;
    END IF;

    IF v_pool_lead.is_unsubscribed THEN
        RETURN QUERY SELECT FALSE, 'Lead requested no contact', 'unsubscribed_globally';
        RETURN;
    END IF;

    IF v_pool_lead.email_status = 'invalid' THEN
        RETURN QUERY SELECT FALSE, 'Email marked as invalid', 'invalid_email';
        RETURN;
    END IF;

    IF p_channel = 'email' AND v_pool_lead.email_status = 'guessed' THEN
        RETURN QUERY SELECT FALSE, 'Email not verified - high bounce risk', 'unverified_email';
        RETURN;
    END IF;

    -- Get assignment
    SELECT * INTO v_assignment
    FROM lead_assignments
    WHERE lead_pool_id = p_lead_pool_id
    AND client_id = p_client_id
    AND status = 'active';

    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, 'Lead not assigned to this client', 'not_assigned';
        RETURN;
    END IF;

    -- Assignment-level checks
    IF v_assignment.status != 'active' THEN
        RETURN QUERY SELECT FALSE, 'Assignment is not active', 'assignment_inactive';
        RETURN;
    END IF;

    IF v_assignment.total_touches >= v_assignment.max_touches THEN
        RETURN QUERY SELECT FALSE, 'Maximum touches reached', 'max_touches_reached';
        RETURN;
    END IF;

    IF v_assignment.cooling_until IS NOT NULL AND v_assignment.cooling_until > NOW() THEN
        RETURN QUERY SELECT FALSE, 'Lead is in cooling period', 'cooling_period';
        RETURN;
    END IF;

    -- All checks passed
    RETURN QUERY SELECT TRUE, NULL::TEXT, NULL::TEXT;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================
-- POOL STATISTICS VIEW
-- ============================================

CREATE OR REPLACE VIEW v_lead_pool_stats AS
SELECT
    COUNT(*) AS total_leads,
    COUNT(*) FILTER (WHERE pool_status = 'available') AS available_leads,
    COUNT(*) FILTER (WHERE pool_status = 'assigned') AS assigned_leads,
    COUNT(*) FILTER (WHERE pool_status = 'converted') AS converted_leads,
    COUNT(*) FILTER (WHERE pool_status = 'bounced') AS bounced_leads,
    COUNT(*) FILTER (WHERE pool_status = 'unsubscribed') AS unsubscribed_leads,
    COUNT(*) FILTER (WHERE email_status = 'verified') AS verified_emails,
    COUNT(*) FILTER (WHERE email_status = 'guessed') AS guessed_emails,
    COUNT(*) FILTER (WHERE enriched_at IS NOT NULL) AS enriched_leads,
    COUNT(*) FILTER (WHERE enriched_at IS NULL) AS unenriched_leads,
    COUNT(DISTINCT company_industry) AS unique_industries,
    COUNT(DISTINCT company_country) AS unique_countries
FROM lead_pool;

-- ============================================
-- CLIENT ASSIGNMENT STATISTICS VIEW
-- ============================================

CREATE OR REPLACE VIEW v_client_assignment_stats AS
SELECT
    la.client_id,
    c.company_name AS client_name,
    COUNT(*) AS total_assignments,
    COUNT(*) FILTER (WHERE la.status = 'active') AS active_assignments,
    COUNT(*) FILTER (WHERE la.status = 'converted') AS converted_assignments,
    COUNT(*) FILTER (WHERE la.status = 'released') AS released_assignments,
    COUNT(*) FILTER (WHERE la.has_replied = TRUE) AS replied_leads,
    SUM(la.total_touches) AS total_touches,
    AVG(la.total_touches) AS avg_touches_per_lead,
    MIN(la.assigned_at) AS first_assignment_at,
    MAX(la.last_contacted_at) AS last_contact_at
FROM lead_assignments la
JOIN clients c ON c.id = la.client_id
GROUP BY la.client_id, c.company_name;

-- ============================================
-- ROW LEVEL SECURITY
-- ============================================

-- Lead pool is platform-owned, only platform admins can access directly
ALTER TABLE lead_pool ENABLE ROW LEVEL SECURITY;

-- Platform admins can see all pool leads
CREATE POLICY "Platform admins can view all pool leads"
    ON lead_pool FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id = auth.uid()
            AND users.is_platform_admin = TRUE
        )
    );

-- Platform admins can modify pool leads
CREATE POLICY "Platform admins can modify pool leads"
    ON lead_pool FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id = auth.uid()
            AND users.is_platform_admin = TRUE
        )
    );

-- Lead assignments are visible to assigned client
ALTER TABLE lead_assignments ENABLE ROW LEVEL SECURITY;

-- Clients can view their own assignments
CREATE POLICY "Clients can view own assignments"
    ON lead_assignments FOR SELECT
    USING (client_id IN (SELECT get_user_client_ids()));

-- Only platform admins can create/modify assignments
CREATE POLICY "Platform admins can manage assignments"
    ON lead_assignments FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id = auth.uid()
            AND users.is_platform_admin = TRUE
        )
    );

-- ============================================
-- VERIFICATION CHECKLIST
-- ============================================
-- [x] lead_pool table with all 40+ Apollo fields
-- [x] lead_assignments table with exclusive constraint
-- [x] Pool references added to existing leads table
-- [x] email_status_type enum for verification tracking
-- [x] pool_status enum for lead lifecycle
-- [x] assignment_status enum for assignment lifecycle
-- [x] is_lead_available() function
-- [x] assign_lead_to_client() function (atomic)
-- [x] release_lead() function
-- [x] get_lead_assignment() function
-- [x] jit_validate_lead() function for pre-send checks
-- [x] v_lead_pool_stats view for analytics
-- [x] v_client_assignment_stats view for client reporting
-- [x] All indexes for performance
-- [x] RLS policies for security
-- [x] updated_at triggers
