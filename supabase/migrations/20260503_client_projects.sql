-- Client projects tracking table
-- Per Dave directive 2026-05-03
CREATE TABLE IF NOT EXISTS client_projects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_name     TEXT NOT NULL,
    project_name    TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'active',
    scope_summary   TEXT,
    price_aud       NUMERIC,
    cost_aud        NUMERIC,
    started_at      TIMESTAMPTZ,
    deadline        TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for common queries
CREATE INDEX IF NOT EXISTS idx_client_projects_status ON client_projects (status);
CREATE INDEX IF NOT EXISTS idx_client_projects_client ON client_projects (client_name);
