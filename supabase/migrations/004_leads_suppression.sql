-- FILE: supabase/migrations/004_leads_suppression.sql
-- PURPOSE: Leads with ALS fields and compound uniqueness, global suppression
-- PHASE: 1 (Foundation + DevOps)
-- TASK: DB-005
-- DEPENDENCIES: 003_campaigns.sql
-- RULES APPLIED:
--   - Rule 1: Follow blueprint exactly
--   - Rule 14: Soft deletes only (deleted_at column)

-- ============================================
-- LEADS
-- ============================================

CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id),
    campaign_id UUID NOT NULL REFERENCES campaigns(id),

    -- Contact information
    email TEXT NOT NULL,
    phone TEXT,
    first_name TEXT,
    last_name TEXT,
    title TEXT,
    company TEXT,
    linkedin_url TEXT,
    domain TEXT,

    -- === ALS Score Components (100 points max) ===
    -- See PART 6 for scoring formula
    als_score INTEGER,                    -- Total score (0-100)
    als_tier TEXT,                        -- Hot/Warm/Cool/Cold/Dead
    als_data_quality INTEGER,             -- Max 20 points
    als_authority INTEGER,                -- Max 25 points
    als_company_fit INTEGER,              -- Max 25 points
    als_timing INTEGER,                   -- Max 15 points
    als_risk INTEGER,                     -- Max 15 points (deductions)

    -- === Organization Data (for ALS) ===
    organization_industry TEXT,
    organization_employee_count INTEGER,
    organization_country TEXT,
    organization_founded_year INTEGER,
    organization_is_hiring BOOLEAN,
    organization_latest_funding_date DATE,
    organization_website TEXT,
    organization_linkedin_url TEXT,

    -- === Person Data (for ALS) ===
    employment_start_date DATE,           -- For "new role" timing signal
    personal_email TEXT,                  -- Additional contact
    seniority_level TEXT,                 -- C-level, VP, Director, Manager, etc.

    -- === Status & Tracking ===
    status lead_status DEFAULT 'new',
    current_sequence_step INTEGER DEFAULT 0,
    next_outreach_at TIMESTAMPTZ,

    -- === Enrichment Metadata ===
    enrichment_source TEXT,               -- apollo, clay, apify, cache
    enrichment_confidence FLOAT,          -- 0.0 to 1.0
    enrichment_version TEXT,              -- Cache version
    enriched_at TIMESTAMPTZ,

    -- === Compliance ===
    dncr_checked BOOLEAN DEFAULT FALSE,   -- Do Not Call Registry (Australia)
    dncr_result BOOLEAN,                  -- True = on DNCR list
    email_verified BOOLEAN,
    phone_verified BOOLEAN,

    -- === Engagement Tracking ===
    last_contacted_at TIMESTAMPTZ,
    last_replied_at TIMESTAMPTZ,
    last_opened_at TIMESTAMPTZ,
    last_clicked_at TIMESTAMPTZ,
    reply_count INTEGER DEFAULT 0,
    bounce_count INTEGER DEFAULT 0,

    -- === Assigned Resources ===
    assigned_email_resource TEXT,         -- Email domain/sender assigned
    assigned_linkedin_seat TEXT,          -- LinkedIn seat assigned
    assigned_phone_resource TEXT,         -- Phone number assigned

    -- === Timestamps ===
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,               -- Soft delete (Rule 14)

    -- === CRITICAL: Compound uniqueness per client ===
    -- Same email can exist for different clients
    CONSTRAINT unique_lead_per_client UNIQUE (client_id, email)
);

-- Trigger for updated_at
CREATE TRIGGER leads_updated_at
    BEFORE UPDATE ON leads
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ============================================
-- INDEXES (Performance Critical)
-- ============================================

-- Primary lookups
CREATE INDEX idx_leads_client_email ON leads(client_id, email)
    WHERE deleted_at IS NULL;
CREATE INDEX idx_leads_campaign ON leads(campaign_id)
    WHERE deleted_at IS NULL;

-- Status filtering
CREATE INDEX idx_leads_status ON leads(client_id, status)
    WHERE deleted_at IS NULL;

-- ALS score ordering (for prioritization)
CREATE INDEX idx_leads_als ON leads(client_id, als_score DESC NULLS LAST)
    WHERE deleted_at IS NULL;

-- Outreach scheduling
CREATE INDEX idx_leads_next_outreach ON leads(next_outreach_at)
    WHERE status = 'in_sequence'
    AND deleted_at IS NULL
    AND next_outreach_at IS NOT NULL;

-- Domain lookups (for enrichment)
CREATE INDEX idx_leads_domain ON leads(domain)
    WHERE domain IS NOT NULL;

-- ============================================
-- GLOBAL SUPPRESSION (Platform-Wide)
-- ============================================

CREATE TABLE global_suppression (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    reason TEXT NOT NULL,       -- unsubscribe, bounce, complaint, legal, manual
    source TEXT,                -- Which system added this
    added_by TEXT,              -- User/system identifier
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast lookups
CREATE INDEX idx_suppression_email ON global_suppression(email);

-- ============================================
-- CLIENT SUPPRESSION (Per-Client)
-- ============================================

CREATE TABLE client_suppression (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    reason TEXT NOT NULL,
    added_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Unique per client
    CONSTRAINT unique_client_suppression UNIQUE (client_id, email)
);

-- Index for lookups
CREATE INDEX idx_client_suppression ON client_suppression(client_id, email);

-- ============================================
-- DOMAIN SUPPRESSION (Competitor/Bad domains)
-- ============================================

CREATE TABLE domain_suppression (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain TEXT NOT NULL UNIQUE,
    reason TEXT NOT NULL,       -- competitor, blacklisted, spam_trap
    added_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for lookups
CREATE INDEX idx_domain_suppression ON domain_suppression(domain);

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Check if email is suppressed (global + client)
CREATE OR REPLACE FUNCTION is_email_suppressed(
    p_email TEXT,
    p_client_id UUID DEFAULT NULL
)
RETURNS BOOLEAN AS $$
BEGIN
    -- Check global suppression
    IF EXISTS (SELECT 1 FROM global_suppression WHERE email = LOWER(p_email)) THEN
        RETURN TRUE;
    END IF;

    -- Check client suppression if client_id provided
    IF p_client_id IS NOT NULL THEN
        IF EXISTS (
            SELECT 1 FROM client_suppression
            WHERE client_id = p_client_id AND email = LOWER(p_email)
        ) THEN
            RETURN TRUE;
        END IF;
    END IF;

    -- Check domain suppression
    IF EXISTS (
        SELECT 1 FROM domain_suppression
        WHERE domain = LOWER(SPLIT_PART(p_email, '@', 2))
    ) THEN
        RETURN TRUE;
    END IF;

    RETURN FALSE;
END;
$$ LANGUAGE plpgsql STABLE;

-- Get ALS tier from score
CREATE OR REPLACE FUNCTION get_als_tier(p_score INTEGER)
RETURNS TEXT AS $$
BEGIN
    IF p_score >= 85 THEN RETURN 'hot';
    ELSIF p_score >= 60 THEN RETURN 'warm';
    ELSIF p_score >= 35 THEN RETURN 'cool';
    ELSIF p_score >= 20 THEN RETURN 'cold';
    ELSE RETURN 'dead';
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================
-- VERIFICATION CHECKLIST
-- ============================================
-- [x] leads table with all ALS fields from PART 5
-- [x] Compound uniqueness: client_id + email
-- [x] Soft delete column (deleted_at)
-- [x] ALS score components (data_quality, authority, company_fit, timing, risk)
-- [x] Organization data fields
-- [x] DNCR compliance fields
-- [x] Enrichment metadata (source, confidence, version)
-- [x] global_suppression table
-- [x] client_suppression table
-- [x] domain_suppression table
-- [x] is_email_suppressed() function
-- [x] get_als_tier() function
-- [x] All performance indexes
-- [x] updated_at trigger
