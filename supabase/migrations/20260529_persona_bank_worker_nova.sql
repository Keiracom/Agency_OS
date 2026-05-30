-- 20260529_persona_bank_worker_nova.sql
-- Seeds the V1 chain's Worker persona row Atlas's api_agent_cold_start.py looks
-- up via GET /dispatcher/persona?role=worker&tier=standard&variant=nova at the
-- nova_build chain step. Without it the nova hop 404s and the dress rehearsal
-- fails at step 3.
--
-- Already applied LIVE via Supabase MCP 2026-05-29 to unblock Atlas — this
-- migration is the persisted record so future deploys + branch builds match
-- the live schema. Idempotent: ON CONFLICT (role,tier,variant) DO UPDATE.

BEGIN;

INSERT INTO public.persona_bank (role, tier, variant, prompt_text, token_count)
VALUES (
  'worker', 'standard', 'nova',
  'You are Nova, the V1 chain Worker. You receive a deliberated plan from Aiden and Max and execute it. Produce a concrete deliverable — code, document, analysis, or specification — that satisfies Aiden''s acceptance criteria. Be thorough, specific, and verifiable. Your output will be reviewed by Orion (spec) and Atlas (safety) before reaching Dave.',
  104
)
ON CONFLICT (role, tier, variant) DO UPDATE
  SET prompt_text = EXCLUDED.prompt_text,
      token_count = EXCLUDED.token_count;

COMMIT;
