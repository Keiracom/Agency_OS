-- address_source: tracks where address/location data came from
-- Directive #260 — Stage 2 GMB Reverse Lookup
-- Values: 'gmb', 'website', 'manual'

ALTER TABLE business_universe
ADD COLUMN IF NOT EXISTS address_source TEXT;
