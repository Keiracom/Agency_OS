-- ============================================================================
-- 20260527_keiracom_spawn_attribution.sql
--
-- Cutover Blocker 6 — per-spawn attribution telemetry.
-- bd: Agency_OS-90ho
-- Cat 21 lever 27 (Viktor / Dave directive 2026-05-27 via Elliot).
--
-- Postgres mirror of the JSONL log at
-- /home/elliotbot/clawd/logs/spawn-attribution.jsonl (see
-- src/keiracom_system/attribution/logger.py). The JSONL is the primary
-- dispatch-time write path; this table backs the operator-side
-- aggregate queries (group-by-source_type + group-by-callsign + per-
-- tenant trend) without coupling dispatch performance to Postgres
-- latency.
--
-- Backfill path (post-merge): an operator-runnable script tails the
-- JSONL into this table on a cron cadence. Same shape as the existing
-- log → metering rollup pattern from PR #1137.
--
-- Sources enumerated per dispatch:
--   - 'slack'   — Slack webhook / DM message ts
--   - 'pr'      — GitHub PR-driven dispatch (PR-NNNN)
--   - 'cron'    — systemd timer / cron job
--   - 'inbox'   — file in /tmp/telegram-relay-<callsign>/inbox/
--   - 'unknown' — fallback for un-tagged dispatches (should be rare;
--                 silent default to a real source_type is a BUG not a
--                 behaviour-preserving fallback)
--
-- KEI-87 bypass: SET LOCAL agency_os.callsign = 'dave' required for
-- public-schema table creation.
-- ============================================================================

SET LOCAL agency_os.callsign = 'dave';

CREATE TABLE IF NOT EXISTS public.keiracom_spawn_attribution (
    spawn_id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    ts                    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    source_type           TEXT         NOT NULL
        CHECK (source_type IN ('slack', 'pr', 'cron', 'inbox', 'unknown')),
    source_id             TEXT         NOT NULL,
    -- Cutover Blocker 7 / Cat 21 lever 23 LAUNCH-BLOCKER — workload-class
    -- classification for empirical pricing validation. Default 'unknown'
    -- lets dispatcher integration land in stages.
    task_type             TEXT         NOT NULL DEFAULT 'unknown'
        CHECK (task_type IN ('pr_review', 'deliberation', 'build', 'chat', 'dispatch_mgmt', 'unknown')),
    callsign              TEXT         NOT NULL,
    model                 TEXT         NOT NULL,
    input_tokens          BIGINT       NOT NULL DEFAULT 0 CHECK (input_tokens >= 0),
    output_tokens         BIGINT       NOT NULL DEFAULT 0 CHECK (output_tokens >= 0),
    cache_read_tokens     BIGINT       NOT NULL DEFAULT 0 CHECK (cache_read_tokens >= 0),
    cache_write_tokens    BIGINT       NOT NULL DEFAULT 0 CHECK (cache_write_tokens >= 0),
    cost_usd              NUMERIC(12, 6) NOT NULL DEFAULT 0 CHECK (cost_usd >= 0)
);

-- Group-by-source_type queries (which Slack messages cost most? which cron jobs?)
CREATE INDEX IF NOT EXISTS idx_keiracom_spawn_attribution_source_type_ts
    ON public.keiracom_spawn_attribution (source_type, ts DESC);

-- Group-by-task_type queries (which workload class costs most? PR_REVIEW vs BUILD?)
-- Per Cutover Blocker 7 / Cat 21 lever 23.
CREATE INDEX IF NOT EXISTS idx_keiracom_spawn_attribution_task_type_ts
    ON public.keiracom_spawn_attribution (task_type, ts DESC);

-- Group-by-callsign queries (per-agent spend breakdown).
CREATE INDEX IF NOT EXISTS idx_keiracom_spawn_attribution_callsign_ts
    ON public.keiracom_spawn_attribution (callsign, ts DESC);

-- Time-window scans for the daily rollup.
CREATE INDEX IF NOT EXISTS idx_keiracom_spawn_attribution_ts
    ON public.keiracom_spawn_attribution (ts DESC);
