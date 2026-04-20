-- Directive #309: Service-first onboarding model
-- Add service_area, services, onboarding_completed_at to clients

-- Service area: metro/state/national
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'service_area_type') THEN
    CREATE TYPE service_area_type AS ENUM ('metro', 'state', 'national');
  END IF;
END$$;

ALTER TABLE clients ADD COLUMN IF NOT EXISTS service_area service_area_type;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS services jsonb;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS onboarding_completed_at timestamptz;

-- LinkedIn account quality tracking
CREATE TABLE IF NOT EXISTS client_linkedin_accounts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id uuid NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    unipile_account_id text,
    status text NOT NULL DEFAULT 'ready' CHECK (status IN ('ready', 'warming', 'disabled')),
    connected_at timestamptz DEFAULT now(),
    connection_count int,
    has_profile_photo boolean,
    has_headline boolean,
    has_recent_activity boolean,
    last_quality_check timestamptz,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_client_linkedin_accounts_client ON client_linkedin_accounts(client_id);

COMMENT ON COLUMN clients.service_area IS 'Metro/State/National — ratified Mar 30 2026, replaces icp_locations for discovery scope';
COMMENT ON COLUMN clients.services IS 'Confirmed services list from agency website scrape — replaces deprecated icp_industries';
COMMENT ON COLUMN clients.onboarding_completed_at IS 'Timestamp when the 4-page onboarding flow was completed';
