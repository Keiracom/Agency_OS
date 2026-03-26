-- Deduplicate business_universe by domain
-- Keep row with highest pipeline_stage; ties broken by most recent updated_at
-- Directive #267

-- Step 1: Delete duplicates for real (non-empty) domains,
-- keep the "best" row per domain (highest stage, most recent updated_at)
DELETE FROM business_universe
WHERE id NOT IN (
    SELECT DISTINCT ON (domain) id
    FROM business_universe
    WHERE domain IS NOT NULL AND domain <> ''
    ORDER BY domain, pipeline_stage DESC, pipeline_updated_at DESC NULLS LAST, created_at DESC
)
AND domain IS NOT NULL AND domain <> '';

-- Step 2: Add partial UNIQUE index on domain
-- (excludes NULL and empty strings; multiple blank-domain rows are kept until
--  the BUG-266-2 blocklist fix prevents new ones from being inserted)
CREATE UNIQUE INDEX IF NOT EXISTS uq_bu_domain
    ON business_universe(domain)
    WHERE domain IS NOT NULL AND domain <> '';
