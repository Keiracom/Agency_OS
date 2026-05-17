-- KEI-95: claim_source discriminator for mechanical self-claim exemption.
-- Ratified 3-way Aiden+Max+Elliot ts ~1779022275 (Option B).
ALTER TABLE public.tasks
  ADD COLUMN IF NOT EXISTS claim_source TEXT NOT NULL DEFAULT 'manual'
    CHECK (claim_source IN ('auto_loop', 'manual'));

-- Backfill: existing rows pre-self-claim era are all 'manual' (default covers).
-- No data migration needed beyond the default.

COMMENT ON COLUMN public.tasks.claim_source IS
  'KEI-95: discriminator for enforcer rules + Step 0 gate. auto_loop = bd ready/claim from agent_self_claim_loop.sh (mechanical governance via phase-lock + SKIP LOCKED is sufficient); manual = peer/Dave/orchestrator dispatch (full CONCUR + Step 0 ceremony retained).';
