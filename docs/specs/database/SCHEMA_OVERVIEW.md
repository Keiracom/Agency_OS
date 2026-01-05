# Database Schema Overview — Agency OS

**Database:** Supabase PostgreSQL  
**Connection:** Transaction Pooler (Port 6543)  
**Migrations Location:** `supabase/migrations/`

---

## Core Tables

| Table | Purpose | Migration | Spec |
|-------|---------|-----------|------|
| `clients` | Multi-tenant organizations | 002 | `CLIENTS_USERS.md` |
| `users` | User profiles (linked to auth.users) | 002 | `CLIENTS_USERS.md` |
| `memberships` | User-Client many-to-many with roles | 002 | `CLIENTS_USERS.md` |
| `campaigns` | Outreach campaigns | 003 | `CAMPAIGNS.md` |
| `leads` | Prospect contacts with ALS scoring | 004 | `LEADS.md` |
| `global_suppression` | Platform-wide email suppression | 004 | `LEADS.md` |
| `activities` | Activity log for all actions | 005 | `ACTIVITIES.md` |

---

## Supporting Tables

| Table | Purpose | Migration | Spec |
|-------|---------|-----------|------|
| `webhook_configs` | Client webhook endpoints | 007 | — |
| `audit_logs` | System audit trail | 008 | — |
| `email_templates` | Saved message templates | 011 | — |
| `client_portfolio` | Discovered client logos/cases | 012 | — |
| `replies` | Captured email/SMS replies | 013 | — |
| `meetings` | Booked meetings | 013 | — |

---

## Conversion Intelligence Tables (Phase 16)

| Table | Purpose | Migration | Spec |
|-------|---------|-----------|------|
| `conversion_patterns` | Learned conversion patterns | 014 | `CONVERSION_PATTERNS.md` |
| `conversion_pattern_history` | Pattern version history | 014 | `CONVERSION_PATTERNS.md` |
| `dataforseo_cache` | SEO metrics cache | 015 | — |
| `credit_transactions` | Credit usage tracking | 016 | — |

---

## Email Infrastructure Tables (Phase 19)

| Table | Purpose | Migration | Spec |
|-------|---------|-----------|------|
| `email_domains` | Provisioned email domains | 017 | `EMAIL_INFRASTRUCTURE.md` |
| `email_mailboxes` | Provisioned mailboxes | 017 | `EMAIL_INFRASTRUCTURE.md` |
| `warmup_stats` | Email warmup tracking | 017 | `EMAIL_INFRASTRUCTURE.md` |

---

## Platform Intelligence Tables (Phase 20)

| Table | Purpose | Migration | Spec |
|-------|---------|-----------|------|
| `platform_patterns` | Cross-client patterns | 018 | — |
| `platform_weights` | Platform-wide ALS weights | 018 | — |

---

## Key Enums

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

---

## RLS Helper Function

```sql
CREATE OR REPLACE FUNCTION get_user_client_ids()
RETURNS SETOF UUID AS $$
    SELECT client_id 
    FROM memberships 
    WHERE user_id = auth.uid()
    AND accepted_at IS NOT NULL
$$ LANGUAGE sql SECURITY DEFINER STABLE;
```

---

## Detailed Schema Files

| Topic | Location |
|-------|----------|
| Clients, Users, Memberships | `docs/specs/database/CLIENTS_USERS.md` |
| Campaigns | `docs/specs/database/CAMPAIGNS.md` |
| Leads & Suppression | `docs/specs/database/LEADS.md` |
| Activities | `docs/specs/database/ACTIVITIES.md` |
| Conversion Patterns | `docs/specs/database/CONVERSION_PATTERNS.md` |
| Email Infrastructure | `docs/specs/database/EMAIL_INFRASTRUCTURE.md` |

---

## Migration Order

```
001_foundation.sql          ← Enums, helper functions
002_clients_users_memberships.sql
003_campaigns.sql
004_leads_suppression.sql
005_activities.sql
006_permission_modes.sql
007_webhook_configs.sql
008_audit_logs.sql
009_rls_policies.sql
010_platform_admin.sql
011_email_template.sql
012_client_icp_profile.sql
013_replies_meetings.sql
014_conversion_intelligence.sql
015_dataforseo_cache.sql
016_credits_usage.sql
017_email_infrastructure.sql
018_platform_intelligence.sql
```
