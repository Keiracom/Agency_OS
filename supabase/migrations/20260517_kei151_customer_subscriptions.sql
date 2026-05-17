-- =============================================================================
-- KEI-151 (KEI-112B) — Customer Subscriptions (Part 17.2)
-- =============================================================================
-- Stores one row per customer-subscription. Tier code drives the rate-limit
-- + cost-cap policy (loaded from src/dispatcher/tier_limits.py TIER_LIMITS,
-- shipped as KEI-172 / KEI-117C).
--
-- Status lifecycle:
--   active    → customer is paying, all tier policies apply
--   canceled  → DELETE /subscriptions/<id> sets canceled_at + status; row
--                kept for audit. New subscription gets a fresh row.
--   paused    → reserved for future Paddle pause-resume; not used in this PR.
--
-- Idempotent: CREATE TABLE IF NOT EXISTS + CREATE INDEX IF NOT EXISTS.
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.customer_subscriptions (
    id                     UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id            UUID         NOT NULL,
    -- tier code maps to src.dispatcher.tier_limits.TIER_LIMITS keys.
    -- Valid values: 'basic' | 'pro' | 'enterprise'.
    tier_code              TEXT         NOT NULL,
    -- Paddle subscription id (KEI-150 / KEI-112A integration). NULLable so
    -- a free-tier or beta subscription can exist before Paddle is wired.
    paddle_subscription_id TEXT,
    -- Subscription lifecycle status. CHECK constraint enforces the enum.
    status                 TEXT         NOT NULL DEFAULT 'active',
    created_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    canceled_at            TIMESTAMPTZ,
    CONSTRAINT customer_subscriptions_status_chk
        CHECK (status IN ('active', 'canceled', 'paused')),
    CONSTRAINT customer_subscriptions_tier_chk
        CHECK (tier_code IN ('basic', 'pro', 'enterprise'))
);

-- One ACTIVE subscription per customer (rotate-on-tier-change pattern via
-- INSERT+UPDATE). Canceled rows retained for audit history.
CREATE UNIQUE INDEX IF NOT EXISTS customer_subscriptions_active_per_customer
    ON public.customer_subscriptions (customer_id)
    WHERE status = 'active';

CREATE INDEX IF NOT EXISTS customer_subscriptions_paddle_id_idx
    ON public.customer_subscriptions (paddle_subscription_id)
    WHERE paddle_subscription_id IS NOT NULL;
