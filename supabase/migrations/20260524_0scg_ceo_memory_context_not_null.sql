-- Agency_OS-0scg — ceo_memory.context NOT NULL + CHECK enum + backfill.
--
-- WHY: Viktor's write-gate inventory item 7 + Aiden+Max MAL V1 G1. Agents
-- currently write ceo_memory entries without a context tag, making them
-- unqueryable by the planned MAL V1 architecture (which routes recall by
-- context). This migration enforces context-at-write-time going forward
-- and backfills existing rows by key-prefix classification.
--
-- Dave-authorised blanket GO 2026-05-24. Sequenced BEFORE Phase 2.0
-- namespace work.
--
-- Enum: fleet | product | archive | both
--   fleet    — orchestration plumbing, fleet-wide governance, session
--              state, cost tracking, current-fleet engineering trace.
--              ceo:* is the fleet-governance namespace by convention,
--              so the catch-all ceo:* → fleet.
--   product  — Keiracom V1.0 product decisions (chat / dashboard /
--              workforce specs + deliberation outcomes).
--   archive  — Agency OS-era historical state (Siege Waterfall, BU,
--              enrichment tiers, pre-separation directives + sprints).
--   both     — explicit cross-product items (separation directive,
--              MAL infrastructure serving the product, tenant model
--              architecture, truly unclassifiable fallthrough).
--
-- Empirical distribution on dry-run 2026-05-24 (882 rows total):
--   fleet 736 (83.4%) — ceo:* governance + completion:* + heartbeat:* etc.
--   archive 125 (14.2%) — Agency OS-era one-off keys
--   product 13 (1.5%) — Keiracom-specific specs + roadmap
--   both 8 (0.9%) — separation + MAL + arch:* + ambiguous fallthrough
--
-- KEI-87 interaction: ceo_memory_write_guard trigger blocks 'ceo:*' writes
-- unless agency_os.callsign IN ('elliot','dave'). The backfill UPDATE fires
-- the trigger on the ~530 ceo:* keys. SET LOCAL agency_os.callsign = 'dave'
-- at top of this migration so the trigger allows the writes (Dave-authorised
-- migration → attribute to dave per the explicit blanket GO).
--
-- ANTI-DRIFT WARNING (Elliot + Aiden + Max concurred 2026-05-24): this
-- SET LOCAL bypass is ONLY for Dave-explicitly-authorised admin migrations.
-- Any routine code (scripts, application helpers, ad-hoc psql sessions,
-- other migrations) using SET LOCAL agency_os.callsign = 'dave' to bypass
-- KEI-87 is a governance violation — the trigger must remain a real gate,
-- not an honour system. Default privileged-callsign for routine ceo:*
-- migrations is 'elliot' (the standing privileged callsign in KEI-87);
-- 'dave' is reserved for blanket-GO admin migrations like this one.

SET LOCAL agency_os.callsign = 'dave';

-- 1. Add column (idempotent — handles partial prior applies)
ALTER TABLE public.ceo_memory ADD COLUMN IF NOT EXISTS context text;

-- 2. Backfill existing rows via key-prefix classification.
--    Order matters: specific rules (product / both / archive) come before
--    the ceo:* catch-all → fleet, so explicit product / both / archive
--    classifications are not overridden.
UPDATE public.ceo_memory
SET context = CASE
    -- PRODUCT — Keiracom V1.0 specs + deliberations + product config
    WHEN key LIKE 'ceo:deliberation:keiracom_%' THEN 'product'
    WHEN key IN (
        'strategic_doc:architecture_final',
        'strategic_doc:roadmap',
        'strategic_doc:deliberation_floor_flow_v2'
    ) THEN 'product'
    WHEN key IN (
        'ceo:product_vision',
        'ceo:pricing_config',
        'ceo:icp_market',
        'ceo:competitive_intelligence',
        'ceo:roadmap:official'
    ) THEN 'product'
    WHEN key LIKE 'ceo:roadmap_%_capabilities_%' THEN 'product'

    -- BOTH — explicit cross-product items (separation, MAL, arch)
    WHEN key LIKE 'ceo:agency_os_keiracom_%' THEN 'both'
    WHEN key LIKE 'ceo:directive_AGENCY-OS-KEIRACOM-%' THEN 'both'
    WHEN key LIKE 'ceo:memory_abstraction_layer_%' THEN 'both'
    WHEN key LIKE 'ceo:directive_KEI-MEMORY-ABSTRACTION-%' THEN 'both'
    WHEN key IN (
        'ceo:directive_10016_complete',
        'ceo:directive_10017_complete',
        'ceo:strategic:agency_os_dead'
    ) THEN 'both'
    WHEN key LIKE 'ceo:arch:%' THEN 'both'

    -- FLEET PLUMBING (must come before archive ELSE strategic_doc:team_*
    -- could match a stale rule)
    WHEN key LIKE 'heartbeat:%' THEN 'fleet'
    WHEN key LIKE 'orchestration:%' THEN 'fleet'
    WHEN key LIKE 'completion:%' THEN 'fleet'
    WHEN key LIKE 'strategic_doc:team_structure%' THEN 'fleet'
    WHEN key LIKE 'governance:%' THEN 'fleet'
    WHEN key LIKE 'memory:%' THEN 'fleet'

    -- ARCHIVE — Agency OS-era historical state (these must come BEFORE
    -- the ceo:* catch-all → fleet to correctly classify the few ceo:*
    -- Agency-OS-specific entries that exist)
    WHEN key LIKE 'directive_%' THEN 'archive'  -- numeric directive_NNN_status
    WHEN key LIKE 'business_universe%' OR key LIKE 'bu_%' THEN 'archive'
    WHEN key LIKE 'siege_waterfall%' OR key LIKE 'waterfall_%' THEN 'archive'
    WHEN key LIKE 'pipeline_%' THEN 'archive'
    WHEN key LIKE 'stage_%_status' THEN 'archive'
    WHEN key LIKE 'sprint_%_status' THEN 'archive'
    WHEN key LIKE 'layer_%' THEN 'archive'  -- layer_2_discovery, layer_3_bulk_filter
    WHEN key LIKE 'enrichment_%' OR key LIKE 'scoring_%' THEN 'archive'
    WHEN key LIKE 'discovery_%' OR key LIKE 'campaign_%' THEN 'archive'
    WHEN key LIKE 'manual_%' OR key LIKE 'v6_%' OR key LIKE 'v7_%' THEN 'archive'
    WHEN key LIKE 'session_savepoint%' THEN 'archive'
    WHEN key LIKE 'savepoint_%' OR key LIKE 'save_point_%' THEN 'archive'
    WHEN key LIKE 'session_decisions_%' THEN 'archive'
    WHEN key LIKE 'session_mar25_%' THEN 'archive'
    WHEN key LIKE 'session_handoff_%' THEN 'archive'
    WHEN key LIKE 'bug_%' OR key LIKE 'dfs_%' OR key LIKE 'leadmagic_%' THEN 'archive'
    WHEN key LIKE 'product_state_%' THEN 'archive'
    WHEN key LIKE 'build_sequence%' OR key LIKE 'build_gotchas_%' THEN 'archive'
    WHEN key LIKE 'live_test_%' THEN 'archive'
    WHEN key LIKE 'calibration_%' OR key LIKE 'dominance_%' THEN 'archive'
    WHEN key LIKE 'signal_config_%' THEN 'archive'
    WHEN key LIKE 'qualification_%' OR key LIKE 'icp_filter_%' THEN 'archive'
    WHEN key IN ('domain_blocklist', 'x_handle_validation_rules_v1', 'tier_structure') THEN 'archive'
    WHEN key LIKE 'dm_%' OR key LIKE 's5_%' THEN 'archive'
    WHEN key LIKE 'voice_psychology_%' THEN 'archive'
    WHEN key LIKE 'call_structure_%' THEN 'archive'
    WHEN key LIKE 'objection_handling_%' THEN 'archive'
    WHEN key LIKE 'research1_%' OR key = 'data_policy' THEN 'archive'
    WHEN key LIKE 'cogs_%' OR key LIKE 'cost_per_outreach_%' THEN 'archive'
    WHEN key IN (
        'dashboard_ux_confirmed',
        'existing_dashboard_pages',
        'outreach_integrations',
        'social_scraping_stack',
        'deprecated_integrations',
        'approval_flow',
        'campaign_model'
    ) THEN 'archive'
    WHEN key LIKE 'architecture_v%' OR key = 'architecture_version' THEN 'archive'
    WHEN key LIKE 'ceo_session_log_2026-03-%' THEN 'archive'
    WHEN key IN (
        'memory',
        'governance',
        'next_directive',
        'bd_status',
        'handoff_for_next_session',
        'manual_restoration'
    ) THEN 'archive'
    WHEN key IN ('ceo:demo_migration_directive', 'ceo:au_name_matching_principle') THEN 'archive'

    -- CATCH-ALL — ceo:* is the fleet-governance namespace by convention.
    -- Anything ceo:* not classified above is governance / state / directive
    -- trace / session state — all fleet.
    WHEN key LIKE 'ceo:%' THEN 'fleet'
    WHEN key LIKE 'strategic_doc:%' THEN 'fleet'  -- non-keiracom strategic docs

    -- True fallthrough — keys that match no prefix. Per dispatch, prefer
    -- 'both' over forcing a single value when content genuinely spans.
    ELSE 'both'
END
WHERE context IS NULL;

-- 3. Sanity gate: backfill must leave zero NULL rows before NOT NULL
DO $$
DECLARE
    null_remaining bigint;
BEGIN
    SELECT COUNT(*) INTO null_remaining FROM public.ceo_memory WHERE context IS NULL;
    IF null_remaining > 0 THEN
        RAISE EXCEPTION
            '0scg: backfill incomplete — % rows still have NULL context. Migration aborted before constraint apply.',
            null_remaining;
    END IF;
END;
$$;

-- 4. CHECK constraint on enum (idempotent: drop-then-add lets re-runs replace)
ALTER TABLE public.ceo_memory DROP CONSTRAINT IF EXISTS ceo_memory_context_check;
ALTER TABLE public.ceo_memory
    ADD CONSTRAINT ceo_memory_context_check
    CHECK (context IN ('fleet', 'product', 'archive', 'both'));

-- 5. NOT NULL constraint (safe because step-3 gate confirmed zero NULL)
ALTER TABLE public.ceo_memory ALTER COLUMN context SET NOT NULL;

-- 6. Helpful index for context-routed recall (MAL V1 will route by context)
CREATE INDEX IF NOT EXISTS ceo_memory_context_idx ON public.ceo_memory (context);

COMMENT ON COLUMN public.ceo_memory.context IS
    'MAL V1 recall-routing tag. Enum: fleet | product | archive | both. NOT NULL + CHECK enforced. See migration 20260524_0scg.';
