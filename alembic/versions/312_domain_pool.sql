-- Directive #312: Salesforge domain pool

-- Burner domain lifecycle
CREATE TABLE IF NOT EXISTS burner_domains (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_name text NOT NULL UNIQUE,
    tld text NOT NULL DEFAULT 'com.au',
    salesforge_domain_id text,
    status text NOT NULL DEFAULT 'candidate' CHECK (status IN (
        'candidate', 'approved', 'purchasing', 'dns_configuring',
        'warming', 'ready', 'assigned', 'quarantined', 'retired'
    )),
    pattern_type text,
    purchased_at timestamptz,
    warmup_started_at timestamptz,
    ready_at timestamptz,
    assigned_to_client_id uuid REFERENCES clients(id),
    assigned_at timestamptz,
    released_at timestamptz,
    quarantine_until timestamptz,
    sender_reputation_score float,
    daily_send_limit int DEFAULT 50,
    dry_run boolean DEFAULT true,
    notes text,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_burner_domains_status ON burner_domains(status);
CREATE INDEX IF NOT EXISTS idx_burner_domains_client ON burner_domains(assigned_to_client_id) WHERE assigned_to_client_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_burner_domains_ready ON burner_domains(status) WHERE status = 'ready';

-- Burner mailboxes (2 per domain)
CREATE TABLE IF NOT EXISTS burner_mailboxes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id uuid NOT NULL REFERENCES burner_domains(id) ON DELETE CASCADE,
    mailbox_address text NOT NULL UNIQUE,
    display_name_template text DEFAULT '{first_name} {last_name}',
    salesforge_mailbox_id text,
    status text NOT NULL DEFAULT 'creating' CHECK (status IN ('creating', 'warming', 'ready', 'assigned', 'retired')),
    created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_burner_mailboxes_domain ON burner_mailboxes(domain_id);

-- Domain naming patterns (seed approved styles)
CREATE TABLE IF NOT EXISTS domain_naming_patterns (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_type text NOT NULL,
    seeds jsonb NOT NULL,
    suffixes jsonb NOT NULL,
    approved boolean DEFAULT false,
    created_at timestamptz DEFAULT now()
);

INSERT INTO domain_naming_patterns (pattern_type, seeds, suffixes, approved) VALUES
('evocative_compound', '["northgate","meridian","cascade","clarion","vestri","thornfield","kalyan","harbourpoint","alderton","belmore","kinross","dalton","ashton","pennant","bellevue"]'::jsonb, '["partners","group","advisory","brief","point","co"]'::jsonb, true),
('professional_abstract', '["clarion","vestri","thornfield","kalyan","alderton","pennant","kinross","dalton"]'::jsonb, '["brief","group","co","advisory","capital"]'::jsonb, true),
('geographic_neutral', '["coastal","ridgeline","summit","headland","foreshore","highland","lakeside","sandstone"]'::jsonb, '["vantage","advisory","brief","north","group","south"]'::jsonb, true),
('landscape_compound', '["redgum","stonewood","silverbark","bluestone","ironbark","ashwood","blackwood","sandridge"]'::jsonb, '["group","co","advisory","partners","capital"]'::jsonb, true)
ON CONFLICT DO NOTHING;
