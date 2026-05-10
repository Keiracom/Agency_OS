-- Migration: 20260510_admin_tier_b_tables.sql
-- Purpose: Phase 4 admin Tier B schema prerequisites — three tables Aiden's
--          audit (#658) flagged as MISSING during the 2026-05-10 schema sweep:
--          email_suppression, system_errors, rate_limits. Pre-stages so when
--          Aiden's Tier A wiring lands, Tier B PRs are wire-only (no migration
--          coupling). All three follow the vendor_usage_log precedent (PR #649).
-- Created: 2026-05-10
-- Pre-flight verified: SELECT EXISTS check showed all 3 missing in prod.

-- ─────────────────────────────────────────────────────────────────────────────
-- Table 1: email_suppression
-- Purpose: persistent suppression list. Email never sent to addresses here.
-- Sources: bounce events, manual admin blocks, unsubscribe webhook callbacks.
-- Consumers: /admin/compliance/suppression (Aiden Phase 4 Tier B)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS email_suppression (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL,                   -- the suppressed address (lowercased at app layer)
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,  -- NULL = global suppression
    reason TEXT NOT NULL,                  -- "hard_bounce" | "soft_bounce" | "complaint" | "unsubscribe" | "manual"
    source TEXT NOT NULL DEFAULT 'manual', -- where the suppression came from
    notes TEXT,                            -- optional admin commentary
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_email_suppression_email ON email_suppression(LOWER(email)) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_email_suppression_client ON email_suppression(client_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_email_suppression_reason ON email_suppression(reason) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_email_suppression_created ON email_suppression(created_at) WHERE deleted_at IS NULL;

ALTER TABLE email_suppression ENABLE ROW LEVEL SECURITY;

CREATE POLICY email_suppression_platform_admin ON email_suppression
    FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM users u WHERE u.id = auth.uid() AND u.is_platform_admin = true));

CREATE POLICY email_suppression_client_member ON email_suppression
    FOR SELECT TO authenticated
    USING (client_id IS NULL OR EXISTS (
        SELECT 1 FROM memberships m
        WHERE m.user_id = auth.uid() AND m.client_id = email_suppression.client_id AND m.deleted_at IS NULL
    ));

COMMENT ON TABLE email_suppression IS 'Phase 4 Tier B: persistent email suppression list (bounces, complaints, unsubscribes, manual). NULL client_id = global.';
COMMENT ON COLUMN email_suppression.reason IS 'hard_bounce | soft_bounce | complaint | unsubscribe | manual';

-- ─────────────────────────────────────────────────────────────────────────────
-- Table 2: system_errors
-- Purpose: structured error log for admin visibility. Pipeline / API /
--          integration failures land here for triage. Different from
--          activity-level activities table (which tracks lead-shaped events).
-- Consumers: /admin/system/errors (Aiden Phase 4 Tier B)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS system_errors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT NOT NULL,                       -- "pipeline" | "api" | "integration:<vendor>" | "scheduled_job"
    severity TEXT NOT NULL DEFAULT 'error',     -- "warning" | "error" | "critical"
    message TEXT NOT NULL,                      -- one-line summary
    context JSONB NOT NULL DEFAULT '{}'::jsonb, -- full structured context (stack trace, args, lead_id, etc.)
    resolved_at TIMESTAMPTZ,                    -- NULL = open; admin marks resolved
    resolved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_system_errors_source ON system_errors(source) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_system_errors_severity ON system_errors(severity) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_system_errors_unresolved ON system_errors(created_at) WHERE deleted_at IS NULL AND resolved_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_system_errors_created ON system_errors(created_at) WHERE deleted_at IS NULL;

ALTER TABLE system_errors ENABLE ROW LEVEL SECURITY;

-- Platform-only table — system errors aren't client-scoped (no client RLS policy).
CREATE POLICY system_errors_platform_admin ON system_errors
    FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM users u WHERE u.id = auth.uid() AND u.is_platform_admin = true));

COMMENT ON TABLE system_errors IS 'Phase 4 Tier B: structured error log for admin triage. Platform-scope only (no client visibility).';
COMMENT ON COLUMN system_errors.source IS 'pipeline | api | integration:<vendor> | scheduled_job';
COMMENT ON COLUMN system_errors.severity IS 'warning | error | critical';

-- ─────────────────────────────────────────────────────────────────────────────
-- Table 3: rate_limits
-- Purpose: per-vendor / per-endpoint rate-limit window tracking. Lets admin
--          see headroom against vendor caps without re-querying each vendor.
-- Consumers: /admin/system/rate-limits (Aiden Phase 4 Tier B)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS rate_limits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor TEXT NOT NULL,                       -- "dataforseo" | "anthropic" | "gemini" | "leadmagic" | "contactout" | etc.
    endpoint TEXT NOT NULL,                     -- vendor-specific endpoint or quota name
    limit_value INT NOT NULL,                   -- the cap (calls/credits per window)
    period_seconds INT NOT NULL,                -- window length in seconds (3600 = hourly, 86400 = daily, 2592000 = monthly)
    current_count INT NOT NULL DEFAULT 0,       -- calls used in the current window
    window_started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_rate_limits_vendor_endpoint ON rate_limits(vendor, endpoint) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_rate_limits_vendor ON rate_limits(vendor) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_rate_limits_window_started ON rate_limits(window_started_at) WHERE deleted_at IS NULL;
-- (Window-end expression index intentionally omitted: timestamptz + interval is
--  STABLE not IMMUTABLE in some pg versions, same gotcha as DATE(timestamptz)
--  on the vendor_usage_log migration. Compute window-end at query time instead.)

ALTER TABLE rate_limits ENABLE ROW LEVEL SECURITY;

-- Platform-only table — rate limits aren't client-scoped.
CREATE POLICY rate_limits_platform_admin ON rate_limits
    FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM users u WHERE u.id = auth.uid() AND u.is_platform_admin = true));

COMMENT ON TABLE rate_limits IS 'Phase 4 Tier B: per-vendor/endpoint rate-limit tracking. Platform-scope only.';
COMMENT ON COLUMN rate_limits.period_seconds IS '3600 = hourly, 86400 = daily, 2592000 = monthly';
