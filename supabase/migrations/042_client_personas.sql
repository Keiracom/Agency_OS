-- Migration: 042_client_personas.sql
-- Purpose: Create client personas table and add branding to clients
-- Spec: docs/architecture/distribution/EMAIL_DISTRIBUTION.md (ED-008, ED-009)
-- Date: 2026-01-20

-- ============================================
-- CLIENTS.BRANDING FIELD (ED-009)
-- ============================================

-- Add branding JSONB field to clients table for signature data
DO $$ BEGIN
    ALTER TABLE clients
    ADD COLUMN branding JSONB DEFAULT '{}';
EXCEPTION
    WHEN duplicate_column THEN null;
END $$;

-- Branding schema:
-- {
--   "company_name": "Sparro Digital",
--   "company_tagline": "Growth marketing for B2B",
--   "logo_url": "https://...",
--   "website_url": "https://sparro.com.au",
--   "primary_color": "#FF5733",
--   "phone": "+61 2 1234 5678",
--   "address": "123 George St, Sydney NSW 2000",
--   "linkedin_url": "https://linkedin.com/company/sparro",
--   "calendar_link": "https://calendly.com/sparro/meeting",
--   "signature_template": "default"  -- or "minimal", "professional"
-- }

COMMENT ON COLUMN clients.branding IS 'Client branding data for email signatures and personalization';

-- ============================================
-- CLIENT_PERSONAS TABLE (ED-008)
-- ============================================

CREATE TABLE IF NOT EXISTS client_personas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,

    -- Persona identity
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    title VARCHAR(255),                        -- "Growth Consultant", "Account Executive"
    email VARCHAR(255),                        -- If persona has dedicated email
    phone VARCHAR(50),                         -- Direct line

    -- Display settings
    display_name VARCHAR(255),                 -- Override: "John from Sparro" format
    photo_url TEXT,                            -- Avatar for LinkedIn, email signatures
    calendar_link TEXT,                        -- Personal calendar link

    -- Channel assignments (which resources use this persona)
    -- Stored as arrays of resource IDs for flexibility
    assigned_mailbox_ids UUID[] DEFAULT '{}',  -- Email mailboxes using this persona
    assigned_phone_ids UUID[] DEFAULT '{}',    -- Phone numbers using this persona
    assigned_linkedin_seat_ids UUID[] DEFAULT '{}',  -- LinkedIn seats using this persona

    -- Status
    is_active BOOLEAN DEFAULT true,
    is_default BOOLEAN DEFAULT false,          -- Default persona for this client

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
    -- Note: No table constraint for unique default - using partial index instead
);

-- Partial unique index ensures only one default persona per client
-- (Regular unique constraint on boolean doesn't work as intended)
DROP INDEX IF EXISTS idx_client_personas_default;
CREATE UNIQUE INDEX idx_client_personas_default
    ON client_personas(client_id)
    WHERE is_default = true;

-- Other indexes
CREATE INDEX IF NOT EXISTS idx_client_personas_client
    ON client_personas(client_id);

CREATE INDEX IF NOT EXISTS idx_client_personas_active
    ON client_personas(client_id)
    WHERE is_active = true;

-- ============================================
-- PERSONA ALLOCATION (Per Tier)
-- ============================================
-- Per EMAIL_DISTRIBUTION.md:
--
-- | Tier       | Personas | Mailboxes per Persona |
-- |------------|----------|----------------------|
-- | Ignition   | 2        | 3 each (6 total)     |
-- | Velocity   | 3        | 3-4 each (10 total)  |
-- | Dominance  | 4        | 4-5 each (18 total)  |
--
-- Each persona represents a "sender identity" that the AI uses:
-- - John Smith, Growth Consultant at Sparro
-- - Sarah Chen, Account Executive at Sparro

-- ============================================
-- DISPLAY NAME GENERATION (ED-011)
-- ============================================

-- Function to generate display name if not explicitly set
CREATE OR REPLACE FUNCTION generate_persona_display_name()
RETURNS TRIGGER AS $$
BEGIN
    -- Only generate if display_name is NULL or empty
    IF NEW.display_name IS NULL OR NEW.display_name = '' THEN
        -- Get client company name
        SELECT
            COALESCE(
                c.branding->>'company_name',
                c.name
            ) INTO NEW.display_name
        FROM clients c
        WHERE c.id = NEW.client_id;

        -- Format as "First from Company"
        NEW.display_name := NEW.first_name || ' from ' || COALESCE(NEW.display_name, 'our team');
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_generate_display_name ON client_personas;
CREATE TRIGGER trigger_generate_display_name
    BEFORE INSERT OR UPDATE ON client_personas
    FOR EACH ROW
    EXECUTE FUNCTION generate_persona_display_name();

-- ============================================
-- UPDATED_AT TRIGGER
-- ============================================

DROP TRIGGER IF EXISTS update_client_personas_updated_at ON client_personas;
CREATE TRIGGER update_client_personas_updated_at
    BEFORE UPDATE ON client_personas
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- RLS POLICIES
-- ============================================

ALTER TABLE client_personas ENABLE ROW LEVEL SECURITY;

-- Clients can view and manage their own personas (owner/admin roles)
CREATE POLICY client_personas_client_all ON client_personas
    FOR ALL
    TO authenticated
    USING (
        client_id IN (
            SELECT m.client_id FROM memberships m
            WHERE m.user_id = auth.uid()
            AND m.role IN ('owner', 'admin')
        )
    );

-- Platform admins can do all operations (SELECT, INSERT, UPDATE, DELETE)
CREATE POLICY client_personas_admin_all ON client_personas
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM users u
            WHERE u.id = auth.uid()
            AND u.is_platform_admin = true
        )
    );

-- ============================================
-- HELPER FUNCTION: Get Active Personas
-- ============================================

CREATE OR REPLACE FUNCTION get_client_personas(
    p_client_id UUID
)
RETURNS TABLE (
    id UUID,
    first_name VARCHAR,
    last_name VARCHAR,
    title VARCHAR,
    display_name VARCHAR,
    email VARCHAR,
    is_default BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        cp.id,
        cp.first_name,
        cp.last_name,
        cp.title,
        cp.display_name,
        cp.email,
        cp.is_default
    FROM client_personas cp
    WHERE cp.client_id = p_client_id
      AND cp.is_active = true
    ORDER BY cp.is_default DESC, cp.created_at ASC;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- HELPER FUNCTION: Get Default Persona
-- ============================================

CREATE OR REPLACE FUNCTION get_default_persona(
    p_client_id UUID
)
RETURNS TABLE (
    id UUID,
    first_name VARCHAR,
    last_name VARCHAR,
    title VARCHAR,
    display_name VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        cp.id,
        cp.first_name,
        cp.last_name,
        cp.title,
        cp.display_name
    FROM client_personas cp
    WHERE cp.client_id = p_client_id
      AND cp.is_active = true
      AND cp.is_default = true
    LIMIT 1;

    -- If no default, return first active persona
    IF NOT FOUND THEN
        RETURN QUERY
        SELECT
            cp.id,
            cp.first_name,
            cp.last_name,
            cp.title,
            cp.display_name
        FROM client_personas cp
        WHERE cp.client_id = p_client_id
          AND cp.is_active = true
        ORDER BY cp.created_at ASC
        LIMIT 1;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- VERIFICATION
-- ============================================
-- Run these queries to verify migration:
--
-- SELECT column_name, data_type FROM information_schema.columns
-- WHERE table_name = 'clients' AND column_name = 'branding';
--
-- SELECT * FROM client_personas LIMIT 5;
--
-- SELECT * FROM get_client_personas('client-uuid-here');
