# Database: Email Infrastructure

**Migration:** `017_email_infrastructure.sql`  
**Phase:** 19 (Email Infrastructure)

---

## Email Domains Table

```sql
CREATE TABLE email_domains (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id),
    
    -- Domain info
    domain TEXT NOT NULL UNIQUE,
    provider TEXT NOT NULL DEFAULT 'infraforge',  -- infraforge, manual
    
    -- DNS status
    dns_configured BOOLEAN DEFAULT FALSE,
    spf_valid BOOLEAN DEFAULT FALSE,
    dkim_valid BOOLEAN DEFAULT FALSE,
    dmarc_valid BOOLEAN DEFAULT FALSE,
    
    -- Reputation
    domain_age_days INTEGER,
    reputation_score FLOAT,  -- 0-100
    
    -- Limits
    daily_send_limit INTEGER DEFAULT 50,
    current_daily_sends INTEGER DEFAULT 0,
    
    -- Status
    status TEXT DEFAULT 'pending',  -- pending, active, suspended, deleted
    
    -- Provider IDs
    infraforge_domain_id TEXT,
    smartlead_domain_id TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    
    CONSTRAINT valid_status CHECK (
        status IN ('pending', 'active', 'suspended', 'deleted')
    )
);

CREATE INDEX idx_email_domains_client ON email_domains(client_id);
CREATE INDEX idx_email_domains_status ON email_domains(status);
```

---

## Email Mailboxes Table

```sql
CREATE TABLE email_mailboxes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id UUID NOT NULL REFERENCES email_domains(id),
    client_id UUID NOT NULL REFERENCES clients(id),
    
    -- Mailbox info
    email_address TEXT NOT NULL UNIQUE,
    display_name TEXT,
    
    -- Provider IDs
    infraforge_mailbox_id TEXT,
    smartlead_account_id TEXT,
    
    -- Warmup status
    warmup_enabled BOOLEAN DEFAULT TRUE,
    warmup_started_at TIMESTAMPTZ,
    warmup_completed_at TIMESTAMPTZ,
    warmup_stage INTEGER DEFAULT 0,  -- 0-30 (days)
    
    -- Sending limits (increases during warmup)
    daily_send_limit INTEGER DEFAULT 10,
    current_daily_sends INTEGER DEFAULT 0,
    
    -- Health metrics
    bounce_rate FLOAT DEFAULT 0,
    spam_rate FLOAT DEFAULT 0,
    reply_rate FLOAT DEFAULT 0,
    
    -- Status
    status TEXT DEFAULT 'warming',  -- warming, active, paused, suspended
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    
    CONSTRAINT valid_mailbox_status CHECK (
        status IN ('warming', 'active', 'paused', 'suspended')
    )
);

CREATE INDEX idx_mailboxes_domain ON email_mailboxes(domain_id);
CREATE INDEX idx_mailboxes_client ON email_mailboxes(client_id);
CREATE INDEX idx_mailboxes_status ON email_mailboxes(status);
```

---

## Warmup Stats Table

```sql
CREATE TABLE warmup_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mailbox_id UUID NOT NULL REFERENCES email_mailboxes(id),
    
    -- Daily stats
    date DATE NOT NULL,
    emails_sent INTEGER DEFAULT 0,
    emails_received INTEGER DEFAULT 0,
    warmup_score FLOAT,  -- Smartlead warmup score
    
    -- Health indicators
    inbox_rate FLOAT,  -- % landing in inbox vs spam
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_mailbox_date UNIQUE (mailbox_id, date)
);

CREATE INDEX idx_warmup_stats_mailbox_date ON warmup_stats(mailbox_id, date DESC);
```

---

## Tier Infrastructure Allocation

| Tier | Domains | Mailboxes | Dedicated IPs |
|------|---------|-----------|---------------|
| Ignition | 2 | 3 | 1 |
| Velocity | 3 | 6 | 1 |
| Dominance | 5 | 11 | 2 |

---

## Warmup Schedule

| Day | Daily Limit | Cumulative |
|-----|-------------|------------|
| 1-5 | 10 | 50 |
| 6-10 | 20 | 150 |
| 11-15 | 30 | 300 |
| 16-20 | 40 | 500 |
| 21-25 | 50 | 750 |
| 26-30 | 60 | 1050 |
| 31+ | 75 | Full capacity |

---

## DNS Records Required

| Record | Type | Purpose |
|--------|------|---------|
| SPF | TXT | Authorize sending IPs |
| DKIM | TXT | Email signing |
| DMARC | TXT | Policy enforcement |
| MX | MX | Receive replies |
