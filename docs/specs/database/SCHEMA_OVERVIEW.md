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

## Email Infrastructure Tables (Phase 18)

| Table | Purpose | Migration | Spec |
|-------|---------|-----------|------|
| `email_domains` | Provisioned email domains | 017 | `EMAIL_INFRASTRUCTURE.md` |
| `email_mailboxes` | Provisioned mailboxes | 017 | `EMAIL_INFRASTRUCTURE.md` |
| `warmup_stats` | Email warmup tracking | 017 | `EMAIL_INFRASTRUCTURE.md` |

---

## Deep Research Tables (Phase 21)

| Table | Purpose | Migration | Spec |
|-------|---------|-----------|------|
| `lead_social_posts` | Social posts audit trail | 021 | — |
| `leads.deep_research_data` | Deep research JSONB | 021 | — |
| `leads.deep_research_run_at` | Research timestamp | 021 | — |

---

## Lead Pool Tables (Phase 24A)

| Table | Purpose | Migration | Spec |
|-------|---------|-----------|------|
| `lead_pool` | Platform-wide lead repository | 024 | `LEAD_POOL.md` |
| `lead_assignments` | Exclusive client assignments | 024 | `LEAD_POOL.md` |

---

## Content Tracking Tables (Phase 24B)

| Table | Purpose | Migration | Spec |
|-------|---------|-----------|------|
| `content_templates` | Message templates with versioning | 025 | — |
| `content_versions` | Template version history | 025 | — |
| `content_performance` | A/B test metrics per variant | 025 | — |

---

## Email Engagement Tables (Phase 24C)

| Table | Purpose | Migration | Spec |
|-------|---------|-----------|------|
| `email_events` | Open/click/bounce events | 026 | — |
| `email_links` | Link click tracking | 026 | — |

---

## Conversation Threading Tables (Phase 24D)

| Table | Purpose | Migration | Spec |
|-------|---------|-----------|------|
| `conversation_threads` | Email thread grouping | 027 | — |
| `thread_messages` | Messages within threads | 027 | — |

---

## Downstream Outcomes Tables (Phase 24E)

| Table | Purpose | Migration | Spec |
|-------|---------|-----------|------|
| `downstream_outcomes` | Deals, revenue, LTV | 028 | — |
| `outcome_milestones` | Conversion journey stages | 028 | — |

---

## CRM Push Tables (Phase 24F)

| Table | Purpose | Migration | Spec |
|-------|---------|-----------|------|
| `crm_sync_config` | CRM connection settings | 029 | — |
| `crm_sync_logs` | Sync operation history | 029 | — |
| `crm_field_mappings` | Field mapping config | 029 | — |

---

## Customer Import Tables (Phase 24G)

| Table | Purpose | Migration | Spec |
|-------|---------|-----------|------|
| `customer_imports` | Import job tracking | 030 | — |
| `import_rows` | Individual row status | 030 | — |

---

## LinkedIn Credentials Tables (Phase 24H)

| Table | Purpose | Migration | Spec |
|-------|---------|-----------|------|
| `linkedin_credentials` | LinkedIn auth storage | 031 | — |

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
CREATE TYPE pool_status AS ENUM ('available', 'assigned', 'converted', 'bounced', 'unsubscribed', 'invalid');
CREATE TYPE assignment_status AS ENUM ('active', 'released', 'converted', 'expired');
CREATE TYPE email_status_type AS ENUM ('verified', 'guessed', 'invalid', 'catch_all', 'unknown');
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
| Lead Pool | `docs/specs/database/LEAD_POOL.md` |

---

## Migration Order

```
001_foundation.sql              ← Enums, helper functions
002_clients_users_memberships.sql
003_campaigns.sql
004_leads_suppression.sql
005_activities.sql
006_permission_modes.sql
007_webhook_configs.sql
008_audit_logs.sql
009_rls_policies.sql
010_platform_admin.sql
011_fix_user_insert_policy.sql
012_client_icp_profile.sql
013_campaign_templates.sql
014_conversion_intelligence.sql
015_founding_spots.sql
016_auto_provision_client.sql
017_fix_trigger_schema.sql
021_deep_research.sql           ← Phase 21
024_lead_pool.sql               ← Phase 24A
025_content_tracking.sql        ← Phase 24B
026_email_engagement.sql        ← Phase 24C
027_conversation_threads.sql    ← Phase 24D
028_downstream_outcomes.sql     ← Phase 24E
029_crm_push.sql                ← Phase 24F
030_customer_import.sql         ← Phase 24G
031_linkedin_credentials.sql    ← Phase 24H
```

**Note:** Migrations 018-020 and 022-023 were skipped during phase renumbering.
