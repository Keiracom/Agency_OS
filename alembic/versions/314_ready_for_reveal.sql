-- Directive #314: Add ready_for_reveal cycle status and cycle_events audit table
-- Migration: 314_ready_for_reveal.sql

-- cycle.status is a plain VARCHAR(20), no enum type to alter.
-- The model uses default='active' and accepts any string value.
-- ready_for_reveal is a valid status string; no DDL change needed for the column.

-- Cycle events audit table
CREATE TABLE IF NOT EXISTS cycle_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    cycle_id uuid NOT NULL REFERENCES cycles(id) ON DELETE CASCADE,
    event_type text NOT NULL,  -- 'started', 'paused', 'resumed', 'reveal_ready', 'revealed', 'completed'
    triggered_by text,         -- 'customer', 'system', 'admin', 'timeout'
    metadata jsonb,
    created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cycle_events_cycle ON cycle_events(cycle_id);
