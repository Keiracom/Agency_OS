-- Migration: 010_onboarding_connection_timestamps
-- Purpose: Add connection timestamp columns to clients table for onboarding gates
-- Architecture Decision: LinkedIn and CRM connections are mandatory for onboarding
-- Date: 2026-02-25

-- ============================================
-- ADD CONNECTION TIMESTAMP COLUMNS
-- ============================================

-- LinkedIn connection timestamp (denormalized from linkedin_seats)
ALTER TABLE clients
ADD COLUMN IF NOT EXISTS linkedin_connected_at TIMESTAMP WITH TIME ZONE;

-- CRM connection timestamp (denormalized from client_crm_configs)
ALTER TABLE clients
ADD COLUMN IF NOT EXISTS crm_connected_at TIMESTAMP WITH TIME ZONE;

-- Add comments for documentation
COMMENT ON COLUMN clients.linkedin_connected_at IS 'Timestamp when first LinkedIn seat was connected (denormalized from linkedin_seats). Required for onboarding completion.';
COMMENT ON COLUMN clients.crm_connected_at IS 'Timestamp when CRM was first connected (denormalized from client_crm_configs). Required for onboarding completion.';

-- ============================================
-- BACKFILL EXISTING DATA
-- ============================================

-- Backfill linkedin_connected_at from existing linkedin_seats
UPDATE clients c
SET linkedin_connected_at = (
    SELECT MIN(ls.created_at)
    FROM linkedin_seats ls
    WHERE ls.client_id = c.id
    AND ls.unipile_account_id IS NOT NULL
    AND ls.status NOT IN ('disconnected', 'restricted', 'pending')
)
WHERE c.linkedin_connected_at IS NULL
AND EXISTS (
    SELECT 1 FROM linkedin_seats ls
    WHERE ls.client_id = c.id
    AND ls.unipile_account_id IS NOT NULL
    AND ls.status NOT IN ('disconnected', 'restricted', 'pending')
);

-- Backfill crm_connected_at from existing client_crm_configs
UPDATE clients c
SET crm_connected_at = (
    SELECT MIN(ccc.created_at)
    FROM client_crm_configs ccc
    WHERE ccc.client_id = c.id
    AND ccc.is_active = true
)
WHERE c.crm_connected_at IS NULL
AND EXISTS (
    SELECT 1 FROM client_crm_configs ccc
    WHERE ccc.client_id = c.id
    AND ccc.is_active = true
);

-- ============================================
-- CREATE INDEX FOR FAST GATE CHECKS
-- ============================================

-- Index for checking onboarding completion status
CREATE INDEX IF NOT EXISTS idx_clients_onboarding_gates
ON clients (id)
WHERE linkedin_connected_at IS NOT NULL AND crm_connected_at IS NOT NULL;

-- ============================================
-- VERIFICATION
-- ============================================

-- Show clients with both connections vs missing connections
DO $$
DECLARE
    both_connected INT;
    linkedin_only INT;
    crm_only INT;
    neither INT;
BEGIN
    SELECT COUNT(*) INTO both_connected
    FROM clients
    WHERE linkedin_connected_at IS NOT NULL AND crm_connected_at IS NOT NULL AND deleted_at IS NULL;

    SELECT COUNT(*) INTO linkedin_only
    FROM clients
    WHERE linkedin_connected_at IS NOT NULL AND crm_connected_at IS NULL AND deleted_at IS NULL;

    SELECT COUNT(*) INTO crm_only
    FROM clients
    WHERE linkedin_connected_at IS NULL AND crm_connected_at IS NOT NULL AND deleted_at IS NULL;

    SELECT COUNT(*) INTO neither
    FROM clients
    WHERE linkedin_connected_at IS NULL AND crm_connected_at IS NULL AND deleted_at IS NULL;

    RAISE NOTICE 'Onboarding gate status after migration:';
    RAISE NOTICE '  Both connected: %', both_connected;
    RAISE NOTICE '  LinkedIn only: %', linkedin_only;
    RAISE NOTICE '  CRM only: %', crm_only;
    RAISE NOTICE '  Neither: %', neither;
END $$;
