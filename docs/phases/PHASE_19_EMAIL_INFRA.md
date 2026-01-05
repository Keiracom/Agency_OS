# Phase 19: Email Infrastructure

**Status:** 🟡 In Progress  
**Tasks:** 20  
**Decision:** InfraForge + Smartlead (NOT Instantly)

---

## Architecture

```
Agency OS Platform
      │
      ├──► InfraForge API (Domain/Mailbox Provisioning)
      │    ├── Purchase domains programmatically
      │    ├── Create mailboxes programmatically  
      │    ├── Automated DNS (SPF, DKIM, DMARC)
      │    └── Dedicated IPs per tenant ($99/month)
      │
      └──► Smartlead API (Warmup + Sending)
           ├── Add email accounts via API
           ├── Enable/configure warmup
           ├── Create campaigns
           └── Webhooks for all events
```

---

## Why Not Instantly?

| Factor | InfraForge + Smartlead | Instantly DFY |
|--------|------------------------|---------------|
| Domain Ownership | ✅ You own | ❌ Instantly owns |
| Cost (100 tenants) | ~$1,500-1,800/mo | ~$6,600-8,100/mo |
| Exit Strategy | ✅ Portable | ❌ Lock-in |

---

## Tier Infrastructure

| Tier | Domains | Mailboxes | IPs | Monthly |
|------|---------|-----------|-----|---------|
| Ignition | 2 | 3 | 1 | ~$115 |
| Velocity | 3 | 6 | 1 | ~$140 |
| Dominance | 5 | 11 | 2 | ~$320 |

---

## Tasks Overview

### 19A: InfraForge Integration (5 tasks)
- INF-001: Request API access
- INF-002: Create integration client
- INF-003: Domain provisioning
- INF-004: Mailbox creation
- INF-005: DNS monitoring

### 19B: Smartlead Integration (6 tasks)
- SML-001 to SML-006

### 19C: Bridge Orchestration (5 tasks)
- BRG-001 to BRG-005

### 19D: Testing (4 tasks)
- TST-019-1 to TST-019-4

---

## Database Schema

**Migration:** `017_email_infrastructure.sql`

Tables:
- `email_domains` — Provisioned domains
- `email_mailboxes` — Provisioned mailboxes
- `warmup_stats` — Daily warmup metrics

---

## Full Spec

See `PROJECT_BLUEPRINT_FULL_ARCHIVE.md` Phase 19 section for complete details.
