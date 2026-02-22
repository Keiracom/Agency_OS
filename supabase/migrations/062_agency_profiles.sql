-- Migration: 062_agency_profiles.sql
-- SSOT Key: missing_tables (ID: 145fb2d1-636f-4275-8f83-eac2065a5e93)
-- Purpose: Agency intelligence layer - service and communication profiles
-- Populated from onboarding ICP extraction

-- ============================================================================
-- Table 1: agency_service_profile
-- Captures what the agency does, who they target, and their track record
-- ============================================================================
CREATE TABLE agency_service_profile (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    
    -- Services offered (array of service names)
    services TEXT[] DEFAULT '{}',
    
    -- Areas of expertise
    specialisations TEXT[] DEFAULT '{}',
    
    -- Industries they typically serve
    target_industries TEXT[] DEFAULT '{}',
    
    -- Deal economics
    avg_deal_size_aud DECIMAL(12, 2),
    win_rate DECIMAL(5, 4),  -- e.g., 0.3500 = 35%
    
    -- Social proof
    best_case_study TEXT,
    top_clients TEXT[] DEFAULT '{}',
    
    -- Geographic targeting
    geographic_focus TEXT[] DEFAULT '{}',  -- e.g., ['Sydney', 'Melbourne', 'AU-wide']
    
    -- Metadata
    extracted_from JSONB DEFAULT '{}',  -- Source tracking (website, crm, linkedin)
    confidence_score DECIMAL(3, 2),  -- 0.00 to 1.00
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- One profile per client
    CONSTRAINT unique_client_service_profile UNIQUE (client_id)
);

-- ============================================================================
-- Table 2: agency_communication_profile
-- Captures how the agency communicates - tone, style, patterns
-- ============================================================================
CREATE TABLE agency_communication_profile (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    
    -- Voice and tone
    tone TEXT,  -- e.g., 'professional', 'casual', 'technical', 'warm'
    
    -- Phrases they commonly use
    common_phrases TEXT[] DEFAULT '{}',
    
    -- Call-to-action preferences
    preferred_cta TEXT,  -- e.g., 'Book a call', 'Get a quote', 'Learn more'
    
    -- Performance data by communication style
    response_rate_by_style JSONB DEFAULT '{}',  -- e.g., {"formal": 0.12, "casual": 0.18}
    
    -- Channel-specific styles
    linkedin_message_style TEXT,  -- Description of their LinkedIn voice
    email_style TEXT,  -- Description of their email voice
    
    -- Metadata
    extracted_from JSONB DEFAULT '{}',
    confidence_score DECIMAL(3, 2),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- One profile per client
    CONSTRAINT unique_client_communication_profile UNIQUE (client_id)
);

-- ============================================================================
-- Indexes for performance
-- ============================================================================
CREATE INDEX idx_agency_service_profile_client ON agency_service_profile(client_id);
CREATE INDEX idx_agency_communication_profile_client ON agency_communication_profile(client_id);

-- ============================================================================
-- Triggers for updated_at
-- ============================================================================
CREATE TRIGGER update_agency_service_profile_updated_at
    BEFORE UPDATE ON agency_service_profile
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agency_communication_profile_updated_at
    BEFORE UPDATE ON agency_communication_profile
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- RLS Policies
-- ============================================================================
ALTER TABLE agency_service_profile ENABLE ROW LEVEL SECURITY;
ALTER TABLE agency_communication_profile ENABLE ROW LEVEL SECURITY;

-- Service account full access
CREATE POLICY service_role_agency_service_profile ON agency_service_profile
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY service_role_agency_communication_profile ON agency_communication_profile
    FOR ALL USING (auth.role() = 'service_role');

-- Users can view their own client's profiles
CREATE POLICY user_view_agency_service_profile ON agency_service_profile
    FOR SELECT USING (
        client_id IN (
            SELECT client_id FROM memberships 
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY user_view_agency_communication_profile ON agency_communication_profile
    FOR SELECT USING (
        client_id IN (
            SELECT client_id FROM memberships 
            WHERE user_id = auth.uid()
        )
    );

-- ============================================================================
-- Comments
-- ============================================================================
COMMENT ON TABLE agency_service_profile IS 'Agency service offering profile - populated from ICP extraction during onboarding';
COMMENT ON TABLE agency_communication_profile IS 'Agency communication style profile - populated from ICP extraction during onboarding';
