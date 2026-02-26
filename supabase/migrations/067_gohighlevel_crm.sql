-- Migration: 067_gohighlevel_crm.sql
-- Purpose: Add GoHighLevel CRM support columns to client_crm_configs
-- Phase: 24E - CRM Push
-- Task: CRM-010 (GoHighLevel Adapter)

-- Add GoHighLevel-specific columns to client_crm_configs
ALTER TABLE client_crm_configs
ADD COLUMN IF NOT EXISTS ghl_location_id TEXT,
ADD COLUMN IF NOT EXISTS ghl_company_id TEXT;

-- Add comment for documentation
COMMENT ON COLUMN client_crm_configs.ghl_location_id IS 'GoHighLevel location/sub-account ID';
COMMENT ON COLUMN client_crm_configs.ghl_company_id IS 'GoHighLevel company/agency ID';

-- Update the crm_type check constraint to include gohighlevel
-- First drop the existing constraint if it exists
ALTER TABLE client_crm_configs DROP CONSTRAINT IF EXISTS client_crm_configs_crm_type_check;

-- Add new constraint that includes gohighlevel
ALTER TABLE client_crm_configs ADD CONSTRAINT client_crm_configs_crm_type_check 
CHECK (crm_type IN ('hubspot', 'pipedrive', 'close', 'gohighlevel'));

-- Create index for GHL location lookups
CREATE INDEX IF NOT EXISTS idx_client_crm_configs_ghl_location 
ON client_crm_configs(ghl_location_id) 
WHERE ghl_location_id IS NOT NULL;

-- ============================================
-- VERIFICATION CHECKLIST
-- ============================================
-- [x] ghl_location_id column added
-- [x] ghl_company_id column added
-- [x] crm_type constraint updated to include 'gohighlevel'
-- [x] Index created for location lookups
-- [x] Comments added for documentation
