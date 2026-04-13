CREATE TABLE IF NOT EXISTS public.agent_comms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_agent TEXT NOT NULL CHECK (from_agent IN ('ceo','cto','dave')),
    to_agent TEXT NOT NULL CHECK (to_agent IN ('ceo','cto','dave')),
    message_type TEXT NOT NULL CHECK (message_type IN ('directive','completion','question','status','approval_request','escalation','ratification')),
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    references_directive TEXT,
    phase TEXT,
    requires_dave_approval BOOLEAN DEFAULT false,
    dave_approved_at TIMESTAMPTZ,
    dave_approved_by UUID,
    budget_impact_usd NUMERIC(10,2),
    created_at TIMESTAMPTZ DEFAULT now(),
    read_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_agent_comms_to_read ON agent_comms(to_agent, read_at);
CREATE INDEX IF NOT EXISTS idx_agent_comms_approval ON agent_comms(requires_dave_approval, dave_approved_at);

ALTER TABLE agent_comms ENABLE ROW LEVEL SECURITY;

CREATE POLICY agent_comms_service_all ON agent_comms
    FOR ALL TO service_role
    USING (true) WITH CHECK (true);

CREATE POLICY agent_comms_dave_read ON agent_comms
    FOR SELECT TO authenticated
    USING (from_agent = 'ceo' OR to_agent = 'dave');

COMMENT ON TABLE agent_comms IS 'Inter-agent communication table. CEO/CTO write via service key. Dave reads via authenticated. Option A from #ROADMAP-MASTER.';
