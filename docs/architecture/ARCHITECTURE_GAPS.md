# Architecture Gaps — Task List

**Purpose:** Track identified gaps across all architecture documents.
**Status:** Active
**Last Updated:** 2026-01-20

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
| RP-008 | **LinkedIn seat provisioning** | Unipile API for seat management | LOW | 🔴 |
| RP-009 | **Resource health monitoring** | Track domain reputation, bounce rates | MEDIUM | 🔴 |
| RP-010 | **Churn release automation** | 30-day hold then release resources | LOW | 🔴 |

---

## EMAIL_DISTRIBUTION.md Gaps

| ID | Gap | Description | Priority | Status |
|----|-----|-------------|----------|--------|
| ED-001 | **Warmup scheduler service** | Gradual limits based on domain age | HIGH | 🔴 |
| ED-002 | **Recipient timezone detection** | Enrich with company HQ timezone | HIGH | 🔴 |
| ED-003 | **9-11 AM send window** | Enforce recipient-local send time | HIGH | 🔴 |
| ED-004 | **Domain health dashboard** | Bounce rate, complaint rate per domain | MEDIUM | 🔴 |
| ED-005 | **Reply-to-reply SDK flow** | When lead replies, SDK generates response | MEDIUM | 🔴 |
| ED-006 | **Mailbox rotation logic** | Round-robin across client's mailboxes | LOW | 🔴 |

---

## SMS_DISTRIBUTION.md Gaps

| ID | Gap | Description | Priority | Status |
|----|-----|-------------|----------|--------|
| SM-001 | **DNCR check before send** | Wire dncr.py into sms.py | HIGH | 🔴 |
| SM-002 | **DNCR batch washing** | Pre-wash lead list during enrichment | MEDIUM | 🔴 |
| SM-003 | **SMS reply handling** | Route SMS replies to reply_agent | MEDIUM | 🔴 |
| SM-004 | **Character count enforcement** | Warn if > 160 chars GSM-7 | LOW | 🔴 |

---

## VOICE_DISTRIBUTION.md Gaps

| ID | Gap | Description | Priority | Status |
|----|-----|-------------|----------|--------|
| VO-001 | **Vapi full integration** | Call initiation with KB | HIGH | 🔴 |
| VO-002 | **Call outcome handling** | answered/voicemail/busy/no_answer flows | HIGH | 🔴 |
| VO-003 | **Recording retrieval** | Store recordings from Twilio | MEDIUM | 🔴 |
| VO-004 | **Voicemail detection** | Leave VM or skip per settings | MEDIUM | 🔴 |
| VO-005 | **Business hours check** | Don't call outside 9-5 recipient time | HIGH | 🔴 |
| VO-006 | **Call retry logic** | Busy/no_answer → retry after cooling | LOW | 🔴 |

---

## LINKEDIN_DISTRIBUTION.md Gaps

| ID | Gap | Description | Priority | Status |
|----|-----|-------------|----------|--------|
| LI-001 | **Seat pool allocation** | Assign seats from pool to client | HIGH | 🔴 |
| LI-002 | **Connection tracking** | Track pending/accepted/ignored | HIGH | 🔴 |
| LI-003 | **Post-accept messaging** | Auto-send message 2 days after accept | MEDIUM | 🔴 |
| LI-004 | **Weekly limit enforcement** | 80 connections/week cap | MEDIUM | 🔴 |
| LI-005 | **Tier-based allocation** | Only Cool/Warm/Hot get LinkedIn | MEDIUM | 🔴 |
| LI-006 | **Account health monitoring** | Detect restrictions/flags | LOW | 🔴 |

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
| SYS-003 | **Reply handling architecture** | Intent classification → SDK response → routing | HIGH | 🔴 |
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
| **HIGH** | 18 | Resource pool, warmup scheduler, DNCR, Vapi |
| **MEDIUM** | 16 | Health monitoring, reply handling, dashboards |
| **LOW** | 8 | Character count, retry logic, archive |

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
