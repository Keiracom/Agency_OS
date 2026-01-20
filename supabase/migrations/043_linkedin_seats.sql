-- Migration: 043_linkedin_seats.sql
-- Purpose: Create linkedin_seats and linkedin_connections tables
-- Spec: docs/architecture/distribution/LINKEDIN_DISTRIBUTION.md
-- Date: 2026-01-20

-- ============================================
-- LINKEDIN_SEATS TABLE
-- ============================================
-- Multi-seat support per client (4/7/14 per tier)
-- White-label auth flow - no third-party branding visible

CREATE TABLE IF NOT EXISTS linkedin_seats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,

    -- Link to resource pool (optional - for platform-managed seats)
    resource_id UUID REFERENCES client_resources(id),

    -- Provider connection (internal, not exposed to client)
    unipile_account_id VARCHAR(255),

    -- Account info (from provider, displayed to client)
    account_email VARCHAR(255),
    account_name VARCHAR(255),
    profile_url TEXT,

    -- Persona mapping
    persona_id UUID REFERENCES client_personas(id),

    -- Status
    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    -- pending: awaiting client connection
    -- awaiting_2fa: 2FA code needed
    -- warmup: in 2-week ramp
    -- active: full capacity
    -- restricted: LinkedIn flagged
    -- disconnected: client removed

    -- Connection flow (for 2FA handling)
    pending_connection_id VARCHAR(255),

    -- Warmup tracking
    activated_at TIMESTAMPTZ,
    warmup_completed_at TIMESTAMPTZ,

    -- Capacity override (health-based reduction)
    daily_limit_override INTEGER,

    -- Health metrics
    accept_rate_7d DECIMAL(5,4),
    accept_rate_30d DECIMAL(5,4),
    pending_count INTEGER DEFAULT 0,

    -- Restriction tracking
    restricted_at TIMESTAMPTZ,
    restricted_reason TEXT,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_linkedin_seats_client
    ON linkedin_seats(client_id);

CREATE INDEX IF NOT EXISTS idx_linkedin_seats_active
    ON linkedin_seats(client_id)
    WHERE status IN ('warmup', 'active');

CREATE INDEX IF NOT EXISTS idx_linkedin_seats_persona
    ON linkedin_seats(persona_id);

CREATE INDEX IF NOT EXISTS idx_linkedin_seats_unipile
    ON linkedin_seats(unipile_account_id)
    WHERE unipile_account_id IS NOT NULL;

-- ============================================
-- LINKEDIN_CONNECTIONS TABLE
-- ============================================
-- Track connection requests: pending/accepted/ignored/declined/withdrawn

CREATE TABLE IF NOT EXISTS linkedin_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID NOT NULL REFERENCES lead_pool(id) ON DELETE CASCADE,
    seat_id UUID NOT NULL REFERENCES linkedin_seats(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES campaigns(id),

    -- Request tracking
    unipile_request_id VARCHAR(255),
    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    -- pending: request sent, awaiting response
    -- accepted: connection accepted
    -- ignored: 14 days no response
    -- declined: explicitly declined
    -- withdrawn: we withdrew stale request

    -- Note tracking
    note_included BOOLEAN DEFAULT FALSE,
    note_content TEXT,

    -- Timestamps
    requested_at TIMESTAMPTZ DEFAULT NOW(),
    profile_viewed_at TIMESTAMPTZ,
    responded_at TIMESTAMPTZ,

    -- Follow-up tracking (3-5 days after accept)
    follow_up_scheduled_for TIMESTAMPTZ,
    follow_up_sent_at TIMESTAMPTZ,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Ensure one connection per lead-seat pair
    CONSTRAINT unique_lead_seat UNIQUE (lead_id, seat_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_linkedin_conn_lead
    ON linkedin_connections(lead_id);

CREATE INDEX IF NOT EXISTS idx_linkedin_conn_seat
    ON linkedin_connections(seat_id);

CREATE INDEX IF NOT EXISTS idx_linkedin_conn_status
    ON linkedin_connections(status);

CREATE INDEX IF NOT EXISTS idx_linkedin_conn_pending
    ON linkedin_connections(seat_id, requested_at)
    WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_linkedin_conn_followup
    ON linkedin_connections(follow_up_scheduled_for)
    WHERE status = 'accepted' AND follow_up_sent_at IS NULL;

-- ============================================
-- UPDATED_AT TRIGGERS
-- ============================================

DROP TRIGGER IF EXISTS update_linkedin_seats_updated_at ON linkedin_seats;
CREATE TRIGGER update_linkedin_seats_updated_at
    BEFORE UPDATE ON linkedin_seats
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- RLS POLICIES
-- ============================================

ALTER TABLE linkedin_seats ENABLE ROW LEVEL SECURITY;
ALTER TABLE linkedin_connections ENABLE ROW LEVEL SECURITY;

-- LinkedIn Seats: Clients can manage their own seats (owner/admin)
CREATE POLICY linkedin_seats_client_all ON linkedin_seats
    FOR ALL
    TO authenticated
    USING (
        client_id IN (
            SELECT m.client_id FROM memberships m
            WHERE m.user_id = auth.uid()
            AND m.role IN ('owner', 'admin')
        )
    );

-- LinkedIn Seats: Platform admins full access
CREATE POLICY linkedin_seats_admin_all ON linkedin_seats
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM users u
            WHERE u.id = auth.uid()
            AND u.is_platform_admin = true
        )
    );

-- LinkedIn Connections: Clients can view their own connections
CREATE POLICY linkedin_connections_client_all ON linkedin_connections
    FOR ALL
    TO authenticated
    USING (
        seat_id IN (
            SELECT ls.id FROM linkedin_seats ls
            JOIN memberships m ON m.client_id = ls.client_id
            WHERE m.user_id = auth.uid()
            AND m.role IN ('owner', 'admin')
        )
    );

-- LinkedIn Connections: Platform admins full access
CREATE POLICY linkedin_connections_admin_all ON linkedin_connections
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
-- HELPER FUNCTIONS
-- ============================================

-- Get seat daily limit based on warmup status
CREATE OR REPLACE FUNCTION get_seat_daily_limit(p_seat_id UUID)
RETURNS INTEGER AS $$
DECLARE
    v_seat linkedin_seats%ROWTYPE;
    v_days_active INTEGER;
BEGIN
    SELECT * INTO v_seat FROM linkedin_seats WHERE id = p_seat_id;

    IF v_seat IS NULL THEN
        RETURN 0;
    END IF;

    -- Override takes precedence
    IF v_seat.daily_limit_override IS NOT NULL THEN
        RETURN v_seat.daily_limit_override;
    END IF;

    -- Restricted = 0
    IF v_seat.status = 'restricted' THEN
        RETURN 0;
    END IF;

    -- Not activated = 0
    IF v_seat.activated_at IS NULL THEN
        RETURN 0;
    END IF;

    -- Calculate days active
    v_days_active := EXTRACT(DAY FROM (NOW() - v_seat.activated_at)) + 1;

    -- Warmup schedule: 5→10→15→20
    IF v_days_active <= 3 THEN
        RETURN 5;
    ELSIF v_days_active <= 7 THEN
        RETURN 10;
    ELSIF v_days_active <= 11 THEN
        RETURN 15;
    ELSE
        RETURN 20;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Get client's active seats with capacity
CREATE OR REPLACE FUNCTION get_client_linkedin_seats(p_client_id UUID)
RETURNS TABLE (
    id UUID,
    account_name VARCHAR,
    account_email VARCHAR,
    status VARCHAR,
    daily_limit INTEGER,
    pending_count INTEGER,
    accept_rate_7d DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ls.id,
        ls.account_name,
        ls.account_email,
        ls.status,
        get_seat_daily_limit(ls.id) as daily_limit,
        ls.pending_count,
        ls.accept_rate_7d
    FROM linkedin_seats ls
    WHERE ls.client_id = p_client_id
    ORDER BY ls.status = 'active' DESC, ls.created_at ASC;
END;
$$ LANGUAGE plpgsql;

-- Get today's connection count for a seat
CREATE OR REPLACE FUNCTION get_seat_daily_connection_count(p_seat_id UUID)
RETURNS INTEGER AS $$
BEGIN
    RETURN (
        SELECT COUNT(*)
        FROM linkedin_connections
        WHERE seat_id = p_seat_id
        AND requested_at >= CURRENT_DATE
        AND requested_at < CURRENT_DATE + INTERVAL '1 day'
    );
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- SEAT ALLOCATION PER TIER (Reference)
-- ============================================
-- Per LINKEDIN_DISTRIBUTION.md:
--
-- | Tier       | LinkedIn Seats | Daily Capacity |
-- |------------|----------------|----------------|
-- | Ignition   | 4              | 80             |
-- | Velocity   | 7              | 140            |
-- | Dominance  | 14             | 280            |
--
-- Warmup schedule (2 weeks):
-- Days 1-3:  5/day
-- Days 4-7:  10/day
-- Days 8-11: 15/day
-- Days 12+:  20/day

-- ============================================
-- VERIFICATION
-- ============================================
-- Run these queries to verify migration:
--
-- SELECT * FROM linkedin_seats LIMIT 5;
-- SELECT * FROM linkedin_connections LIMIT 5;
-- SELECT get_seat_daily_limit('seat-uuid-here');
-- SELECT * FROM get_client_linkedin_seats('client-uuid-here');
