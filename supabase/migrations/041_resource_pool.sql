-- Migration: 041_resource_pool.sql
-- Purpose: Create resource pool tables for automated resource allocation
-- Spec: docs/architecture/distribution/RESOURCE_POOL.md
-- Date: 2026-01-20

-- ============================================
-- RESOURCE TYPES ENUM
-- ============================================

DO $$ BEGIN
    CREATE TYPE resource_type AS ENUM ('email_domain', 'phone_number', 'linkedin_seat');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE resource_status AS ENUM ('available', 'assigned', 'warming', 'retired');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ============================================
-- RESOURCE_POOL TABLE (Platform-Level)
-- ============================================

CREATE TABLE IF NOT EXISTS resource_pool (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Resource identification
    resource_type resource_type NOT NULL,
    resource_value TEXT NOT NULL UNIQUE,      -- 'agencyxos-growth.com', '+61412345678', 'seat_abc123'
    resource_name TEXT,                        -- Friendly name

    -- Capacity tracking (for shared resources)
    max_clients INTEGER DEFAULT 1,             -- How many clients can share this resource
    current_clients INTEGER DEFAULT 0,         -- Currently assigned clients

    -- Status
    status resource_status DEFAULT 'available',

    -- Warmup tracking (for email domains)
    warmup_started_at TIMESTAMPTZ,
    warmup_completed_at TIMESTAMPTZ,
    reputation_score INTEGER DEFAULT 0,        -- 0-100

    -- Provider metadata
    provider TEXT,                             -- 'infraforge', 'twilio', 'unipile'
    provider_id TEXT,                          -- External ID
    provider_metadata JSONB DEFAULT '{}',      -- Additional provider-specific data

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for resource_pool
CREATE INDEX IF NOT EXISTS idx_resource_pool_type_status
    ON resource_pool(resource_type, status);

CREATE INDEX IF NOT EXISTS idx_resource_pool_available
    ON resource_pool(resource_type)
    WHERE status = 'available' AND current_clients < max_clients;

CREATE INDEX IF NOT EXISTS idx_resource_pool_provider
    ON resource_pool(provider, provider_id);

-- ============================================
-- CLIENT_RESOURCES TABLE (Client-Level)
-- ============================================

CREATE TABLE IF NOT EXISTS client_resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    resource_pool_id UUID NOT NULL REFERENCES resource_pool(id),

    -- Assignment tracking
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    released_at TIMESTAMPTZ,                   -- NULL = still assigned

    -- Usage tracking
    total_sends INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_client_resource UNIQUE (client_id, resource_pool_id)
);

-- Indexes for client_resources
CREATE INDEX IF NOT EXISTS idx_client_resources_client
    ON client_resources(client_id)
    WHERE released_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_client_resources_pool
    ON client_resources(resource_pool_id);

-- ============================================
-- CAMPAIGN_RESOURCES UPDATE
-- ============================================

-- Add column to link campaign_resources to client_resources
-- This allows campaigns to inherit resources from clients automatically
DO $$ BEGIN
    ALTER TABLE campaign_resources
    ADD COLUMN client_resource_id UUID REFERENCES client_resources(id);
EXCEPTION
    WHEN duplicate_column THEN null;
END $$;

CREATE INDEX IF NOT EXISTS idx_campaign_resources_client_resource
    ON campaign_resources(client_resource_id);

-- ============================================
-- TIER ALLOCATION REFERENCE (Comment Only)
-- ============================================
-- Per RESOURCE_POOL.md (CEO Decisions 2026-01-20):
--
-- | Tier       | Domains | Mailboxes | Phone Numbers | LinkedIn Seats |
-- |------------|---------|-----------|---------------|----------------|
-- | Ignition   | 3       | 6         | 1             | 4              |
-- | Velocity   | 5       | 10        | 2             | 7              |
-- | Dominance  | 9       | 18        | 3             | 14             |
--
-- Domain Selection Priority:
-- 1. Prefer warmed domains (warmup_completed_at IS NOT NULL)
-- 2. Prefer higher reputation (reputation_score DESC)
-- 3. Prefer less loaded (current_clients < max_clients)
-- 4. Oldest first (created_at ASC)

-- ============================================
-- SEED EXISTING DOMAINS (if available)
-- ============================================
-- Note: Actual seeding should be done via admin API or manual insert
-- This is a template for reference:
--
-- INSERT INTO resource_pool (resource_type, resource_value, status, warmup_completed_at, provider)
-- VALUES
--     ('email_domain', 'agencyxos-growth.com', 'available', NOW(), 'infraforge'),
--     ('email_domain', 'agencyxos-reach.com', 'available', NOW(), 'infraforge'),
--     ('email_domain', 'agencyxos-leads.com', 'available', NOW(), 'infraforge')
-- ON CONFLICT (resource_value) DO NOTHING;

-- ============================================
-- RLS POLICIES
-- ============================================

-- resource_pool: Platform admins only
ALTER TABLE resource_pool ENABLE ROW LEVEL SECURITY;

CREATE POLICY resource_pool_admin_all ON resource_pool
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM users u
            WHERE u.id = auth.uid()
            AND u.is_platform_admin = true
        )
    );

-- client_resources: Clients can view their own, admins can view all
ALTER TABLE client_resources ENABLE ROW LEVEL SECURITY;

CREATE POLICY client_resources_client_select ON client_resources
    FOR SELECT
    TO authenticated
    USING (
        client_id IN (
            SELECT m.client_id FROM memberships m
            WHERE m.user_id = auth.uid()
        )
        OR EXISTS (
            SELECT 1 FROM users u
            WHERE u.id = auth.uid()
            AND u.is_platform_admin = true
        )
    );

CREATE POLICY client_resources_admin_all ON client_resources
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
-- UPDATED_AT TRIGGER
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_resource_pool_updated_at ON resource_pool;
CREATE TRIGGER update_resource_pool_updated_at
    BEFORE UPDATE ON resource_pool
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_client_resources_updated_at ON client_resources;
CREATE TRIGGER update_client_resources_updated_at
    BEFORE UPDATE ON client_resources
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- HELPER FUNCTION: Get Available Resources
-- ============================================

CREATE OR REPLACE FUNCTION get_available_resources(
    p_resource_type resource_type,
    p_count INTEGER
)
RETURNS TABLE (
    id UUID,
    resource_value TEXT,
    reputation_score INTEGER,
    warmup_completed_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        rp.id,
        rp.resource_value,
        rp.reputation_score,
        rp.warmup_completed_at
    FROM resource_pool rp
    WHERE rp.resource_type = p_resource_type
      AND rp.status IN ('available', 'assigned')
      AND rp.current_clients < rp.max_clients
    ORDER BY
        (rp.warmup_completed_at IS NOT NULL) DESC,  -- Warmed first
        rp.reputation_score DESC,                    -- Higher reputation
        rp.current_clients ASC,                      -- Less loaded
        rp.created_at ASC                            -- Oldest first
    LIMIT p_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- HELPER FUNCTION: Get Pool Stats
-- ============================================

CREATE OR REPLACE FUNCTION get_pool_stats(
    p_resource_type resource_type DEFAULT NULL
)
RETURNS TABLE (
    resource_type resource_type,
    total INTEGER,
    available INTEGER,
    assigned INTEGER,
    warming INTEGER,
    retired INTEGER,
    buffer_pct NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        rp.resource_type,
        COUNT(*)::INTEGER as total,
        COUNT(*) FILTER (WHERE rp.status = 'available' AND rp.current_clients < rp.max_clients)::INTEGER as available,
        COUNT(*) FILTER (WHERE rp.status = 'assigned' OR rp.current_clients >= rp.max_clients)::INTEGER as assigned,
        COUNT(*) FILTER (WHERE rp.status = 'warming')::INTEGER as warming,
        COUNT(*) FILTER (WHERE rp.status = 'retired')::INTEGER as retired,
        CASE
            WHEN COUNT(*) FILTER (WHERE rp.status = 'assigned' OR rp.current_clients > 0) > 0
            THEN ROUND(
                COUNT(*) FILTER (WHERE rp.status = 'available' AND rp.current_clients < rp.max_clients)::NUMERIC /
                COUNT(*) FILTER (WHERE rp.status = 'assigned' OR rp.current_clients > 0)::NUMERIC * 100,
                1
            )
            ELSE 100.0
        END as buffer_pct
    FROM resource_pool rp
    WHERE p_resource_type IS NULL OR rp.resource_type = p_resource_type
    GROUP BY rp.resource_type;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- VERIFICATION
-- ============================================
-- Run these queries to verify migration:
--
-- SELECT * FROM resource_pool LIMIT 5;
-- SELECT * FROM client_resources LIMIT 5;
-- SELECT * FROM get_pool_stats();
-- SELECT * FROM get_available_resources('email_domain', 3);
