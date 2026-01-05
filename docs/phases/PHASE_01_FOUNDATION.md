# Phase 1: Foundation + DevOps

**Status:** ✅ Complete  
**Tasks:** 17  
**Dependencies:** None  
**Checkpoint:** CEO approval required

---

## Overview

Set up the core infrastructure: Docker, database migrations, and base integrations.

---

## Tasks

| Task ID | Task Name | Description | Files | Complexity |
|---------|-----------|-------------|-------|------------|
| DEV-001 | Dockerfile | Shared container image | `Dockerfile` | M |
| DEV-002 | Docker Compose | Local dev with 3 services | `docker-compose.yml` | M |
| DEV-003 | Dev tunnel script | ngrok for webhook testing | `scripts/dev_tunnel.sh` | S |
| DEV-004 | Webhook URL updater | Update Postmark/Twilio URLs | `scripts/update_webhook_urls.py` | S |
| DB-001 | Settings with pools | Pydantic settings, pool config | `src/config/settings.py` | M |
| DB-002 | Foundation migration | Enums, roles, base types | `supabase/migrations/001_foundation.sql` | M |
| DB-003 | Clients + Users + Memberships | Multi-tenant with team access | `supabase/migrations/002_clients_users_memberships.sql` | L |
| DB-004 | Campaigns migration | Campaigns with allocation | `supabase/migrations/003_campaigns.sql` | M |
| DB-005 | Leads + Suppression | Leads with compound uniqueness | `supabase/migrations/004_leads_suppression.sql` | L |
| DB-006 | Activities migration | Activity log with indexes | `supabase/migrations/005_activities.sql` | M |
| DB-007 | Permission modes | Autopilot/Co-Pilot/Manual | `supabase/migrations/006_permission_modes.sql` | S |
| DB-008 | Webhook configs | Client webhook endpoints | `supabase/migrations/007_webhook_configs.sql` | S |
| DB-009 | Audit logs | System audit trail | `supabase/migrations/008_audit_logs.sql` | M |
| DB-010 | RLS policies | Row-level security via memberships | `supabase/migrations/009_rls_policies.sql` | L |
| CFG-001 | Exceptions module | Custom exceptions | `src/exceptions.py` | S |
| INT-001 | Supabase integration | Async client with pool limits | `src/integrations/supabase.py` | M |
| INT-002 | Redis integration | Versioned cache, resource rate limits | `src/integrations/redis.py` | M |

---

## Key Decisions

- **Database:** Supabase PostgreSQL (Port 6543 Transaction Pooler)
- **Pool limits:** pool_size=5, max_overflow=10 per service
- **Redis:** Caching ONLY (NOT task queues)

---

## Checkpoint 1 Criteria

- [ ] Docker containers build and run
- [ ] All migrations applied successfully
- [ ] Supabase connection works (port 6543)
- [ ] Redis connection works
- [ ] RLS policies verified

---

## Database Enums Created

```sql
CREATE TYPE tier_type AS ENUM ('ignition', 'velocity', 'dominance');
CREATE TYPE subscription_status AS ENUM ('trialing', 'active', 'past_due', 'cancelled', 'paused');
CREATE TYPE membership_role AS ENUM ('owner', 'admin', 'member', 'viewer');
CREATE TYPE permission_mode AS ENUM ('autopilot', 'co_pilot', 'manual');
CREATE TYPE campaign_status AS ENUM ('draft', 'active', 'paused', 'completed');
CREATE TYPE lead_status AS ENUM ('new', 'enriched', 'scored', 'in_sequence', 'converted', 'unsubscribed', 'bounced');
CREATE TYPE channel_type AS ENUM ('email', 'sms', 'linkedin', 'voice', 'mail');
CREATE TYPE intent_type AS ENUM ('meeting_request', 'interested', 'question', 'not_interested', 'unsubscribe', 'out_of_office', 'auto_reply');
```
