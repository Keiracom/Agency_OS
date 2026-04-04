-- EVO-005: Task Consumer + Guardrails schema
-- Creates evo_auth_requests table and extends existing tables.

CREATE TABLE IF NOT EXISTS evo_auth_requests (
    id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id       text        NOT NULL,
    flow_run_id   text,
    reason        text,
    request_type  text        NOT NULL DEFAULT 'budget_exceeded'
                              CHECK (request_type IN ('budget_exceeded', 'verification_failed')),
    estimated     jsonb,
    actual        jsonb,
    status        text        NOT NULL DEFAULT 'pending'
                              CHECK (status IN ('pending', 'approved', 'denied')),
    created_at    timestamptz DEFAULT now(),
    resolved_at   timestamptz
);

ALTER TABLE evo_task_queue
    ADD COLUMN IF NOT EXISTS estimated_cost jsonb;

ALTER TABLE evo_task_results
    ADD COLUMN IF NOT EXISTS actual_cost jsonb;
