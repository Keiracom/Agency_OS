-- FILE: supabase/migrations/036_client_intelligence.sql
-- PURPOSE: Store scraped client data for SDK personalization
-- PHASE: SDK Integration
-- DEPENDENCIES: 002_clients_users_memberships.sql
-- RULES APPLIED:
--   - Rule 1: Follow blueprint exactly
--   - Rule 14: Soft deletes only (deleted_at column)

-- ============================================
-- CLIENT_INTELLIGENCE: Scraped client data
-- ============================================

CREATE TABLE IF NOT EXISTS client_intelligence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,

    -- === WEBSITE DATA ===
    website_tagline TEXT,
    website_value_prop TEXT,
    website_services JSONB DEFAULT '[]',  -- [{name, description}]
    website_case_studies JSONB DEFAULT '[]',  -- [{title, client_name, industry, result_metrics, summary}]
    website_testimonials JSONB DEFAULT '[]',  -- [{quote, author, title, company}]
    website_team_bios JSONB DEFAULT '[]',  -- [{name, title, linkedin_url, bio}]
    website_blog_topics TEXT[],  -- Recent blog post topics
    website_scraped_at TIMESTAMPTZ,

    -- === LINKEDIN COMPANY ===
    linkedin_url TEXT,
    linkedin_follower_count INTEGER,
    linkedin_employee_count INTEGER,
    linkedin_description TEXT,
    linkedin_specialties TEXT[],
    linkedin_recent_posts JSONB DEFAULT '[]',  -- [{text, date, engagement}]
    linkedin_scraped_at TIMESTAMPTZ,

    -- === TWITTER/X ===
    twitter_handle TEXT,
    twitter_follower_count INTEGER,
    twitter_bio TEXT,
    twitter_recent_posts JSONB DEFAULT '[]',  -- [{text, date, likes, retweets}]
    twitter_topics TEXT[],  -- Common topics from posts
    twitter_scraped_at TIMESTAMPTZ,

    -- === FACEBOOK ===
    facebook_url TEXT,
    facebook_follower_count INTEGER,
    facebook_about TEXT,
    facebook_recent_posts JSONB DEFAULT '[]',
    facebook_scraped_at TIMESTAMPTZ,

    -- === INSTAGRAM ===
    instagram_handle TEXT,
    instagram_follower_count INTEGER,
    instagram_bio TEXT,
    instagram_recent_posts JSONB DEFAULT '[]',  -- [{caption, date, likes}]
    instagram_scraped_at TIMESTAMPTZ,

    -- === REVIEW PLATFORMS ===
    g2_url TEXT,
    g2_rating DECIMAL(2,1),
    g2_review_count INTEGER,
    g2_top_reviews JSONB DEFAULT '[]',  -- [{rating, title, pros, cons, reviewer}]
    g2_ai_summary TEXT,  -- G2's AI-generated pros/cons
    g2_scraped_at TIMESTAMPTZ,

    capterra_url TEXT,
    capterra_rating DECIMAL(2,1),
    capterra_review_count INTEGER,
    capterra_top_reviews JSONB DEFAULT '[]',
    capterra_scraped_at TIMESTAMPTZ,

    trustpilot_url TEXT,
    trustpilot_rating DECIMAL(2,1),
    trustpilot_review_count INTEGER,
    trustpilot_top_reviews JSONB DEFAULT '[]',
    trustpilot_scraped_at TIMESTAMPTZ,

    -- === GOOGLE BUSINESS ===
    google_business_url TEXT,
    google_rating DECIMAL(2,1),
    google_review_count INTEGER,
    google_top_reviews JSONB DEFAULT '[]',
    google_scraped_at TIMESTAMPTZ,

    -- === EXTRACTED PROOF POINTS ===
    -- AI-processed summaries for SDK use
    proof_metrics JSONB DEFAULT '[]',  -- [{metric, context, source}]
    proof_clients TEXT[],  -- Named clients from case studies
    proof_industries TEXT[],  -- Industries served
    common_pain_points TEXT[],  -- Pain points our client solves
    differentiators TEXT[],  -- Key differentiators vs competitors

    -- === SCRAPING METADATA ===
    total_scrape_cost_aud DECIMAL(10,4) DEFAULT 0,
    last_full_scrape_at TIMESTAMPTZ,
    scrape_errors JSONB DEFAULT '[]',  -- [{source, error, timestamp}]

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- ============================================
-- TRIGGERS
-- ============================================

CREATE TRIGGER client_intelligence_updated_at
    BEFORE UPDATE ON client_intelligence
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ============================================
-- INDEXES
-- ============================================

-- One intelligence record per client
CREATE UNIQUE INDEX IF NOT EXISTS idx_client_intelligence_client
    ON client_intelligence(client_id) WHERE deleted_at IS NULL;

-- For finding stale data to refresh
CREATE INDEX IF NOT EXISTS idx_client_intelligence_last_scrape
    ON client_intelligence(last_full_scrape_at) WHERE deleted_at IS NULL;

-- ============================================
-- RLS POLICIES
-- ============================================

ALTER TABLE client_intelligence ENABLE ROW LEVEL SECURITY;

CREATE POLICY client_intelligence_select ON client_intelligence
    FOR SELECT USING (client_id IN (SELECT get_user_client_ids()));

CREATE POLICY client_intelligence_insert ON client_intelligence
    FOR INSERT WITH CHECK (client_id IN (SELECT get_user_client_ids()));

CREATE POLICY client_intelligence_update ON client_intelligence
    FOR UPDATE USING (client_id IN (SELECT get_user_client_ids()));

CREATE POLICY client_intelligence_delete ON client_intelligence
    FOR DELETE USING (client_id IN (SELECT get_user_client_ids()));

-- ============================================
-- HELPER FUNCTION: Get or create intelligence record
-- ============================================

CREATE OR REPLACE FUNCTION get_or_create_client_intelligence(p_client_id UUID)
RETURNS UUID AS $$
DECLARE
    v_intelligence_id UUID;
BEGIN
    -- Try to find existing record
    SELECT id INTO v_intelligence_id
    FROM client_intelligence
    WHERE client_id = p_client_id AND deleted_at IS NULL;

    -- Create if not exists
    IF v_intelligence_id IS NULL THEN
        INSERT INTO client_intelligence (client_id)
        VALUES (p_client_id)
        RETURNING id INTO v_intelligence_id;
    END IF;

    RETURN v_intelligence_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- VERIFICATION CHECKLIST
-- ============================================
-- [x] client_intelligence table with all scraped data fields
-- [x] Website data section (tagline, services, case studies, testimonials)
-- [x] Social media sections (LinkedIn, Twitter, Facebook, Instagram)
-- [x] Review platforms (G2, Capterra, Trustpilot, Google)
-- [x] Extracted proof points for SDK use
-- [x] Scraping metadata and cost tracking
-- [x] Soft delete column (deleted_at) - Rule 14
-- [x] updated_at trigger
-- [x] Unique index on client_id
-- [x] RLS policies for multi-tenant security
-- [x] Helper function for get_or_create
