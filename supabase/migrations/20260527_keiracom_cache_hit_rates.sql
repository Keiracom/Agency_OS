-- ============================================================================
-- 20260527_keiracom_cache_hit_rates.sql
--
-- Cutover Blocker 9 — Cache hit-rate observability (Agency_OS-if0r).
-- Per Cat 21 lever 15 RATIFIED-CEO LAUNCH-BLOCKER + Elliot dispatch 2026-05-27.
--
-- Anthropic prompt-cache hit rate per spawn per worker per day. Source data
-- is the Claude session JSONL files at
-- /home/elliotbot/.claude/projects/-home-elliotbot-clawd-Agency-OS-<callsign>/
-- each assistant message carries message.usage with input_tokens +
-- cache_creation_input_tokens + cache_read_input_tokens + output_tokens.
--
-- Hit-rate definition (per Anthropic's canonical framing + the 95% target):
--   hit_rate = cache_read_input_tokens / (cache_read_input_tokens + input_tokens)
-- I.e. "of the non-cache-write portion of the prompt, how much came from cache
-- vs. full re-read." Excludes creation tokens (which are the write-cost, paid
-- once per cache block). 0% = every call re-reads the full prompt; 100% =
-- every call's input came from cache.
--
-- Threshold: alert when daily per-worker hit_rate drops below 80% (gate
-- minimum; 95% is the target per the bounded-spawn baseline anchored at
-- Atlas 0.79 AUD).
--
-- Sibling tables: keiracom_tenant_metering (PR #1137) + keiracom_tenant_budgets
-- (PR #1173) + keiracom_atoms (PR #1185). Schema convention preserved.
--
-- KEI-87 bypass: SET LOCAL agency_os.callsign = 'dave' required for public-
-- schema table creation (same pattern as the prior keiracom_* migrations).
-- ============================================================================

SET LOCAL agency_os.callsign = 'dave';

-- ----------------------------------------------------------------------------
-- Primary table: per-(date, callsign) cache token aggregates
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.keiracom_cache_hit_rates_daily (
    rollup_date              DATE        NOT NULL,
    callsign                 TEXT        NOT NULL,
    spawn_count              INTEGER     NOT NULL DEFAULT 0
        CHECK (spawn_count >= 0),
    cache_read_tokens        BIGINT      NOT NULL DEFAULT 0
        CHECK (cache_read_tokens >= 0),
    cache_creation_tokens    BIGINT      NOT NULL DEFAULT 0
        CHECK (cache_creation_tokens >= 0),
    input_tokens             BIGINT      NOT NULL DEFAULT 0
        CHECK (input_tokens >= 0),
    output_tokens            BIGINT      NOT NULL DEFAULT 0
        CHECK (output_tokens >= 0),
    assistant_message_count  INTEGER     NOT NULL DEFAULT 0
        CHECK (assistant_message_count >= 0),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (rollup_date, callsign)
);

-- "All callsigns for this date" + "all dates for this callsign" — both common
-- queries from the alert script + the CEO rollup integration.
CREATE INDEX IF NOT EXISTS idx_keiracom_cache_hit_rates_callsign_date
    ON public.keiracom_cache_hit_rates_daily (callsign, rollup_date DESC);

-- Trigger: refresh updated_at on every UPDATE so re-ingest tracks last write.
CREATE OR REPLACE FUNCTION public.keiracom_cache_hit_rates_set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_keiracom_cache_hit_rates_updated_at
    ON public.keiracom_cache_hit_rates_daily;

CREATE TRIGGER trg_keiracom_cache_hit_rates_updated_at
    BEFORE UPDATE ON public.keiracom_cache_hit_rates_daily
    FOR EACH ROW
    EXECUTE FUNCTION public.keiracom_cache_hit_rates_set_updated_at();

-- ----------------------------------------------------------------------------
-- View: hit_rate computed at query time + threshold-violation flag
-- ----------------------------------------------------------------------------

CREATE OR REPLACE VIEW public.keiracom_cache_hit_rates_v1 AS
SELECT
    rollup_date,
    callsign,
    spawn_count,
    assistant_message_count,
    cache_read_tokens,
    cache_creation_tokens,
    input_tokens,
    output_tokens,
    -- Anthropic-canonical hit rate: of non-write input, how much came from cache.
    -- NULL-safe: if (cache_read + input) is 0 (no input at all), return NULL
    -- so the alert script ignores empty days rather than alerting on 0/0.
    CASE
        WHEN (cache_read_tokens + input_tokens) > 0 THEN
            ROUND(
                (cache_read_tokens::NUMERIC / (cache_read_tokens + input_tokens))
                * 100,
                2
            )
        ELSE NULL
    END AS hit_rate_percent,
    -- Alternative metric for cost-attribution reviews: cache_read as % of total
    -- input (including creation cost). Lower than canonical hit_rate because
    -- creation tokens are the first-write cost.
    CASE
        WHEN (cache_read_tokens + cache_creation_tokens + input_tokens) > 0 THEN
            ROUND(
                (cache_read_tokens::NUMERIC
                 / (cache_read_tokens + cache_creation_tokens + input_tokens))
                * 100,
                2
            )
        ELSE NULL
    END AS hit_rate_total_input_percent,
    -- Threshold-violation flag for the alert script. Strict: <80% counts as
    -- breach. NULL hit_rate (empty day) is NOT a breach.
    CASE
        WHEN (cache_read_tokens + input_tokens) > 0
             AND (cache_read_tokens::NUMERIC / (cache_read_tokens + input_tokens))
                 < 0.80 THEN TRUE
        ELSE FALSE
    END AS below_threshold_80,
    updated_at
FROM public.keiracom_cache_hit_rates_daily;

-- ----------------------------------------------------------------------------
-- Reader grant note: RLS is OFF on this table (operational telemetry, not
-- tenant data; same posture as keiracom_tenant_metering). The Python ingestor
-- writes with SECURITY DEFINER context (KEI-87 callsign='dave' bypass via the
-- service-role key). Read access via the standard public schema.
-- ----------------------------------------------------------------------------

COMMENT ON TABLE public.keiracom_cache_hit_rates_daily IS
    'Cutover Blocker 9 (Agency_OS-if0r) — per-day per-callsign Anthropic '
    'prompt-cache token aggregates. Populated by scripts/'
    'cache_hit_rate_ingest.py reading session JSONL files.';

COMMENT ON VIEW public.keiracom_cache_hit_rates_v1 IS
    'Computed hit_rate_percent + below_threshold_80 flag for the daily '
    'CEO rollup + alert script.';
