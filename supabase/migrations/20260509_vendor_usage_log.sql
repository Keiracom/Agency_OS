-- Migration: 20260509_vendor_usage_log.sql
-- Purpose: E1 R3 — per-call cost ledger for non-token vendors (DataForSEO,
--          Bright Data, Leadmagic, ContactOut, …). Parallel to sdk_usage_log,
--          which only covers token-shaped AI vendors. See spike doc:
--          docs/audits/elliot/e1_r3_vendor_cost_spike_2026-05-09.md
-- Created: 2026-05-09
-- Decision: Option B per Max group concurrence 2026-05-09

CREATE TABLE IF NOT EXISTS vendor_usage_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Context (mirrors sdk_usage_log: SYSTEM_PIPELINE_CLIENT_ID sentinel for pipeline runs)
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,

    -- Vendor identity (vendor-agnostic — new vendor is data, not migration)
    vendor TEXT NOT NULL,            -- "dataforseo" | "leadmagic" | "contactout" | "brightdata"
    endpoint TEXT NOT NULL,          -- "domain_rank_overview" | "find_email" | "phone_lookup" | "gmb_lookup"

    -- Volume (vendor-specific unit type — freetext now, can tighten to enum later)
    units INT NOT NULL DEFAULT 1,
    units_unit TEXT NOT NULL DEFAULT 'api_calls',  -- "records" | "credits" | "api_calls"

    -- Cost tracking (AUD via settings.aud_per_usd at write time, LAW II SSOT)
    cost_aud DECIMAL(10, 6) NOT NULL DEFAULT 0,

    -- Execution metrics
    duration_ms INT NOT NULL DEFAULT 0,

    -- Status
    success BOOLEAN NOT NULL DEFAULT true,
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Soft delete
    deleted_at TIMESTAMPTZ
);

-- Indexes for common queries (mirror sdk_usage_log shape)
CREATE INDEX IF NOT EXISTS idx_vendor_usage_client ON vendor_usage_log(client_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_vendor_usage_lead ON vendor_usage_log(lead_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_vendor_usage_vendor ON vendor_usage_log(vendor) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_vendor_usage_endpoint ON vendor_usage_log(vendor, endpoint) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_vendor_usage_created ON vendor_usage_log(created_at) WHERE deleted_at IS NULL;
-- (Date-bucket index intentionally omitted: DATE(timestamptz) is not IMMUTABLE,
--  so it cannot back a btree index. The created_at btree above + WHERE
--  deleted_at IS NULL suffices for daily-spend range scans, which the
--  vendor_daily_spend view uses.)

-- Daily spend tracking view (mirrors sdk_daily_spend shape)
CREATE OR REPLACE VIEW vendor_daily_spend AS
SELECT
    client_id,
    DATE(created_at) AS spend_date,
    vendor,
    endpoint,
    COUNT(*) AS call_count,
    SUM(units) AS total_units,
    SUM(cost_aud) AS total_cost_aud,
    AVG(duration_ms) AS avg_duration_ms,
    COUNT(*) FILTER (WHERE success = true) AS success_count,
    COUNT(*) FILTER (WHERE success = false) AS failure_count
FROM vendor_usage_log
WHERE deleted_at IS NULL
GROUP BY client_id, DATE(created_at), vendor, endpoint;

-- RLS (mirrors sdk_usage_log policies)
ALTER TABLE vendor_usage_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY vendor_usage_platform_admin ON vendor_usage_log
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM users u
            WHERE u.id = auth.uid()
            AND u.is_platform_admin = true
        )
    );

-- NOTE: Pre-existing migrations (018_sdk_usage_log.sql, etc.) reference a
-- table named `client_memberships` that does not exist in prod schema. The
-- canonical table is `memberships` (verified via information_schema query
-- 2026-05-09: columns user_id, client_id, deleted_at all present). This
-- migration uses the correct table name. Older policies should be patched
-- in a follow-up PR — out of scope for E1 R3.
CREATE POLICY vendor_usage_client_member ON vendor_usage_log
    FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM memberships m
            WHERE m.user_id = auth.uid()
            AND m.client_id = vendor_usage_log.client_id
            AND m.deleted_at IS NULL
        )
    );

COMMENT ON TABLE vendor_usage_log IS 'E1 R3: per-call cost ledger for non-token vendors (DFS, Leadmagic, ContactOut, Bright Data). Parallel to sdk_usage_log.';
COMMENT ON COLUMN vendor_usage_log.vendor IS 'Vendor identifier: dataforseo, leadmagic, contactout, brightdata';
COMMENT ON COLUMN vendor_usage_log.endpoint IS 'Vendor endpoint or operation name (e.g. domain_rank_overview, find_email)';
COMMENT ON COLUMN vendor_usage_log.units IS 'Volume of work charged for (records, credits, or api_calls per units_unit)';
COMMENT ON COLUMN vendor_usage_log.cost_aud IS 'Total cost in Australian dollars (USD × settings.aud_per_usd at write time)';
