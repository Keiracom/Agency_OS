-- ============================================
-- Migration: 054_personas.sql
-- Purpose: Platform personas - pre-created sender identities
-- ============================================
-- Platform personas are pre-built identities (name, title, bio, photo)
-- that can be allocated to clients and assigned to resources (mailboxes, etc.)
-- Unlike client_personas (client-provided), these are platform-owned.
-- ============================================

-- Create the personas table
CREATE TABLE personas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    title TEXT,
    company_name TEXT,
    bio TEXT,
    photo_url TEXT,
    signature_html TEXT,
    status TEXT DEFAULT 'available' CHECK (status IN ('available', 'allocated', 'retired')),
    allocated_to_client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    allocated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for finding available personas quickly
CREATE INDEX idx_personas_status ON personas(status) WHERE status = 'available';

-- Index for finding personas allocated to a specific client
CREATE INDEX idx_personas_client ON personas(allocated_to_client_id) WHERE allocated_to_client_id IS NOT NULL;

-- Add persona_id to resource_pool to link resources to platform personas
ALTER TABLE resource_pool ADD COLUMN persona_id UUID REFERENCES personas(id);
CREATE INDEX idx_resource_pool_persona ON resource_pool(persona_id);

-- Add updated_at trigger for personas
CREATE OR REPLACE FUNCTION update_personas_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER personas_updated_at
    BEFORE UPDATE ON personas
    FOR EACH ROW
    EXECUTE FUNCTION update_personas_updated_at();

-- ============================================
-- RLS Policies
-- ============================================
ALTER TABLE personas ENABLE ROW LEVEL SECURITY;

-- Service role can do everything
CREATE POLICY personas_service_all ON personas
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Authenticated users can read personas allocated to their clients
CREATE POLICY personas_read_allocated ON personas
    FOR SELECT
    TO authenticated
    USING (
        allocated_to_client_id IN (
            SELECT client_id FROM memberships
            WHERE user_id = auth.uid()
        )
    );

-- ============================================
-- Comments
-- ============================================
COMMENT ON TABLE personas IS 'Platform-owned sender identities for allocation to clients';
COMMENT ON COLUMN personas.status IS 'available = can be allocated, allocated = assigned to a client, retired = no longer usable';
COMMENT ON COLUMN personas.allocated_to_client_id IS 'Client this persona is currently allocated to';
COMMENT ON COLUMN personas.signature_html IS 'Pre-rendered HTML signature for this persona';
COMMENT ON COLUMN resource_pool.persona_id IS 'Platform persona assigned to this resource';
