# Database: Campaigns

**Migration:** `003_campaigns.sql`

---

## Campaigns Table

```sql
CREATE TABLE campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id),
    name TEXT NOT NULL,
    status campaign_status DEFAULT 'draft',
    permission_mode permission_mode DEFAULT 'co_pilot',
    
    -- Targeting
    target_industries TEXT[],
    target_titles TEXT[],
    target_company_sizes TEXT[],
    target_locations TEXT[],
    
    -- Channel allocation (percentages, must sum to 100)
    email_allocation INTEGER DEFAULT 40,
    linkedin_allocation INTEGER DEFAULT 30,
    voice_allocation INTEGER DEFAULT 20,
    sms_allocation INTEGER DEFAULT 5,
    mail_allocation INTEGER DEFAULT 5,
    
    -- Limits
    daily_lead_limit INTEGER DEFAULT 50,
    total_lead_limit INTEGER,
    
    -- Dates
    start_date DATE,
    end_date DATE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    
    -- Constraint: allocation must sum to 100
    CONSTRAINT valid_allocation CHECK (
        email_allocation + linkedin_allocation + voice_allocation + 
        sms_allocation + mail_allocation = 100
    )
);

CREATE INDEX idx_campaigns_client ON campaigns(client_id);
CREATE INDEX idx_campaigns_status ON campaigns(status);
```

---

## Campaign Status Flow

```
draft ──► active ──► paused ──► active ──► completed
                        │
                        └──► completed
```

| Status | Description |
|--------|-------------|
| `draft` | Not yet started, can edit all fields |
| `active` | Running, leads being processed |
| `paused` | Temporarily stopped, can resume |
| `completed` | Finished, read-only |

---

## Permission Modes

| Mode | Description | User Action |
|------|-------------|-------------|
| `autopilot` | Fully automated | None required |
| `co_pilot` | AI suggests, user approves | Approve/reject suggestions |
| `manual` | User controls everything | Initiate all actions |

---

## Channel Allocation

Allocation determines what percentage of leads go to each channel:

```python
# Example: Ignition tier campaign
allocation = {
    "email": 40,      # 40% of leads get email
    "linkedin": 30,   # 30% get LinkedIn
    "voice": 20,      # 20% get voice
    "sms": 5,         # 5% get SMS (Hot only)
    "mail": 5         # 5% get mail (Hot only)
}
# Must sum to 100
```

Note: Actual channel access is gated by ALS tier. A Cold lead won't get LinkedIn even if allocated.

---

## Targeting Fields

| Field | Type | Example |
|-------|------|---------|
| `target_industries` | TEXT[] | `["Digital Marketing", "SEO"]` |
| `target_titles` | TEXT[] | `["CEO", "Marketing Director"]` |
| `target_company_sizes` | TEXT[] | `["1-10", "11-50"]` |
| `target_locations` | TEXT[] | `["Sydney", "Melbourne"]` |

These are used by Scout Engine when finding new leads.
