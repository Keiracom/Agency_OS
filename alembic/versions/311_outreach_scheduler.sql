-- Directive #311: Outreach scheduler schema

-- Cycle state machine
CREATE TABLE IF NOT EXISTS cycles (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id uuid NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    cycle_number int NOT NULL DEFAULT 1,
    started_at timestamptz NOT NULL DEFAULT now(),
    target_prospects int NOT NULL,
    cycle_day_1_date date NOT NULL DEFAULT CURRENT_DATE,
    status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'complete', 'cancelled')),
    completed_at timestamptz,
    warmup_mode text NOT NULL DEFAULT 'full' CHECK (warmup_mode IN ('full', 'first_cycle_rampup', 'dormant_reactivation')),
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cycles_client ON cycles(client_id);
CREATE INDEX IF NOT EXISTS idx_cycles_status ON cycles(client_id, status) WHERE status = 'active';
CREATE UNIQUE INDEX IF NOT EXISTS idx_cycles_active_per_client ON cycles(client_id) WHERE status = 'active';

-- Cycle prospects (links prospects to cycles with outreach state)
CREATE TABLE IF NOT EXISTS cycle_prospects (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    cycle_id uuid NOT NULL REFERENCES cycles(id) ON DELETE CASCADE,
    prospect_id uuid NOT NULL,
    entered_cycle_on_day int NOT NULL,
    outreach_status text NOT NULL DEFAULT 'pending' CHECK (outreach_status IN ('pending', 'in_sequence', 'replied', 'meeting_booked', 'suppressed', 'complete')),
    current_step int NOT NULL DEFAULT 0,
    next_action_at timestamptz,
    sequence_type text NOT NULL DEFAULT 'standard' CHECK (sequence_type IN ('standard', 'warming', 'dormant_account')),
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    UNIQUE(cycle_id, prospect_id)
);

CREATE INDEX IF NOT EXISTS idx_cycle_prospects_cycle ON cycle_prospects(cycle_id);
CREATE INDEX IF NOT EXISTS idx_cycle_prospects_status ON cycle_prospects(outreach_status);
CREATE INDEX IF NOT EXISTS idx_cycle_prospects_next ON cycle_prospects(next_action_at) WHERE outreach_status = 'in_sequence';

-- Outreach actions (individual scheduled + fired actions)
CREATE TABLE IF NOT EXISTS outreach_actions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    cycle_id uuid NOT NULL REFERENCES cycles(id) ON DELETE CASCADE,
    cycle_prospect_id uuid NOT NULL REFERENCES cycle_prospects(id) ON DELETE CASCADE,
    prospect_id uuid NOT NULL,
    channel text NOT NULL CHECK (channel IN ('email', 'linkedin_connect', 'linkedin_message', 'voice', 'sms')),
    action_type text NOT NULL,
    step_number int NOT NULL,
    scheduled_at timestamptz NOT NULL,
    fired_at timestamptz,
    status text NOT NULL DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'fired', 'skipped', 'failed', 'held')),
    result jsonb,
    skipped_reason text,
    dry_run boolean NOT NULL DEFAULT true,
    created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_outreach_actions_scheduled ON outreach_actions(scheduled_at, status) WHERE status = 'scheduled';
CREATE INDEX IF NOT EXISTS idx_outreach_actions_cycle ON outreach_actions(cycle_id);
CREATE INDEX IF NOT EXISTS idx_outreach_actions_prospect ON outreach_actions(prospect_id);

-- Sequence templates (JSONB-driven, per-tier customizable)
CREATE TABLE IF NOT EXISTS sequence_templates (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL UNIQUE,
    sequence_type text NOT NULL DEFAULT 'standard',
    steps jsonb NOT NULL,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- Seed the standard template
INSERT INTO sequence_templates (name, sequence_type, steps) VALUES
('standard', 'standard', '[
    {"step": 1, "day_offset": 0, "channel": "email", "action_type": "email_1", "window": "morning_email"},
    {"step": 2, "day_offset": 0, "channel": "linkedin_connect", "action_type": "li_connect", "window": "morning_linkedin"},
    {"step": 3, "day_offset": 2, "channel": "email", "action_type": "email_2", "window": "morning_email", "skip_if": "replied"},
    {"step": 4, "day_offset": 2, "channel": "linkedin_message", "action_type": "li_msg_1", "window": "afternoon_linkedin", "requires": "linkedin_connected"},
    {"step": 5, "day_offset": 6, "channel": "voice", "action_type": "voice_1", "window": "afternoon_voice", "skip_if": "replied"},
    {"step": 6, "day_offset": 9, "channel": "email", "action_type": "email_3", "window": "morning_email", "skip_if": "replied"},
    {"step": 7, "day_offset": 9, "channel": "voice", "action_type": "voice_2", "window": "afternoon_voice", "skip_if": "replied"},
    {"step": 8, "day_offset": 13, "channel": "linkedin_message", "action_type": "li_msg_2", "window": "late_morning_linkedin", "requires": "linkedin_connected", "skip_if": "replied"}
]'::jsonb),
('warming', 'warming', '[
    {"step": 1, "day_offset": 0, "channel": "email", "action_type": "email_1", "window": "morning_email"},
    {"step": 2, "day_offset": 0, "channel": "linkedin_connect", "action_type": "li_connect", "window": "morning_linkedin", "volume_cap": 0.5},
    {"step": 3, "day_offset": 2, "channel": "email", "action_type": "email_2", "window": "morning_email", "skip_if": "replied"},
    {"step": 4, "day_offset": 2, "channel": "linkedin_message", "action_type": "li_msg_1", "window": "afternoon_linkedin", "requires": "linkedin_connected", "volume_cap": 0.5},
    {"step": 5, "day_offset": 6, "channel": "voice", "action_type": "voice_1", "window": "afternoon_voice", "skip_if": "replied"},
    {"step": 6, "day_offset": 9, "channel": "email", "action_type": "email_3", "window": "morning_email", "skip_if": "replied"},
    {"step": 7, "day_offset": 13, "channel": "linkedin_message", "action_type": "li_msg_2", "window": "late_morning_linkedin", "requires": "linkedin_connected", "volume_cap": 0.75}
]'::jsonb),
('dormant_account', 'dormant_account', '[
    {"step": 1, "day_offset": 0, "channel": "email", "action_type": "email_1", "window": "morning_email"},
    {"step": 2, "day_offset": 2, "channel": "email", "action_type": "email_2", "window": "morning_email", "skip_if": "replied"},
    {"step": 3, "day_offset": 6, "channel": "voice", "action_type": "voice_1", "window": "afternoon_voice", "skip_if": "replied"},
    {"step": 4, "day_offset": 9, "channel": "email", "action_type": "email_3", "window": "morning_email", "skip_if": "replied"},
    {"step": 5, "day_offset": 9, "channel": "voice", "action_type": "voice_2", "window": "afternoon_voice", "skip_if": "replied"}
]'::jsonb)
ON CONFLICT (name) DO NOTHING;
