-- Migration 022: signal_configurations table
-- Directive #256

CREATE TABLE IF NOT EXISTS signal_configurations (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    vertical_slug       text UNIQUE NOT NULL,
    display_name        text NOT NULL,
    description         text,
    service_signals     jsonb NOT NULL DEFAULT '[]',
    discovery_config    jsonb NOT NULL DEFAULT '{}',
    enrichment_gates    jsonb NOT NULL DEFAULT '{}',
    channel_config      jsonb NOT NULL DEFAULT '{}',
    created_at          timestamptz NOT NULL DEFAULT NOW(),
    updated_at          timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signal_config_vertical_slug ON signal_configurations(vertical_slug);

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_signal_configurations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_signal_configurations_updated_at
    BEFORE UPDATE ON signal_configurations
    FOR EACH ROW EXECUTE FUNCTION update_signal_configurations_updated_at();
