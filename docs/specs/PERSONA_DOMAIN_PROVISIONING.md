# Persona & Domain Provisioning System

**Status:** 🟡 IN DEVELOPMENT  
**Created:** 2026-01-30  
**Owner:** Dave + Elliot  

---

## Executive Summary

Automated system for pre-creating professional personas with matching domains, warming them via WarmForge, and allocating to clients at signup for Day 1 sending capability.

---

## Business Model

| Component | Created By | Pre-warmed |
|-----------|-----------|------------|
| Persona (name, title, bio, photo, signature) | Us (AI) | ✅ |
| Domain | Us (InfraForge) | ✅ |
| Mailbox | Us (InfraForge) | ✅ |
| Warmup | Us (WarmForge) | ✅ |
| Sending | Us (Salesforge) | ✅ |
| LinkedIn Account | **Client** | ❌ |

**Client provides LinkedIn. We provide everything else.**

---

## Naming Convention

**Persona-branded domains:**

| Pattern | Example (Persona: David Stephens) |
|---------|-----------------------------------|
| `{firstname}{lastname}.{tld}` | `davidstephens.io` |
| `{f}{lastname}.{tld}` | `dstephens.co` |
| `team{firstname}.{tld}` | `teamdavid.com` |

**Approved TLDs:** `.com`, `.io`, `.co`

**Mailbox pattern:** `{firstname}@{domain}` → `david@davidstephens.io`

---

## Tier Allocations

| Tier | Personas | Domains | Mailboxes | Monthly Price |
|------|----------|---------|-----------|---------------|
| Ignition | 2 | 3 | 6 | $2,500 |
| Velocity | 3 | 5 | 10 | $4,000 |
| Dominance | 4 | 9 | 18 | $7,500 |

*2 mailboxes per domain, ~1.5 domains per persona*

---

## Buffer Rule

**Formula:**
```
Required Buffer = Allocated Domains × 0.40
Shortfall = Required Buffer − Available Buffer
```

**Trigger Condition:**
```python
if available_buffer < (allocated × 0.40):
    shortfall = ceil((allocated × 0.40) - available_buffer)
    provision_personas_and_domains(count=shortfall)
```

**Trigger:** Event-driven via Stripe signup webhook (not cron)

---

## Data Model

### `personas` table (NEW)
```sql
CREATE TABLE personas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    title TEXT,
    company_name TEXT,
    bio TEXT,
    photo_url TEXT,
    signature_html TEXT,
    status TEXT DEFAULT 'available',  -- available, allocated, retired
    allocated_to_client_id UUID REFERENCES clients(id),
    allocated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### `resource_pool` table (MODIFIED)
```sql
ALTER TABLE resource_pool ADD COLUMN persona_id UUID REFERENCES personas(id);
```

### Hierarchy
```
Persona (David Stephens)
├── Domain: davidstephens.io (resource_pool)
│   ├── Mailbox: david@davidstephens.io
│   └── Mailbox: d.stephens@davidstephens.io
├── Domain: dstephens.co (resource_pool)
│   └── Mailbox: david@dstephens.co
└── Domain: teamdavid.com (resource_pool)
    └── Mailbox: david@teamdavid.com
```

---

## Architecture

### Triggers

| Trigger | Action |
|---------|--------|
| Stripe signup webhook | Allocate personas + domains → Replenish buffer if < 40% |
| Daily cron (6am AEST) | Poll WarmForge → Mark warmed domains AVAILABLE |

### Integration Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                      CLIENT SIGNUP (Stripe webhook)                 │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                        ┌───────────────────┐
                        │ onboarding_flow   │
                        └─────────┬─────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
            ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
            │ Allocate    │ │ Allocate    │ │ Extract ICP │
            │ personas    │ │ domains     │ │ + campaigns │
            └─────────────┘ └─────────────┘ └─────────────┘
                    │             │
                    ▼             ▼
            ┌─────────────────────────────┐
            │ Buffer < 40%?               │
            │ YES → persona_buffer_flow   │
            └─────────────────────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │ CLIENT LIVE DAY 1 │
                    │ (pre-warmed)      │
                    └───────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                         DAILY CRON (6am AEST)                       │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                        ┌───────────────────┐
                        │ warmup_monitor_   │
                        │ flow              │
                        └─────────┬─────────┘
                                  │
                                  ▼
                        ┌───────────────────┐
                        │ For each WARMING: │
                        │ • Check WarmForge │
                        │ • If heat >= 85   │
                        │   → AVAILABLE     │
                        └───────────────────┘
```

---

## External Service Workspace IDs

| Service | Workspace ID |
|---------|--------------|
| InfraForge | `wks_cho0dp6wypzgzkou1c0p4` |
| WarmForge | `wks_8wuh9f3b74o7o930ocoie` |
| Salesforge | `wks_b86a0iopxkzx2u3gvz9et` |

---

## Files

### New Files
| File | Purpose |
|------|---------|
| `supabase/migrations/054_personas.sql` | Personas table + resource_pool FK |
| `src/models/persona.py` | Persona SQLAlchemy model |
| `src/services/persona_service.py` | AI generation, allocation |
| `src/services/domain_provisioning_service.py` | Domain purchase, mailbox creation |
| `src/integrations/warmforge.py` | WarmForge API client |
| `src/orchestration/flows/persona_buffer_flow.py` | Buffer replenishment |
| `src/orchestration/flows/warmup_monitor_flow.py` | Daily warmup check |

### Modified Files
| File | Change |
|------|--------|
| `src/integrations/infraforge.py` | Already created, enhance if needed |
| `src/models/resource_pool.py` | Add persona_id FK |
| `src/orchestration/flows/onboarding_flow.py` | Call persona allocation |
| `src/orchestration/schedules/scheduled_jobs.py` | Add warmup monitor cron |
| `src/api/routes/webhooks.py` | Trigger buffer check on signup |

---

## Verification Checklist

- [ ] `personas` table created (migration 054)
- [ ] `persona_id` added to `resource_pool`
- [ ] Persona model with all fields
- [ ] WarmForge integration working
- [ ] Persona service generates realistic identities
- [ ] Domain provisioning purchases + creates mailboxes
- [ ] Buffer flow triggers on signup
- [ ] Warmup monitor runs daily
- [ ] Onboarding allocates personas + domains
- [ ] All files committed and pushed to git
