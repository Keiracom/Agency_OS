-- Client projects tracking table
-- Per Dave directive 2026-05-03
CREATE TABLE IF NOT EXISTS client_projects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id       UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    client_name     TEXT NOT NULL,
    project_name    TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'completed', 'on_hold', 'cancelled')),
    scope_summary   TEXT,
    price_aud       NUMERIC,
    cost_aud        NUMERIC,
    started_at      TIMESTAMPTZ,
    deadline        TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_client_projects_status
    ON client_projects (status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_client_projects_client_id
    ON client_projects (client_id) WHERE deleted_at IS NULL;

-- updated_at trigger (reuses existing function from 002_clients_users_memberships)
CREATE TRIGGER set_client_projects_updated_at
    BEFORE UPDATE ON client_projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();
