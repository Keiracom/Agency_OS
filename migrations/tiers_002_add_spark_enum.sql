-- TIERS-002: Add 'spark' to tier_type enum
-- Manual SSOT ratified Mar 26 2026
-- Dominance kept in enum for migration safety (no new records)

ALTER TYPE tier_type ADD VALUE IF NOT EXISTS 'spark' BEFORE 'ignition';

-- Note: PostgreSQL does not support DROP VALUE from enum.
-- 'dominance' remains in enum but should not be assigned to new clients.
-- Application-level enforcement in src/config/tiers.py
