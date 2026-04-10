-- Migration 100: Billing lifecycle fields + webhook_events table
-- Directive #310 — Stripe consolidation + webhook handlers + activation email

-- ============================================================
-- 1. webhook_events table (idempotent Stripe event logging)
-- ============================================================

CREATE TABLE IF NOT EXISTS webhook_events (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    provider    text        NOT NULL,           -- 'stripe'
    event_type  text        NOT NULL,
    event_id    text        NOT NULL UNIQUE,    -- Stripe event ID for idempotency
    payload     jsonb       NOT NULL DEFAULT '{}'::jsonb,
    processed_at timestamptz NOT NULL DEFAULT now(),
    status      text        NOT NULL DEFAULT 'processed'  -- processed/failed/skipped/duplicate
);

CREATE INDEX IF NOT EXISTS idx_webhook_events_event_id ON webhook_events(event_id);
CREATE INDEX IF NOT EXISTS idx_webhook_events_provider ON webhook_events(provider, event_type);

COMMENT ON TABLE webhook_events IS
    'Idempotent log of processed webhook events. One row per unique event_id.';

-- ============================================================
-- 2. Client billing lifecycle columns
-- ============================================================

ALTER TABLE clients
    ADD COLUMN IF NOT EXISTS subscription_started_at  timestamptz,
    ADD COLUMN IF NOT EXISTS cancelled_at             timestamptz,
    ADD COLUMN IF NOT EXISTS last_payment_at          timestamptz,
    ADD COLUMN IF NOT EXISTS next_billing_at          timestamptz;

COMMENT ON COLUMN clients.subscription_started_at IS
    'When the first paid subscription became active (set by customer.subscription.created webhook)';
COMMENT ON COLUMN clients.cancelled_at IS
    'When the subscription was cancelled (set by customer.subscription.deleted webhook). Data retained 30 days.';
COMMENT ON COLUMN clients.last_payment_at IS
    'Timestamp of last successful invoice payment';
COMMENT ON COLUMN clients.next_billing_at IS
    'Next scheduled billing date from Stripe next_payment_attempt';
