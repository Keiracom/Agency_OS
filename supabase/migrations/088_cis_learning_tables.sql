-- Migration 088: CIS Recursive Learning Tables
-- Directive #179: Measurement infrastructure for recursive learning
-- Pre-conditions: None of these tables existed (LAW I-A verified)

-- Table 1: Per-directive execution tracking
CREATE TABLE IF NOT EXISTS cis_directive_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    directive_id INTEGER NOT NULL,
    issued_date TIMESTAMPTZ NOT NULL,
    completed_date TIMESTAMPTZ,
    execution_rounds INTEGER NOT NULL DEFAULT 1,
    scope_creep BOOLEAN NOT NULL DEFAULT FALSE,
    verification_first_pass BOOLEAN NOT NULL DEFAULT TRUE,
    tokens_estimated INTEGER,
    save_completed BOOLEAN NOT NULL DEFAULT FALSE,
    agents_used TEXT[] NOT NULL DEFAULT '{}',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cis_directive_metrics_directive_id ON cis_directive_metrics(directive_id);
CREATE INDEX IF NOT EXISTS idx_cis_directive_metrics_issued_date ON cis_directive_metrics(issued_date DESC);

-- Table 2: CEO error encoding and correction log
CREATE TABLE IF NOT EXISTS cis_ceo_corrections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    what_was_assumed TEXT NOT NULL,
    what_was_true TEXT NOT NULL,
    error_class TEXT NOT NULL,
    encoded_fix TEXT NOT NULL,
    applied_to TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cis_ceo_corrections_date ON cis_ceo_corrections(date DESC);
CREATE INDEX IF NOT EXISTS idx_cis_ceo_corrections_error_class ON cis_ceo_corrections(error_class);

-- Table 3: Per-agent quality and performance metrics
CREATE TABLE IF NOT EXISTS cis_agent_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id TEXT NOT NULL,
    directive_id INTEGER NOT NULL,
    task_type TEXT NOT NULL,
    quality_score INTEGER NOT NULL CHECK (quality_score BETWEEN 1 AND 5),
    tokens_used INTEGER,
    completion_minutes INTEGER,
    issues_found TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cis_agent_metrics_directive_id ON cis_agent_metrics(directive_id);
CREATE INDEX IF NOT EXISTS idx_cis_agent_metrics_agent_id ON cis_agent_metrics(agent_id);

-- Table 4: Improvement proposal lifecycle
CREATE TABLE IF NOT EXISTS cis_improvement_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_loop TEXT NOT NULL CHECK (source_loop IN ('directive_quality', 'ceo_correction', 'agent_performance', 'competitive', 'tooling')),
    finding TEXT NOT NULL,
    action_taken TEXT,
    outcome_measured TEXT,
    status TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed', 'adopted', 'rejected', 'measured')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cis_improvement_log_status ON cis_improvement_log(status);
CREATE INDEX IF NOT EXISTS idx_cis_improvement_log_date ON cis_improvement_log(date DESC);
