# Phase 18: E2E Journey Test

**Status:** 🟡 In Progress  
**Tasks:** 47  
**Complete:** 5  
**Dependencies:** Phase 17 complete

---

## Overview

Validate the complete user journey before launch. This phase tests every touchpoint from signup to campaign execution.

---

## Task Summary

| Section | Tests | Pass | Fail | Pending |
|---------|-------|------|------|---------|
| Pre-Flight | 7 | 7 | 0 | 0 |
| M1: Signup & Onboarding | 10 | 0 | 0 | 10 |
| M2: Campaign Creation | 10 | 0 | 0 | 10 |
| M3: Email Send & Receive | 5 | 0 | 0 | 5 |
| M4: Reply Handling | 5 | 0 | 0 | 5 |
| M5: Dashboard & Analytics | 5 | 0 | 0 | 5 |
| M6: Admin Panel | 5 | 0 | 0 | 5 |
| **TOTAL** | **47** | **7** | **0** | **40** |

---

## Pre-Flight Checks ✅

| # | Test | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 1 | Backend health check | 200 OK | ✅ | `{"status":"healthy","version":"3.0.0"}` |
| 2 | Frontend loads | No console errors | ✅ | Returns 307 redirect (expected) |
| 3 | Supabase connection | Can query | ✅ | Connected, queried clients table |
| 4 | Resend API works | Can send | ✅ | Key restricted to send-only (intentional) |
| 5 | Anthropic API works | Can generate | ✅ | Claude response generated |
| 6 | Apollo API works | Can enrich | ✅ | Upgraded - full API access |
| 7 | Apify API works | Can scrape | ✅ | User: brawny_epitope |

---

## M1: Signup & Onboarding 🔴

| # | Test | Expected | Status |
|---|------|----------|--------|
| 1 | Go to /login | Login page loads | 🔴 |
| 2 | Click "Sign Up" | Signup form shows | 🔴 |
| 3 | Enter email + password | Form validates | 🔴 |
| 4 | Submit signup | Confirmation sent | 🔴 |
| 5 | Confirm email | Redirected to onboarding | 🔴 |
| 6 | Enter website URL | ICP extraction starts | 🔴 |
| 7 | Wait for extraction | Progress shown | 🔴 |
| 8 | Review ICP | Extracted data displayed | 🔴 |
| 9 | Confirm ICP | Saved to database | 🔴 |
| 10 | Redirect to dashboard | Dashboard loads | 🔴 |

---

## M2: Campaign Creation 🔴

| # | Test | Expected | Status |
|---|------|----------|--------|
| 1 | Click "New Campaign" | Form opens | 🔴 |
| 2 | Enter campaign name | Saved | 🔴 |
| 3 | Select permission mode | Dropdown works | 🔴 |
| 4 | Set channel allocation | Sliders sum to 100% | 🔴 |
| 5 | Upload leads CSV | File parsed | 🔴 |
| 6 | Preview leads | Table shows data | 🔴 |
| 7 | Click "Create" | Campaign created | 🔴 |
| 8 | View campaign detail | Page loads | 🔴 |
| 9 | Click "Start Campaign" | Status changes to active | 🔴 |
| 10 | Enrichment starts | Leads show enriched status | 🔴 |

---

## M3: Email Send & Receive 🔴

| # | Test | Expected | Status |
|---|------|----------|--------|
| 1 | Outreach flow runs | Email queued | 🔴 |
| 2 | Email sent via Resend | Activity logged | 🔴 |
| 3 | Email lands in inbox | Not in spam | 🔴 |
| 4 | Email has correct content | Personalized | 🔴 |
| 5 | Threading works | Follow-ups threaded | 🔴 |

---

## M4: Reply Handling 🔴

| # | Test | Expected | Status |
|---|------|----------|--------|
| 1 | Reply to email | Postmark webhook fires | 🔴 |
| 2 | Webhook processed | Activity created | 🔴 |
| 3 | Intent classified | Correct intent type | 🔴 |
| 4 | Lead status updated | Reflects intent | 🔴 |
| 5 | Client notified | Email/in-app notification | 🔴 |

---

## M5: Dashboard & Analytics 🔴

| # | Test | Expected | Status |
|---|------|----------|--------|
| 1 | Dashboard loads | Activity feed shows | 🔴 |
| 2 | Campaign metrics | Correct numbers | 🔴 |
| 3 | Lead list | ALS tiers color-coded | 🔴 |
| 4 | Real-time updates | New activity appears | 🔴 |
| 5 | Reports page | Charts render | 🔴 |

---

## M6: Admin Panel 🔴

| # | Test | Expected | Status |
|---|------|----------|--------|
| 1 | Admin login | Access granted | 🔴 |
| 2 | Platform metrics | Shows all clients | 🔴 |
| 3 | Client list | Can view details | 🔴 |
| 4 | Usage stats | Accurate numbers | 🔴 |
| 5 | Error logs | Sentry connected | 🔴 |

---

## Test Execution Order

```
Pre-Flight (DONE)
      │
      ▼
M1: Signup → M2: Campaign → M3: Email → M4: Reply
                                              │
                                              ▼
                                   M5: Dashboard → M6: Admin
```

---

## Blocking Issues

Track any blocking issues here:

| Issue | Blocking | Resolution | Status |
|-------|----------|------------|--------|
| — | — | — | — |

---

## Related Documentation

- **UX Audit:** `docs/audits/UX_AUDIT_2026-01-04.md`
- **Phase 17:** `docs/phases/PHASE_17_LAUNCH_PREREQ.md`
- **Testing Phase:** `docs/phases/PHASE_09_TESTING.md`
