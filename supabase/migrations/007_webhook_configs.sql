-- FILE: supabase/migrations/007_webhook_configs.sql
-- PURPOSE: Client webhook endpoint configurations
-- PHASE: 1 (Foundation + DevOps)
-- TASK: DB-008
-- DEPENDENCIES: 006_permission_modes.sql
-- RULES APPLIED:
--   - Rule 1: Follow blueprint exactly
--   - Rule 14: Soft deletes only
--   - Rule 20: Webhook-first architecture

-- ============================================
-- WEBHOOK CONFIGS (Per-Client Endpoints)
-- ============================================

CREATE TABLE webhook_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,

    -- Endpoint configuration
    name TEXT NOT NULL,                   -- Human-readable name
    url TEXT NOT NULL,                    -- Webhook endpoint URL
    secret TEXT,                          -- HMAC signing secret

    -- Event subscriptions
    events webhook_event_type[] NOT NULL DEFAULT '{}',
    /*
    Available events:
    - lead.created
    - lead.enriched
    - lead.scored
    - lead.converted
    - campaign.started
    - campaign.paused
    - campaign.completed
    - reply.received
    - meeting.booked
    */

    -- Request configuration
    headers JSONB DEFAULT '{}',           -- Custom headers to include
    timeout_ms INTEGER DEFAULT 30000,     -- Request timeout (30s default)
    retry_count INTEGER DEFAULT 3,        -- Number of retries
    retry_delay_ms INTEGER DEFAULT 1000,  -- Delay between retries

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    last_triggered_at TIMESTAMPTZ,
    last_success_at TIMESTAMPTZ,
    last_failure_at TIMESTAMPTZ,
    failure_count INTEGER DEFAULT 0,
    consecutive_failures INTEGER DEFAULT 0,

    -- Auto-disable after N consecutive failures
    auto_disable_threshold INTEGER DEFAULT 10,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,              -- Soft delete

    -- Unique name per client
    CONSTRAINT unique_webhook_name UNIQUE (client_id, name)
);

-- Trigger for updated_at
CREATE TRIGGER webhook_configs_updated_at
    BEFORE UPDATE ON webhook_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Indexes
CREATE INDEX idx_webhook_configs_client ON webhook_configs(client_id)
    WHERE deleted_at IS NULL AND is_active = TRUE;
CREATE INDEX idx_webhook_configs_events ON webhook_configs USING GIN(events)
    WHERE deleted_at IS NULL AND is_active = TRUE;

-- ============================================
-- WEBHOOK DELIVERY LOG
-- ============================================

CREATE TABLE webhook_deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    webhook_config_id UUID NOT NULL REFERENCES webhook_configs(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id),

    -- Event details
    event_type webhook_event_type NOT NULL,
    payload JSONB NOT NULL,
    signature TEXT,                      -- HMAC signature sent

    -- Delivery status
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, success, failed, retrying
    attempt_count INTEGER DEFAULT 0,

    -- Response details
    response_status INTEGER,             -- HTTP status code
    response_body TEXT,                  -- Response body (truncated)
    response_time_ms INTEGER,            -- Response time
    error_message TEXT,                  -- Error if failed

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    delivered_at TIMESTAMPTZ,
    next_retry_at TIMESTAMPTZ
);

-- Indexes for delivery management
CREATE INDEX idx_webhook_deliveries_config ON webhook_deliveries(webhook_config_id, created_at DESC);
CREATE INDEX idx_webhook_deliveries_pending ON webhook_deliveries(next_retry_at)
    WHERE status IN ('pending', 'retrying');
CREATE INDEX idx_webhook_deliveries_recent ON webhook_deliveries(created_at DESC);

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Get active webhooks for an event
CREATE OR REPLACE FUNCTION get_webhooks_for_event(
    p_client_id UUID,
    p_event webhook_event_type
)
RETURNS TABLE (
    id UUID,
    url TEXT,
    secret TEXT,
    headers JSONB,
    timeout_ms INTEGER,
    retry_count INTEGER
) AS $$
    SELECT
        wc.id,
        wc.url,
        wc.secret,
        wc.headers,
        wc.timeout_ms,
        wc.retry_count
    FROM webhook_configs wc
    WHERE wc.client_id = p_client_id
    AND wc.is_active = TRUE
    AND wc.deleted_at IS NULL
    AND p_event = ANY(wc.events);
$$ LANGUAGE sql STABLE;

-- Record webhook success
CREATE OR REPLACE FUNCTION record_webhook_success(
    p_delivery_id UUID,
    p_response_status INTEGER,
    p_response_body TEXT,
    p_response_time_ms INTEGER
)
RETURNS void AS $$
DECLARE
    v_config_id UUID;
BEGIN
    -- Update delivery record
    UPDATE webhook_deliveries
    SET status = 'success',
        response_status = p_response_status,
        response_body = LEFT(p_response_body, 10000),  -- Truncate
        response_time_ms = p_response_time_ms,
        delivered_at = NOW()
    WHERE id = p_delivery_id
    RETURNING webhook_config_id INTO v_config_id;

    -- Update config stats
    UPDATE webhook_configs
    SET last_triggered_at = NOW(),
        last_success_at = NOW(),
        consecutive_failures = 0
    WHERE id = v_config_id;
END;
$$ LANGUAGE plpgsql;

-- Record webhook failure
CREATE OR REPLACE FUNCTION record_webhook_failure(
    p_delivery_id UUID,
    p_response_status INTEGER,
    p_error_message TEXT,
    p_should_retry BOOLEAN DEFAULT TRUE
)
RETURNS void AS $$
DECLARE
    v_config_id UUID;
    v_retry_count INTEGER;
    v_attempt_count INTEGER;
    v_consecutive INTEGER;
    v_threshold INTEGER;
BEGIN
    -- Get delivery info
    SELECT webhook_config_id, attempt_count
    INTO v_config_id, v_attempt_count
    FROM webhook_deliveries
    WHERE id = p_delivery_id;

    -- Get config info
    SELECT retry_count, consecutive_failures, auto_disable_threshold
    INTO v_retry_count, v_consecutive, v_threshold
    FROM webhook_configs
    WHERE id = v_config_id;

    -- Update delivery record
    IF p_should_retry AND v_attempt_count < v_retry_count THEN
        UPDATE webhook_deliveries
        SET status = 'retrying',
            response_status = p_response_status,
            error_message = p_error_message,
            attempt_count = attempt_count + 1,
            next_retry_at = NOW() + (POWER(2, attempt_count) * INTERVAL '1 second')
        WHERE id = p_delivery_id;
    ELSE
        UPDATE webhook_deliveries
        SET status = 'failed',
            response_status = p_response_status,
            error_message = p_error_message,
            attempt_count = attempt_count + 1
        WHERE id = p_delivery_id;
    END IF;

    -- Update config stats
    UPDATE webhook_configs
    SET last_triggered_at = NOW(),
        last_failure_at = NOW(),
        failure_count = failure_count + 1,
        consecutive_failures = consecutive_failures + 1,
        -- Auto-disable if threshold reached
        is_active = CASE
            WHEN consecutive_failures + 1 >= auto_disable_threshold THEN FALSE
            ELSE is_active
        END
    WHERE id = v_config_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- VERIFICATION CHECKLIST
-- ============================================
-- [x] webhook_configs table for client endpoints
-- [x] Event type subscriptions
-- [x] HMAC secret for signing
-- [x] Retry configuration
-- [x] Auto-disable on consecutive failures
-- [x] webhook_deliveries for delivery log
-- [x] get_webhooks_for_event() function
-- [x] record_webhook_success() function
-- [x] record_webhook_failure() with retry logic
-- [x] Soft delete column
-- [x] Proper indexes
