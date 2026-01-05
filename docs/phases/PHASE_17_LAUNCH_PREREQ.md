# Phase 17: Launch Prerequisites

**Status:** 🟡 In Progress  
**Tasks:** 20  
**Complete:** 8  
**Dependencies:** Phases 1-16 complete

---

## Overview

Everything needed before the first paying customer. This phase focuses on collecting API credentials, validating integrations, and setting up marketing automation.

---

## Task Summary

| Section | Tasks | Complete |
|---------|-------|----------|
| 17A: API Credentials | 11 | 10 |
| 17B: Frontend Pages | 3 | 3 |
| 17C: Live Validation | 4 | 1 |
| 17D: Marketing Integrations | 2 | 0 |
| 17E: Marketing Automation | 3 | 0 |
| **TOTAL** | **23** | **14** |

---

## 17A: API Credentials

| Task | Description | Status | Priority |
|------|-------------|--------|----------|
| CRED-001 | Resend API key + domain verification | ✅ | P0 |
| CRED-002 | Anthropic API key + spend limit | ✅ | P0 |
| CRED-003 | Apollo API key | ✅ | P0 |
| CRED-004 | Apify API key | ✅ | P0 |
| CRED-005 | Twilio account + phone number | ✅ | P1 |
| CRED-006 | HeyReach API key + LinkedIn seats | ✅ | P1 |
| CRED-007 | Vapi API key + phone number link | ✅ | P1 |
| CRED-007a | ElevenLabs API key | ✅ | P1 |
| CRED-008 | ClickSend credentials (AU direct mail) | 🔴 | P2 |
| CRED-009 | DataForSEO credentials | ✅ | P1 |
| CRED-010 | v0.dev API key (UI generation) | ✅ | P1 |

---

## 17B: Frontend Missing Pages

| Task | Description | Status | Files |
|------|-------------|--------|-------|
| FE-016 | Landing page with waitlist | ✅ | `frontend/app/page.tsx` |
| FE-017 | Pricing page | ✅ | `frontend/app/(marketing)/pricing/page.tsx` |
| FE-018 | Waitlist thank you page | ✅ | `frontend/app/waitlist/thank-you/page.tsx` |

---

## 17C: Live Validation

| Task | Description | Status | Depends On |
|------|-------------|--------|------------|
| LIVE-001 | Integration health check script | ✅ | CRED-001 to CRED-004 |
| LIVE-002 | Send test email to yourself | 🔴 | CRED-001 |
| LIVE-003 | Full onboarding flow test | 🟡 | CRED-002, CRED-003, CRED-004 |
| LIVE-004 | Full campaign creation test | 🔴 | LIVE-003 |

---

## 17D: Marketing Integrations

| Task | Description | Status | Files |
|------|-------------|--------|-------|
| INT-013 | HeyGen integration | 🔴 | `src/integrations/heygen.py` |
| INT-014 | Buffer integration | 🔴 | `src/integrations/buffer.py` |

---

## 17E: Marketing Automation

| Task | Description | Status | Files |
|------|-------------|--------|-------|
| MKT-001 | HeyGen account + avatar setup | 🔴 | — |
| MKT-002 | Content automation flow (Prefect) | 🔴 | `src/orchestration/flows/marketing_automation_flow.py` |
| MKT-003 | Day 1 video script + post | 🔴 | — |

---

## 17X: Auto-Provisioning Flow (Jan 4, 2026)

| Task | Description | Status | Files |
|------|-------------|--------|-------|
| PROV-001 | Migration: auto-provision client on signup | ✅ | `supabase/migrations/016_auto_provision_client.sql` |
| PROV-002 | Auth callback: redirect based on onboarding status | ✅ | `frontend/app/auth/callback/route.ts` |
| PROV-003 | Dashboard layout: redirect to onboarding if needed | ✅ | `frontend/app/dashboard/layout.tsx` |
| PROV-004 | Skip onboarding page (testing) | ✅ | `frontend/app/onboarding/skip/page.tsx` |
| PROV-005 | Supabase export createClient alias | ✅ | `frontend/lib/supabase.ts` |

---

## Health Check Results (Jan 4, 2026)

| Service | Status | Notes |
|---------|--------|-------|
| Anthropic | ✅ | Working |
| Resend | ✅ | Working (send-only, expected) |
| Apollo | ✅ | Working (upgraded) |
| Apify | ✅ | Working |

---

## Checklist Before Phase 18

- [x] All P0 credentials collected
- [x] All P1 credentials collected
- [ ] All P2 credentials collected (ClickSend)
- [x] Landing page live
- [x] Health checks pass
- [ ] Marketing automation configured

---

## Related Documentation

- **Marketing Plan:** `docs/marketing/MARKETING_LAUNCH_PLAN.md`
- **API Checklist:** `reference/API_CREDENTIALS_CHECKLIST.md`
- **Integration Specs:** `docs/specs/integrations/`
