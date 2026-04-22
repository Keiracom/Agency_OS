-- Escalation registry for clone tier system (C1 runtime gate).
-- Tracks which task classes require clone dispatch (Tier A) vs sub-agent (Tier B).
-- Unknown classes default to Tier B. First stall on a class → permanent Tier A.
CREATE TABLE IF NOT EXISTS public.tier_registry (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    task_class text NOT NULL UNIQUE,
    tier text NOT NULL DEFAULT 'B' CHECK (tier IN ('A', 'B')),
    escalated_from_stall boolean DEFAULT false,
    stall_evidence_path text,
    reviewed_by text,
    last_reviewed_at timestamptz,
    created_at timestamptz DEFAULT NOW(),
    updated_at timestamptz DEFAULT NOW()
);

-- Seed known Tier A classes from PR #374 session
INSERT INTO public.tier_registry (task_class, tier, escalated_from_stall, stall_evidence_path, reviewed_by, last_reviewed_at)
VALUES 
    ('test-pollution-hunt', 'A', true, 'PR #374 — test-4 agent stalled 40+ min', 'elliot', NOW()),
    ('on-conflict-partial-index-debugging', 'A', true, 'PR #374 — sub-agent missed partial index', 'aiden', NOW()),
    ('gov-8-data-persistence-fix', 'A', false, 'PR #374 — touches pipeline_f_master_flow + cohort_runner', 'elliot', NOW()),
    ('pipeline-resilience-fix', 'A', false, 'PR #374 — touches gemini_client + stage_10', 'elliot', NOW()),
    ('migration-authoring', 'A', false, 'Schema changes ship to prod', 'elliot', NOW())
ON CONFLICT (task_class) DO NOTHING;
