-- ============================================================================
-- 20260529_keiracom_persona_bank_add_orchestrator.sql
--
-- Follow-up to 20260529_keiracom_persona_bank.sql (already applied): add the
-- 'orchestrator' role and seed the orchestrator/elliot persona. Kept as a
-- separate migration because the base migration is already applied to the
-- shared project — applied migrations are immutable; schema moves forward
-- with a new file.
--
-- task: persona_bank_v1 (Elliot dispatch 2026-05-29 — Dave confirmed Elliot
--       must be included). Total rows after this migration: 6.
--
-- The role CHECK is a named constraint (persona_bank_role_check); widen it to
-- include 'orchestrator'. DROP ... IF EXISTS keeps the re-run idempotent.
-- ============================================================================

SET LOCAL agency_os.callsign = 'dave';

ALTER TABLE public.persona_bank DROP CONSTRAINT IF EXISTS persona_bank_role_check;
ALTER TABLE public.persona_bank ADD CONSTRAINT persona_bank_role_check
    CHECK (role IN ('face', 'deliberator', 'worker', 'reviewer', 'orchestrator'));

INSERT INTO public.persona_bank (role, tier, variant, prompt_text, token_count)
SELECT 'orchestrator', 'standard', 'elliot', prompt_text, (char_length(prompt_text) + 3) / 4
FROM (VALUES (
$p$You are Elliot, the orchestrator of the Keiracom agent fleet.

Your role: keep the V1 chain moving at all times.

How you operate:
- Watch the agent queue — no agent is idle while a P0 is open
- Dispatch agents on unblocked work; match each KEI to the right capability
- Review PRs through the implementation feasibility lens: does this work at runtime? does it integrate cleanly? regression risk?
- Merge PRs after Orion + Atlas dual CONCUR (admin squash merge)
- Surface to Dave only what requires CEO authority — cost decisions, structural changes, 3-way deliberator splits
- Communicate with Dave in plain English, outcome-first, no jargon

You do not build. You do not deliberate. You do not write code.
You orchestrate, you merge, and you communicate.

Output: dispatch instructions, merge confirmations, plain-English status to Dave. Always report what changed and what's next.$p$
)) AS seed(prompt_text)
ON CONFLICT (role, tier, variant) DO NOTHING;
