-- KEI-53 — Agent profiles: personalised bd ready queue with capability affinity
-- Ratified Dave 2026-05-13; claimed by Aiden ts 2026-05-14 07:00:48 UTC per
-- pull-model first-mover-wins (Max [CONCUR-on-routing:max] ts ~1778742280).
--
-- Purpose: store per-callsign capability weights + recent task tags so
-- bd ready can return personalised orderings rather than global queue.
-- Also resolves Max's PR #861 caveat by giving pre_compact_alert.py a
-- canonical SQL source for callsign → configured-model lookup (replaces
-- the interim static _CONFIGURED_MODEL_MAP).

CREATE TABLE IF NOT EXISTS public.agent_profiles (
    callsign           TEXT        PRIMARY KEY,
    configured_model   TEXT        NOT NULL,
    context_tags       TEXT[]      NOT NULL DEFAULT '{}',
    recent_kei_types   TEXT[]      NOT NULL DEFAULT '{}',
    capability_weights JSONB       NOT NULL DEFAULT '{}'::jsonb,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.agent_profiles IS
    'KEI-53 — per-callsign capability + model profile. Source of truth for '
    'bd ready --agent personalisation and for pre_compact_alert.py Configured '
    'Model lookup (replaces static map per KEI-36 follow-up caveat).';

COMMENT ON COLUMN public.agent_profiles.configured_model IS
    'Anthropic model id (claude-opus-4-7 / claude-sonnet-4-6 / etc). Read by '
    'pre_compact_alert.py to fill HEARTBEAT.md Configured Model field.';

COMMENT ON COLUMN public.agent_profiles.capability_weights IS
    'JSONB map of capability → weight (0.0-1.0). Used by bd ready scoring '
    'to re-rank unclaimed KEIs per agent. Updated by bd complete via EMA.';

-- Initial seed for 6 known callsigns (matches global CLAUDE.md agent table
-- + Dave's KEI-53 description seed; model values from KEI-36 _CONFIGURED_MODEL_MAP
-- which this row supersedes).
INSERT INTO public.agent_profiles
    (callsign, configured_model, context_tags, capability_weights)
VALUES
    ('elliot', 'claude-opus-4-7',
        ARRAY['orchestration', 'governance', 'python'],
        '{"orchestration": 0.9, "governance": 0.9, "python": 0.8, "cognee": 0.6}'::jsonb),
    ('aiden',  'claude-opus-4-7',
        ARRAY['code_review', 'refactoring', 'python', 'ci'],
        '{"code_review": 0.9, "refactoring": 0.8, "python": 0.8, "ci": 0.7}'::jsonb),
    ('max',    'claude-opus-4-7',
        ARRAY['cognee', 'memory', 'python'],
        '{"cognee": 0.9, "memory": 0.9, "python": 0.7, "systemd": 0.3}'::jsonb),
    ('atlas',  'claude-sonnet-4-6',
        ARRAY['systemd', 'infrastructure', 'python'],
        '{"systemd": 0.9, "infrastructure": 0.8, "python": 0.6, "cognee": 0.3}'::jsonb),
    ('orion',  'claude-sonnet-4-6',
        ARRAY['parallel_build', 'python', 'infrastructure'],
        '{"parallel_build": 0.8, "python": 0.7, "infrastructure": 0.7}'::jsonb),
    ('scout',  'claude-sonnet-4-6',
        ARRAY['research', 'analysis', 'documentation'],
        '{"research": 0.9, "analysis": 0.8, "documentation": 0.7}'::jsonb)
ON CONFLICT (callsign) DO UPDATE SET
    configured_model   = EXCLUDED.configured_model,
    context_tags       = EXCLUDED.context_tags,
    capability_weights = EXCLUDED.capability_weights,
    updated_at         = NOW();

-- Update trigger to keep updated_at fresh on any column change.
CREATE OR REPLACE FUNCTION public._agent_profiles_set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_agent_profiles_updated_at ON public.agent_profiles;
CREATE TRIGGER trg_agent_profiles_updated_at
    BEFORE UPDATE ON public.agent_profiles
    FOR EACH ROW EXECUTE FUNCTION public._agent_profiles_set_updated_at();
