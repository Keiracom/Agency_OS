# Architecture Gaps — Task List

**Purpose:** Track identified gaps across all architecture documents.
**Status:** Active
**Last Updated:** 2026-01-20 (LinkedIn gaps expanded)

---

## How to Use This Document

1. Gaps identified during architecture review are logged here
2. Each gap becomes a task before implementation
3. CEO approves gap resolution before coding
4. Completed gaps are marked ✅ with implementation reference

---

## RESOURCE_POOL.md Gaps

| ID | Gap | Description | Priority | Status |
|----|-----|-------------|----------|--------|
| RP-001 | **Stripe integration** | Payment confirmed webhook triggers resource allocation | HIGH | 🔴 |
| RP-002 | **Admin UI for pool** | Dashboard to view pool status, add resources | HIGH | 🔴 |
| RP-003 | **Capacity alerts** | Notify admin when pool buffer < 40% | HIGH | 🔴 |
| RP-004 | **InfraForge API integration** | Auto-purchase domains when buffer low | HIGH | 🔴 |
| RP-005 | **Mailbox creation flow** | 2 mailboxes per domain via InfraForge/Salesforge | MEDIUM | 🔴 |
| RP-006 | **Warmup initiation** | New domains auto-start warmup in Warmforge | MEDIUM | 🔴 |
| RP-007 | **Phone number provisioning** | Twilio API for auto-purchasing numbers | MEDIUM | 🔴 |
| RP-008 | **LinkedIn seat management** | Client connects their own seats via white-label UI | LOW | 🔴 |
| RP-009 | **Resource health monitoring** | Track domain reputation, bounce rates | MEDIUM | 🔴 |
| RP-010 | **Churn release automation** | 30-day hold then release resources | LOW | 🔴 |

---

## EMAIL_DISTRIBUTION.md Gaps

| ID | Gap | Description | Priority | Status |
|----|-----|-------------|----------|--------|
| ED-001 | **Timezone engine** | Australian state-level timezone detection | HIGH | 🔴 |
| ED-002 | **9-11 AM send window** | Enforce recipient-local send time | HIGH | 🔴 |
| ED-003 | **Domain capacity service** | Track usage with 10% response buffer | HIGH | 🔴 |
| ED-004 | **Domain health service** | good/warning/critical status + actions | HIGH | 🔴 |
| ED-005 | **Health-based limit reduction** | 35/day at warning, 0 at critical | MEDIUM | 🔴 |
| ED-006 | **Reply-to-reply SDK flow** | When lead replies, SDK generates response | MEDIUM | 🔴 |
| ED-007 | **Mailbox rotation logic** | Round-robin across client's mailboxes | LOW | 🔴 |
| ED-008 | **Persona system** | `client_personas` table + assignment to mailboxes | HIGH | 🔴 |
| ED-009 | **Client branding** | `clients.branding` JSONB field for signature data | HIGH | 🔴 |
| ED-010 | **Signature engine** | Generate branded signatures from client + persona | HIGH | 🔴 |
| ED-011 | **Display name generation** | "{First} from {Company}" format | HIGH | 🔴 |
| ED-012 | **Neutral pool domains** | Rename from agencyxos-X to neutral names | MEDIUM | 🔴 |

---

## SMS_DISTRIBUTION.md Gaps

| ID | Gap | Description | Priority | Status |
|----|-----|-------------|----------|--------|
| SM-001 | **DNCR batch wash at enrichment** | Add `on_dncr`, `dncr_checked_at` fields, wash during enrichment | HIGH | 🔴 |
| SM-002 | **DNCR quarterly re-wash flow** | Prefect flow to re-wash leads older than 90 days | MEDIUM | 🔴 |
| SM-003 | **SMS send window** | 9 AM - 5 PM recipient local time | HIGH | 🔴 |
| SM-004 | **SMS reply webhook service** | Route SMS replies to reply_agent | HIGH | 🔴 |
| SM-005 | **Reply agent SMS support** | Generate 160-char responses for SMS channel | MEDIUM | 🔴 |
| SM-006 | **SMS client branding** | Persona name + company in message content | MEDIUM | 🔴 |
| SM-007 | **Character count enforcement** | Validate < 160 chars GSM-7 before send | LOW | 🔴 |

---

## VOICE_DISTRIBUTION.md Gaps

| ID | Gap | Description | Priority | Status |
|----|-----|-------------|----------|--------|
| VO-001 | **Vapi full integration** | Call initiation with KB | HIGH | 🔴 |
| VO-002 | **Call outcome handling** | answered/voicemail/busy/no_answer flows | HIGH | 🔴 |
| VO-003 | **Retry service** | Busy = 2hr later, no_answer = next day | HIGH | 🔴 |
| VO-004 | **Voicemail script** | Persona-branded VM with email reference | MEDIUM | 🔴 |
| VO-005 | **Recording disclosure** | "This call may be recorded" at start | HIGH | 🔴 |
| VO-006 | **Recording retention** | 90-day auto-delete, flag for keep | MEDIUM | 🔴 |
| VO-007 | **Phone auto-provisioning** | Twilio API + AU regulatory bundle | HIGH | 🔴 |
| VO-008 | **Voice warmup** | 1-week ramp (20→30→40→50/day) | MEDIUM | 🔴 |
| VO-009 | **DNCR integration** | Use same cached check as SMS | HIGH | 🔴 |
| VO-010 | **Lunch skip** | Don't call 12-1 PM recipient time | LOW | 🔴 |

---

## LINKEDIN_DISTRIBUTION.md Gaps

**Spec Status:** ✅ Complete (2026-01-20) — See `distribution/LINKEDIN_DISTRIBUTION.md`

| ID | Gap | Description | Priority | Status |
|----|-----|-------------|----------|--------|
| LI-001 | **`linkedin_seats` table** | Multi-seat support per client (4/7/14 per tier) | HIGH | 🔴 |
| LI-002 | **`linkedin_connections` table** | Track pending/accepted/ignored/declined/withdrawn | HIGH | 🔴 |
| LI-003 | **White-label auth flow** | Direct API connection (no Unipile branding visible) | HIGH | 🔴 |
| LI-004 | **2FA handling** | Handle 2FA code entry in Agency OS UI | HIGH | 🔴 |
| LI-005 | **Seat warmup enforcement** | 2-week ramp (5→10→15→20/day) | HIGH | 🔴 |
| LI-006 | **Profile view before connect** | View profile 10-30 min before connection request | MEDIUM | 🔴 |
| LI-007 | **Connection note logic** | Include note only if ≥2 mutual connections | MEDIUM | 🔴 |
| LI-008 | **Post-accept messaging** | Auto-send message 3-5 days after accept | MEDIUM | 🔴 |
| LI-009 | **Weekly limit enforcement** | 80 connections/week cap | MEDIUM | 🔴 |
| LI-010 | **Tier-based gating** | Only ALS ≥ 35 (Cool+) get LinkedIn | MEDIUM | 🔴 |
| LI-011 | **Quota tracking** | Track manual + automated activity against daily limit | MEDIUM | 🔴 |
| LI-012 | **14-day ignored timeout** | Mark pending connections as ignored after 14 days | LOW | 🔴 |
| LI-013 | **30-day stale withdrawal** | Withdraw pending requests after 30 days | LOW | 🔴 |
| LI-014 | **Health monitoring** | Accept rate tracking, reduce limit at <30% | MEDIUM | 🔴 |
| LI-015 | **Restriction detection** | Handle provider restriction webhooks, pause seat | MEDIUM | 🔴 |
| LI-016 | **Weekend reduction** | Saturday 50%, Sunday off | LOW | 🔴 |
| LI-017 | **Reply routing** | Route LinkedIn messages to unified reply_agent | HIGH | 🔴 |
| LI-018 | **Persona-to-seat mapping** | Link personas to LinkedIn seats | MEDIUM | 🔴 |

---

## AUTOMATED_DISTRIBUTION_DEFAULTS.md Gaps

| ID | Gap | Description | Priority | Status |
|----|-----|-------------|----------|--------|
| AD-001 | **Sequence generator service** | Auto-create 5-step default sequence | HIGH | 🔴 |
| AD-002 | **Remove user sequence config** | Simplify campaign creation form | MEDIUM | 🔴 |
| AD-003 | **Channel fallback logic** | If LinkedIn unavailable, skip step | MEDIUM | 🔴 |
| AD-004 | **ALS-based channel gating** | Enforce channel access per score | HIGH | 🔴 |

---

## SDK_AND_CONTENT_ARCHITECTURE.md Gaps

| ID | Gap | Description | Priority | Status |
|----|-----|-------------|----------|--------|
| SDK-001 | **Run migration 040** | Drop A/B testing tables in production | LOW | 🔴 |
| SDK-002 | **Schedule stale refresh flow** | daily_outreach_prep_flow cron | MEDIUM | 🔴 |

---

## SYSTEM-WIDE Gaps (Not Covered by Existing Docs)

| ID | Gap | Description | Priority | Status |
|----|-----|-------------|----------|--------|
| SYS-001 | **Onboarding architecture** | ICP → sourcing → enrichment → scoring flow | HIGH | 🔴 |
| SYS-002 | **Scoring architecture** | ALS formula, tier thresholds, signal weights | MEDIUM | 🔴 |
| SYS-003 | **Reply handling architecture** | Intent classification → SDK response → routing | HIGH | ✅ `REPLY_ARCHITECTURE.md` |
| SYS-004 | **Meeting architecture** | Calendar booking → deal creation → CRM push | MEDIUM | 🔴 |
| SYS-005 | **Billing architecture** | Stripe subscription → tier → resource allocation | HIGH | 🔴 |
| SYS-006 | **Admin dashboard architecture** | What admins see and can do | MEDIUM | 🔴 |
| SYS-007 | **Client dashboard architecture** | What clients see (metrics, leads, campaigns) | MEDIUM | 🔴 |
| SYS-008 | **Webhook architecture** | All inbound webhooks, routing, handling | MEDIUM | 🔴 |
| SYS-009 | **Error handling architecture** | Sentry integration, alerting, recovery | LOW | 🔴 |
| SYS-010 | **Multi-tenancy architecture** | RLS enforcement, data isolation | HIGH | 🔴 |

---

## Summary by Priority

| Priority | Count | Examples |
|----------|-------|----------|
| **HIGH** | 31 | Resource pool, timezone, personas, DNCR batch wash, SMS reply, Vapi, LinkedIn auth |
| **MEDIUM** | 27 | Health monitoring, reply agent SMS, neutral domains, dashboards, LinkedIn note logic |
| **LOW** | 9 | Character count, retry logic, mailbox rotation, LinkedIn weekend reduction |

---

## Next Actions

1. CEO reviews this gap list
2. CEO prioritizes / adds / removes gaps
3. Each gap gets assigned to an architecture doc
4. Architecture docs updated with gap resolutions
5. Then implementation begins

---

## Status Legend

| Symbol | Meaning |
|--------|---------|
| 🔴 | Not started |
| 🟡 | In progress |
| ✅ | Complete |
