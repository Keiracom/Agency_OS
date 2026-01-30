-- Migration: 054_personas.sql
-- Purpose: Platform personas for automated outreach identities
-- Date: 2026-01-30

-- ============================================
-- 1. CREATE PERSONAS TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS personas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identity
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    title TEXT,
    company_name TEXT,
    bio TEXT,
    photo_url TEXT,
    signature_html TEXT,
    
    -- Status: available, allocated, retired
    status TEXT NOT NULL DEFAULT 'available' 
        CHECK (status IN ('available', 'allocated', 'retired')),
    
    -- Allocation tracking
    allocated_to_client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    allocated_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_personas_status ON personas(status) WHERE status = 'available';
CREATE INDEX idx_personas_client ON personas(allocated_to_client_id) WHERE allocated_to_client_id IS NOT NULL;

-- ============================================
-- 2. ADD PERSONA_ID TO RESOURCE_POOL
-- ============================================

ALTER TABLE resource_pool ADD COLUMN IF NOT EXISTS persona_id UUID REFERENCES personas(id);
CREATE INDEX IF NOT EXISTS idx_resource_pool_persona ON resource_pool(persona_id);

-- ============================================
-- 3. RLS POLICIES
-- ============================================

ALTER TABLE personas ENABLE ROW LEVEL SECURITY;

-- Service role can do everything
CREATE POLICY "Service role full access on personas"
ON personas FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Users can view personas allocated to their client
CREATE POLICY "Users can view allocated personas"
ON personas FOR SELECT
TO authenticated
USING (
    allocated_to_client_id IN (
        SELECT client_id FROM memberships WHERE user_id = auth.uid()
    )
);
