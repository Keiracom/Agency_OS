-- SCHEMA-F1 Step 3: Drop 5 dead columns from agent_memories.
-- provenance: all 388 rows = {} (empty JSONB default). Zero code reads.
-- signoff_status: all 388 rows = 'approved' (default). Zero code reads.
-- category: all 388 rows = NULL. Zero code reads.
-- business_score: all 388 rows = NULL. Zero code reads.
-- learning_score: all 388 rows = NULL. Zero code reads.

ALTER TABLE public.agent_memories DROP COLUMN IF EXISTS provenance;
ALTER TABLE public.agent_memories DROP COLUMN IF EXISTS signoff_status;
ALTER TABLE public.agent_memories DROP COLUMN IF EXISTS category;
ALTER TABLE public.agent_memories DROP COLUMN IF EXISTS business_score;
ALTER TABLE public.agent_memories DROP COLUMN IF EXISTS learning_score;

-- SCHEMA-F1 Step 2: Document promoted_from_id semantics.
COMMENT ON COLUMN public.agent_memories.promoted_from_id IS 'Self-reference indicates this row was promoted in-place from tentative to confirmed. Non-self FK reserved for future audit-row pattern.';

-- SCHEMA-F1 Step 4: Defer contradicted_by_id — retain column, document intent.
COMMENT ON COLUMN public.agent_memories.contradicted_by_id IS 'DEFERRED (SCHEMA-F1). Awaiting /contradict command or dave-correction flow design. Column retained — dropping has rollback cost.';
