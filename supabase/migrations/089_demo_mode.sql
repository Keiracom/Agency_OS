-- Migration: 089_demo_mode.sql
-- Directive #184 Fix 3: Demo mode support
-- Adds is_demo flag to clients and campaigns, inserts a demo client.

-- Add is_demo to clients
ALTER TABLE clients ADD COLUMN IF NOT EXISTS is_demo BOOLEAN DEFAULT false;

-- Add is_demo to campaigns
ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS is_demo BOOLEAN DEFAULT false;

-- Insert a demo client for sandbox/demo flows
-- Note: uses name column (not company_name — that column doesn't exist on clients)
INSERT INTO clients (
    id,
    name,
    is_demo,
    created_at,
    updated_at
)
VALUES (
    'demo0000-0000-0000-0000-000000000001'::uuid,
    'Demo Agency',
    true,
    NOW(),
    NOW()
)
ON CONFLICT (id) DO NOTHING;

-- Index for fast is_demo lookups
CREATE INDEX IF NOT EXISTS idx_clients_is_demo ON clients (is_demo) WHERE is_demo = true;
CREATE INDEX IF NOT EXISTS idx_campaigns_is_demo ON campaigns (is_demo) WHERE is_demo = true;
