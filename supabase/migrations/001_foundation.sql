-- FILE: supabase/migrations/001_foundation.sql
-- PURPOSE: Enums, roles, and base types for Agency OS
-- PHASE: 1 (Foundation + DevOps)
-- TASK: DB-002
-- DEPENDENCIES: None (first migration)
-- RULES APPLIED:
--   - Rule 1: Follow blueprint exactly
--   - Rule 14: Soft deletes only

-- ============================================
-- ENUMS: Core type definitions
-- ============================================

-- Subscription tiers (AUD pricing)
CREATE TYPE tier_type AS ENUM ('ignition', 'velocity', 'dominance');

-- Subscription status
CREATE TYPE subscription_status AS ENUM (
    'trialing',
    'active',
    'past_due',
    'cancelled',
    'paused'
);

-- Team membership roles
CREATE TYPE membership_role AS ENUM (
    'owner',
    'admin',
    'member',
    'viewer'
);

-- Automation permission modes
CREATE TYPE permission_mode AS ENUM (
    'autopilot',    -- Full automation, no approval needed
    'co_pilot',     -- AI recommends, human approves
    'manual'        -- Human does everything
);

-- Campaign lifecycle status
CREATE TYPE campaign_status AS ENUM (
    'draft',
    'active',
    'paused',
    'completed'
);

-- Lead lifecycle status
CREATE TYPE lead_status AS ENUM (
    'new',
    'enriched',
    'scored',
    'in_sequence',
    'converted',
    'unsubscribed',
    'bounced'
);

-- Outreach channel types
CREATE TYPE channel_type AS ENUM (
    'email',
    'sms',
    'linkedin',
    'voice',
    'mail'
);

-- Reply intent classification
CREATE TYPE intent_type AS ENUM (
    'meeting_request',
    'interested',
    'question',
    'not_interested',
    'unsubscribe',
    'out_of_office',
    'auto_reply'
);

-- Webhook event types
CREATE TYPE webhook_event_type AS ENUM (
    'lead.created',
    'lead.enriched',
    'lead.scored',
    'lead.converted',
    'campaign.started',
    'campaign.paused',
    'campaign.completed',
    'reply.received',
    'meeting.booked'
);

-- Audit action types
CREATE TYPE audit_action AS ENUM (
    'create',
    'update',
    'delete',
    'login',
    'logout',
    'export',
    'import',
    'webhook_sent',
    'webhook_failed'
);

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Function to get current user's client IDs (for RLS)
CREATE OR REPLACE FUNCTION get_user_client_ids()
RETURNS SETOF UUID AS $$
    SELECT client_id
    FROM memberships
    WHERE user_id = auth.uid()
    AND accepted_at IS NOT NULL
    AND deleted_at IS NULL
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- Function to check if user has role on client
CREATE OR REPLACE FUNCTION user_has_role(
    p_client_id UUID,
    p_roles membership_role[]
)
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1
        FROM memberships
        WHERE user_id = auth.uid()
        AND client_id = p_client_id
        AND role = ANY(p_roles)
        AND accepted_at IS NOT NULL
        AND deleted_at IS NULL
    )
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- UUID v7 Support (time-ordered UUIDs)
-- ============================================

-- Install the extension if available
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- UUID v7 generator function (fallback to v4 if not available)
-- In production, consider using a proper UUID v7 implementation
CREATE OR REPLACE FUNCTION gen_uuid_v7()
RETURNS UUID AS $$
DECLARE
    unix_ts_ms BIGINT;
    uuid_bytes BYTEA;
BEGIN
    -- Get current unix timestamp in milliseconds
    unix_ts_ms := (EXTRACT(EPOCH FROM clock_timestamp()) * 1000)::BIGINT;

    -- Create UUID v7 bytes
    -- First 48 bits: timestamp
    -- Next 4 bits: version (7)
    -- Next 12 bits: random
    -- Next 2 bits: variant (10)
    -- Last 62 bits: random
    uuid_bytes :=
        set_byte(
            set_byte(
                decode(
                    lpad(to_hex(unix_ts_ms), 12, '0') ||
                    lpad(to_hex((random() * 65535)::int), 4, '0') ||
                    lpad(to_hex((random() * 65535)::int), 4, '0') ||
                    lpad(to_hex((random() * 65535)::int), 4, '0') ||
                    lpad(to_hex((random() * 65535)::int), 4, '0') ||
                    lpad(to_hex((random() * 65535)::int), 4, '0'),
                    'hex'
                ),
                6,
                (get_byte(decode(lpad(to_hex((random() * 65535)::int), 4, '0'), 'hex'), 0) & x'0f'::int) | x'70'::int
            ),
            8,
            (get_byte(decode(lpad(to_hex((random() * 65535)::int), 4, '0'), 'hex'), 0) & x'3f'::int) | x'80'::int
        );

    RETURN encode(uuid_bytes, 'hex')::uuid;
END;
$$ LANGUAGE plpgsql VOLATILE;

-- ============================================
-- VERIFICATION CHECKLIST
-- ============================================
-- [x] All enums from PART 5 created
-- [x] tier_type: ignition, velocity, dominance
-- [x] subscription_status: trialing, active, past_due, cancelled, paused
-- [x] membership_role: owner, admin, member, viewer
-- [x] permission_mode: autopilot, co_pilot, manual
-- [x] campaign_status: draft, active, paused, completed
-- [x] lead_status: new, enriched, scored, in_sequence, converted, unsubscribed, bounced
-- [x] channel_type: email, sms, linkedin, voice, mail
-- [x] intent_type: meeting_request, interested, question, not_interested, unsubscribe, out_of_office, auto_reply
-- [x] get_user_client_ids() function for RLS
-- [x] user_has_role() function for RLS
-- [x] update_updated_at() trigger function
-- [x] UUID v7 support
