-- Migration 079: Rename als_learned_weights to propensity_learned_weights
-- Directive #153 Phase 3 — API/Models/Services + als_learned_weights rename
-- This migration renames the client learned weights column as part of the ALS → Propensity renaming

-- Rename the column in clients table
ALTER TABLE clients 
RENAME COLUMN als_learned_weights TO propensity_learned_weights;

-- Add comment for documentation
COMMENT ON COLUMN clients.propensity_learned_weights IS 'Learned propensity scoring weights from conversion pattern analysis (formerly als_learned_weights)';
