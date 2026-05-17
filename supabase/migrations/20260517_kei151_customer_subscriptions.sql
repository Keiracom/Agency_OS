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
-- DO-block wrap follows Max's KEI-45 fix pattern (CONSTANT for repeated SQL
-- literal — Sonar S1192). The literal 'active' would otherwise repeat 3×
-- (DEFAULT + CHECK + partial index WHERE), tripping S1192.
-- =============================================================================

DO $migration$
DECLARE
    status_active CONSTANT text := 'active';
BEGIN
    EXECUTE format($ddl$
        CREATE TABLE IF NOT EXISTS public.customer_subscriptions (
            id                     UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            customer_id            UUID         NOT NULL,
            tier_code              TEXT         NOT NULL,
            paddle_subscription_id TEXT,
            status                 TEXT         NOT NULL DEFAULT %1$L,
            created_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            canceled_at            TIMESTAMPTZ,
            CONSTRAINT customer_subscriptions_status_chk
                CHECK (status IN (%1$L, 'canceled', 'paused')),
            CONSTRAINT customer_subscriptions_tier_chk
                CHECK (tier_code IN ('basic', 'pro', 'enterprise'))
        );

        CREATE UNIQUE INDEX IF NOT EXISTS customer_subscriptions_active_per_customer
            ON public.customer_subscriptions (customer_id)
            WHERE status = %1$L;

        CREATE INDEX IF NOT EXISTS customer_subscriptions_paddle_id_idx
            ON public.customer_subscriptions (paddle_subscription_id)
            WHERE paddle_subscription_id IS NOT NULL;
    $ddl$, status_active);
END
$migration$;
