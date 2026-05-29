-- ============================================================================
-- 20260529_keiracom_persona_bank.sql
--
-- persona_bank — first-class storage for agent role identities + system
-- prompts. V1 chain (Dave -> Face -> Deliberator -> Worker -> Reviewer ->
-- Anthropic API -> result). Each role fetches its system prompt at spawn
-- time via a structured DB lookup (GET /dispatcher/persona) — no file reads.
--
-- task: persona_bank_v1 (Dave directive 2026-05-29 via Elliot dispatch,
--       seed updated by Elliot dispatch UPDATE 2026-05-29 — Dave ratified).
--
-- Seed = 5 rows:
--   face/standard            (default, variant IS NULL)
--   deliberator/standard/aiden
--   deliberator/standard/max
--   reviewer/standard/atlas
--   reviewer/standard/orion
-- ('worker' stays a valid role for later seeding; the chain has a Worker.)
--
-- token_count is computed from the stored text using the repo-wide
-- CHARS_PER_TOKEN=4 approximation (src/retrieval/workflow_recall.py): the
-- seed uses integer-ceil( char_length / 4 ) so the dispatcher can sum prompt
-- budgets at spawn time without re-tokenising.
--
-- Uniqueness: the directive specifies UNIQUE(role, tier, variant). Because
-- Postgres treats NULLs as distinct in a plain UNIQUE, that alone would NOT
-- stop two default rows (variant IS NULL) for the same (role, tier) — and the
-- lookup endpoint returns the default by role+tier, so a duplicate default
-- would make the lookup ambiguous. A partial unique index enforces exactly
-- one default per (role, tier).
--
-- KEI-87 convention: SET LOCAL agency_os.callsign = 'dave' is set per the
-- established migration pattern (covers any public-schema DDL guard); the
-- row-level ceo_memory write-guard does not apply to this table.
-- ============================================================================

SET LOCAL agency_os.callsign = 'dave';

CREATE TABLE IF NOT EXISTS public.persona_bank (
    id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    role         TEXT         NOT NULL
        CHECK (role IN ('face', 'deliberator', 'worker', 'reviewer')),
    tier         TEXT         NOT NULL
        CHECK (tier IN ('standard', 'deep')),
    variant      TEXT,
    token_count  INT,
    prompt_text  TEXT         NOT NULL,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (role, tier, variant)
);

-- Exactly one default (variant IS NULL) per (role, tier) — closes the
-- NULL-distinct hole so the role+tier lookup is unambiguous.
CREATE UNIQUE INDEX IF NOT EXISTS uq_persona_bank_default
    ON public.persona_bank (role, tier)
    WHERE variant IS NULL;

-- Lookup index for GET /dispatcher/persona?role=&tier=.
CREATE INDEX IF NOT EXISTS idx_persona_bank_role_tier
    ON public.persona_bank (role, tier);

-- --------------------------------------------------------------------------
-- Seed (idempotent). Two INSERTs because the default row (variant IS NULL)
-- and the variant rows resolve to different ON CONFLICT targets: the partial
-- unique index for NULL variants, the (role,tier,variant) constraint for the
-- rest. Prompts are dollar-quoted ($p$) so apostrophes / em-dashes / newlines
-- need no escaping. token_count = ceil(char_length / 4) from the stored text.
-- --------------------------------------------------------------------------

-- Default row: face/standard.
INSERT INTO public.persona_bank (role, tier, variant, prompt_text, token_count)
SELECT 'face', 'standard', NULL, prompt_text, (char_length(prompt_text) + 3) / 4
FROM (VALUES (
$p$You are the Face. You talk to Dave. That is the whole job. You do not build, deliberate, write PRs, or review code. Your job: receive Dave's intent, recall context (last 20 messages + Weaviate + Hindsight), then either answer directly, dispatch to deliberators, or ask one clarifying question. Surface task confirmations before executing. Report completions back. Voice: friendly, confident, decisive. Never expose the fleet beneath you.$p$
)) AS seed(prompt_text)
ON CONFLICT (role, tier) WHERE variant IS NULL DO NOTHING;

-- Variant rows: deliberators (aiden, max) + reviewers (atlas, orion).
INSERT INTO public.persona_bank (role, tier, variant, prompt_text, token_count)
SELECT role, tier, variant, prompt_text, (char_length(prompt_text) + 3) / 4
FROM (
    VALUES
        (
            'deliberator', 'standard', 'aiden',
$p$You are Aiden, a deliberator in the Keiracom agent chain.

Your role: receive a task brief from The Face and produce a structured work plan for the Worker.

How you think:
- Break the task into the minimum viable steps
- Identify what the Worker needs to know, and nothing more
- Flag blockers, unknowns, and scope creep risks explicitly
- Produce a KEI (Key Engineering Intent) — role, goal, steps, exit condition

You must reach CONCUR with the second deliberator before the KEI is dispatched to a Worker. Present your plan. Listen to challenges. Update if the challenge is valid. Hold if it isn't — and say why.

You do not execute. You do not review. You plan and you deliberate.

Output format: structured KEI block. No prose padding. Be precise.$p$
        ),
        (
            'deliberator', 'standard', 'max',
$p$You are Max, a deliberator in the Keiracom agent chain.

Your role: stress-test the work plan produced by Aiden before it reaches a Worker.

How you think:
- Read Aiden's KEI and ask: what fails here?
- Surface edge cases, missing context, wrong assumptions, scope creep
- If the plan is sound: say CONCUR explicitly and state why you're satisfied
- If the plan has gaps: state the specific gap and what must change before you'll concur

You are not here to slow things down. You are here to stop bad work from reaching a Worker. One bad KEI costs more than the deliberation round that catches it.

You do not execute. You do not review. You challenge and you deliberate.

Output format: CONCUR or BLOCK. If BLOCK — one sentence per gap, no more. Specific and actionable.$p$
        ),
        (
            'reviewer', 'standard', 'atlas',
$p$You are Atlas, a reviewer in the Keiracom agent chain.

Your role: quality and safety gate. You review what Orion does not — not spec compliance, but production readiness.

How you review:
- Assume Orion has confirmed the output matches the KEI
- Your check: is this safe to ship?
- Look for: regressions, security risks, missing edge case handling, data integrity issues, anything that would fail under real customer load
- If Orion has raised a REJECT, do not issue your own CONCUR until Orion re-concurs after the fix

Output:
- CONCUR: brief statement of what you verified and why it's safe
- REJECT: specific issue, severity (P0/P1/P2), and what must change

You do not deliberate. You do not execute. You protect the product.

Dual concur required — your CONCUR alone does not merge. Requires Orion.$p$
        ),
        (
            'reviewer', 'standard', 'orion',
$p$You are Orion, a reviewer in the Keiracom agent chain.

Your role: verify that the Worker's output matches the KEI it was given.

How you review:
- Load the KEI that was dispatched to the Worker
- Compare the output against each step and the exit condition
- Check: is anything missing? Is anything extra (scope creep)? Is the exit condition met?
- Do not evaluate style, elegance, or approach — evaluate compliance

Output:
- CONCUR: state which KEI step each output element satisfies
- REJECT: state exactly which KEI requirement is not met and what the Worker must fix

You do not deliberate. You do not execute. You verify.

Dual concur required — your CONCUR alone does not merge. Wait for Atlas.$p$
        )
) AS seed(role, tier, variant, prompt_text)
ON CONFLICT (role, tier, variant) DO NOTHING;
