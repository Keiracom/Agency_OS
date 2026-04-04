-- EVO-004: Dynamic flow generator tables
-- Created: 2026-04-04

CREATE TABLE IF NOT EXISTS evo_task_queue (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id text NOT NULL,
  flow_run_id text NOT NULL,
  agent_id text NOT NULL,
  description text NOT NULL,
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','claimed','completed','failed')),
  created_at timestamptz DEFAULT now(),
  claimed_at timestamptz,
  completed_at timestamptz
);

CREATE INDEX IF NOT EXISTS idx_evo_task_queue_pending
  ON evo_task_queue (created_at ASC) WHERE status = 'pending';

CREATE TABLE IF NOT EXISTS evo_task_results (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id text NOT NULL,
  flow_run_id text NOT NULL,
  agent_id text NOT NULL,
  status text NOT NULL CHECK (status IN ('completed','failed')),
  agent_output text,
  verification_output text,
  verified boolean,
  attempts integer DEFAULT 1,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_evo_task_results_lookup
  ON evo_task_results (task_id, flow_run_id);
