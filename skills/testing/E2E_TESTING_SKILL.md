# SKILL.md — Phase 21: E2E Testing & Autonomous Fixing

**Skill:** E2E Testing with Autonomous Issue Resolution  
**Author:** Dave + Claude  
**Version:** 2.0  
**Updated:** January 7, 2026  
**Phase:** 21

---

## Purpose

Enable Claude Code to:
1. Run E2E test journeys (J1-J6)
2. Identify failures and root causes
3. Fix issues autonomously without getting lost
4. Verify fixes work
5. Document what was fixed

**Philosophy:** We're dogfooding — using Agency OS to test Agency OS as a real customer would. Not checkbox testing.

---

## Quick Reference

### Test Configuration

| Field | Value |
|-------|-------|
| **Test Agency** | Umped |
| **Website** | https://umped.com.au/ |
| **Test Email** | david.stephens@keiracom.com |
| **Test Phone** | +61457543392 |
| **Test LinkedIn** | https://www.linkedin.com/in/david-stephens-8847a636a/ |
| **Lead Volume** | 100 leads |
| **Email Limit** | 10-15 max (protect warmup) |

### Production URLs

| Service | URL |
|---------|-----|
| Frontend | https://agency-os-liart.vercel.app |
| Backend | https://agency-os-production.up.railway.app |
| Admin | https://agency-os-liart.vercel.app/admin |
| Health | https://agency-os-production.up.railway.app/api/v1/health |

### Journey Status

| Journey | Description | Status | Blocker |
|---------|-------------|--------|---------|
| J1 | Signup & Onboarding | 🟢 Ready | — |
| J2 | Campaign & Leads | 🟢 Ready | Stop before activation |
| J3 | Outreach Execution | 🔴 Blocked | TEST_MODE |
| J4 | Reply & Meeting | 🔴 Blocked | Needs J3 |
| J5 | Dashboard Validation | 🟢 Ready | — |
| J6 | Admin Dashboard | 🟢 Ready | — |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (Vercel)                             │
│                     https://agency-os-liart.vercel.app                  │
│                                                                         │
│   /login → /auth/callback → /onboarding → /dashboard                   │
│                                                                         │
│   Key Files:                                                            │
│   - frontend/app/auth/callback/route.ts (auth redirect logic)          │
│   - frontend/app/onboarding/* (onboarding flow)                        │
│   - frontend/app/dashboard/* (main app)                                │
│   - frontend/lib/supabase.ts (Supabase client)                         │
│   - frontend/lib/api.ts (Backend API calls)                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ API calls
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          BACKEND (Railway)                              │
│                https://agency-os-production.up.railway.app              │
│                                                                         │
│   /api/v1/health → Health check                                        │
│   /api/v1/clients/* → Client CRUD                                      │
│   /api/v1/campaigns/* → Campaign management                            │
│   /api/v1/leads/* → Lead operations                                    │
│   /api/v1/onboarding/* → Onboarding flow                               │
│                                                                         │
│   Key Files:                                                            │
│   - src/api/routes/*.py (API endpoints)                                │
│   - src/engines/*.py (Business logic)                                  │
│   - src/services/*.py (Data operations)                                │
│   - src/integrations/*.py (External APIs)                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Database queries
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         SUPABASE (Database)                             │
│                                                                         │
│   Core: clients, campaigns, leads, activities                          │
│   Phase 24: lead_pool, lead_assignments, conversation_threads,         │
│             email_events, meetings, deals                              │
│   Auth: Supabase Auth with JWT                                         │
│   RLS: Row-level security on all tables                                │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Journey Flows

### J1: Signup & Onboarding

```
User → /login
    └── Click "Sign Up"
    └── Enter email + password
    └── Supabase creates user
    └── Email confirmation sent

User → Clicks email link
    └── /auth/callback receives code
    └── Exchanges code for session
    └── Auto-provision trigger creates client record
    └── Redirect to /onboarding

User → /onboarding
    └── Step 1: CRM Connect (optional) → HubSpot/Pipedrive OAuth
    └── Step 2: Sender Profile → Name, title, LinkedIn URL
    └── Step 3: Customer Import (optional) → CRM or CSV
    └── Step 4: Website URL → ICP Extraction
        └── 5-tier scraper waterfall:
            1. URL Validation
            2. Apify Cheerio
            3. Apify Playwright
            4. Camoufox + Proxy
            5. Manual Fallback (/onboarding/manual-entry)
    └── Step 5: LinkedIn Connect (optional) → Credentials for HeyReach
    └── Step 6: Webhook URL (optional) → Meeting push

User → /dashboard
    └── Onboarding complete
```

**Key Files:**
| Component | File |
|-----------|------|
| Login page | `frontend/app/(auth)/login/page.tsx` |
| Auth callback | `frontend/app/auth/callback/route.ts` |
| Onboarding flow | `frontend/app/onboarding/page.tsx` |
| Manual entry | `frontend/app/onboarding/manual-entry/page.tsx` |
| ICP extraction API | `src/api/routes/onboarding.py` |
| Scraper waterfall | `src/engines/icp_scraper.py` |
| Auto-provision | `supabase/migrations/016_auto_provision_client.sql` |

---

### J2: Campaign & Leads

```
User → /dashboard
    └── Click "Create Campaign"
    └── Enter campaign details (name, target, channels)
    └── Save campaign

System → Lead Sourcing
    └── Apollo enriches leads matching ICP
    └── Leads added to lead_pool (50+ fields)
    └── Leads assigned to client (lead_assignments)

System → ALS Scoring
    └── All leads scored 0-100
    └── Distribution: Hot (85+), Warm (60-84), Cool (<60)

System → Deep Research (Hot leads only)
    └── Triggered automatically for ALS >= 85
    └── LinkedIn posts scraped
    └── Company news scraped
    └── Icebreakers generated

System → Content Generation
    └── Content Engine creates sequences for each channel
    └── Email, SMS, LinkedIn, Voice scripts generated

⚠️ STOP — Do not activate campaign until TEST_MODE ready
```

**Key Files:**
| Component | File |
|-----------|------|
| Campaign list | `frontend/app/dashboard/campaigns/page.tsx` |
| Campaign create | `frontend/app/dashboard/campaigns/new/page.tsx` |
| Campaign API | `src/api/routes/campaigns.py` |
| Lead pool service | `src/services/lead_pool_service.py` |
| Lead allocator | `src/services/lead_allocator_service.py` |
| Scorer engine | `src/engines/scorer.py` |
| Deep research | `src/engines/deep_research.py` |
| Content engine | `src/engines/content.py` |

---

### J3: Outreach Execution (Requires TEST_MODE)

```
⚠️ BLOCKED until TEST_MODE implemented

User → Activates campaign
    └── Campaign status → "active"

System → Pre-send validation (JIT Validator)
    └── Check: Not suppressed?
    └── Check: Not bounced?
    └── Check: Rate limit OK?
    └── Check: Warmup complete?

System → Send via each channel
    └── Email: Salesforge API → TEST_EMAIL_RECIPIENT
    └── SMS: Twilio API → TEST_SMS_RECIPIENT
    └── Voice: Vapi API → TEST_VOICE_RECIPIENT
    └── LinkedIn: HeyReach API → TEST_LINKEDIN_RECIPIENT

System → Log activity
    └── activities table updated
    └── Dashboard reflects sends
```

**Key Files:**
| Component | File |
|-----------|------|
| Email engine | `src/engines/email.py` |
| SMS engine | `src/engines/sms.py` |
| Voice engine | `src/engines/voice.py` |
| LinkedIn engine | `src/engines/linkedin.py` |
| JIT validator | `src/services/jit_validator.py` |
| Salesforge integration | `src/integrations/salesforge.py` |
| Twilio integration | `src/integrations/twilio.py` |
| Vapi integration | `src/integrations/vapi.py` |

---

### J4: Reply & Meeting (Requires J3)

```
⚠️ BLOCKED until J3 complete

User → Replies to test email
    └── "Yes, I'm interested in learning more"

System → Webhook receives reply
    └── Salesforge webhook fires
    └── POST /webhooks/salesforge/reply

System → Reply processing
    └── Reply Analyzer classifies intent
    └── Sentiment: positive
    └── Intent: interested
    └── Objections: none

System → Thread management
    └── conversation_threads record created
    └── thread_messages record added
    └── Lead status → "replied"

User → Books meeting
    └── Calendly/Cal.com webhook fires
    └── meetings table record created
    └── deals table record created
    └── Dashboard updates
```

**Key Files:**
| Component | File |
|-----------|------|
| Webhook handlers | `src/api/routes/webhooks.py` |
| Reply analyzer | `src/services/reply_analyzer.py` |
| Thread service | `src/services/thread_service.py` |
| Closer engine | `src/engines/closer.py` |
| Deal service | `src/services/deal_service.py` |
| Meeting service | `src/services/meeting_service.py` |

---

### J5: Dashboard Validation

```
User → /dashboard
    └── Overview metrics load
    └── Activity feed populates
    └── Charts render

Verify → Metrics match database
    └── Total leads = SELECT COUNT(*) FROM lead_assignments WHERE client_id = X
    └── Hot leads = SELECT COUNT(*) FROM lead_assignments WHERE als_score >= 85
    └── Emails sent = SELECT COUNT(*) FROM activities WHERE channel = 'email'
```

**Key Files:**
| Component | File |
|-----------|------|
| Dashboard page | `frontend/app/dashboard/page.tsx` |
| Dashboard API | `src/api/routes/dashboard.py` |
| Dashboard hooks | `frontend/hooks/use-dashboard.ts` |

---

### J6: Admin Dashboard

```
Admin → /admin
    └── Command Center loads
    └── KPIs display (MRR, clients, leads, AI spend)
    └── System status shows all healthy
    └── Alerts display (if any)

Admin → /admin/clients
    └── Client list shows Umped
    └── Can click into client detail

Admin → /admin/activity
    └── Global activity feed shows all sends
```

**Key Files:**
| Component | File |
|-----------|------|
| Admin layout | `frontend/app/admin/layout.tsx` |
| Admin pages | `frontend/app/admin/*.tsx` |
| Admin API | `src/api/routes/admin.py` |
| Admin hooks | `frontend/hooks/use-admin.ts` |
| Admin fetchers | `frontend/lib/api/admin.ts` |

---

## TEST_MODE Implementation

### Why Required

Without TEST_MODE, clicking "Start Campaign" will:
- Email 100 real leads
- SMS real phone numbers
- Call real people with AI voice
- Send LinkedIn messages to real profiles

This burns leads and damages reputation before launch.

### Implementation

**TEST-001: Add env vars to settings**

```python
# src/config/settings.py

class Settings(BaseSettings):
    # ... existing settings ...
    
    # Test Mode Configuration
    TEST_MODE: bool = Field(default=False, env="TEST_MODE")
    TEST_EMAIL_RECIPIENT: str = Field(
        default="david.stephens@keiracom.com",
        env="TEST_EMAIL_RECIPIENT"
    )
    TEST_SMS_RECIPIENT: str = Field(
        default="+61457543392",
        env="TEST_SMS_RECIPIENT"
    )
    TEST_VOICE_RECIPIENT: str = Field(
        default="+61457543392",
        env="TEST_VOICE_RECIPIENT"
    )
    TEST_LINKEDIN_RECIPIENT: str = Field(
        default="https://www.linkedin.com/in/david-stephens-8847a636a/",
        env="TEST_LINKEDIN_RECIPIENT"
    )
    TEST_DAILY_EMAIL_LIMIT: int = Field(
        default=15,
        env="TEST_DAILY_EMAIL_LIMIT"
    )
```

**TEST-002 to TEST-005: Add redirect to each engine**

```python
# Example: src/engines/email.py

from src.config.settings import settings
import logging

logger = logging.getLogger(__name__)

async def send_email(lead: Lead, content: EmailContent) -> SendResult:
    recipient = lead.email
    
    # TEST_MODE redirect
    if settings.TEST_MODE:
        original = recipient
        recipient = settings.TEST_EMAIL_RECIPIENT
        logger.info(f"TEST_MODE: Redirecting {original} → {recipient}")
    
    # ... rest of send logic using recipient ...
```

**TEST-006: Daily send limit safeguard**

```python
# src/services/send_limiter.py

from datetime import datetime, timedelta
from src.config.settings import settings

class SendLimiter:
    async def check_daily_limit(self, client_id: UUID) -> bool:
        """Returns True if under limit, False if exceeded."""
        if not settings.TEST_MODE:
            return True  # No limit in production
        
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0)
        
        count = await db.execute(
            select(func.count(Activity.id))
            .where(Activity.client_id == client_id)
            .where(Activity.channel == "email")
            .where(Activity.created_at >= today_start)
        )
        
        return count.scalar() < settings.TEST_DAILY_EMAIL_LIMIT
```

### Deployment

After implementing:

```bash
# Add to Railway environment
TEST_MODE=true
TEST_EMAIL_RECIPIENT=david.stephens@keiracom.com
TEST_SMS_RECIPIENT=+61457543392
TEST_VOICE_RECIPIENT=+61457543392
TEST_LINKEDIN_RECIPIENT=https://www.linkedin.com/in/david-stephens-8847a636a/
TEST_DAILY_EMAIL_LIMIT=15

# Deploy
railway up
```

---

## Common Failure Patterns & Fixes

### Category 1: Authentication

**Problem: Auth callback redirect loop**
```
Symptoms: Page refreshes endlessly after email confirmation
Root cause: Session not set or client record not found
Fix: Check auth callback error handling
File: frontend/app/auth/callback/route.ts
```

**Problem: Client not auto-provisioned**
```
Symptoms: Dashboard shows "No client found"
Root cause: Trigger not firing on auth.users insert
Fix: Verify trigger exists and function works
File: supabase/migrations/016_auto_provision_client.sql
```

### Category 2: ICP Extraction

**Problem: JSON parsing error**
```
Symptoms: "Failed to parse JSON response"
Root cause: Claude returns markdown-wrapped JSON
Fix: Strip ```json fences before parsing
File: src/agents/skills/website_parser.py
```

**Problem: Empty ICP extraction**
```
Symptoms: Extraction returns nothing, no error
Root cause: Cloudflare blocking, waterfall not progressing
Fix: Check scraper logs, verify waterfall fallthrough
File: src/engines/icp_scraper.py
```

### Category 3: API Errors

**Problem: CORS error**
```
Symptoms: Browser console shows Access-Control-Allow-Origin error
Root cause: Backend CORS not configured for frontend URL
Fix: Add frontend URL to CORS origins
File: src/main.py
```

**Problem: 401 Unauthorized**
```
Symptoms: API returns 401, user is logged in
Root cause: JWT not sent or expired
Fix: Check Authorization header, refresh token logic
File: frontend/lib/api.ts
```

### Category 4: Database

**Problem: RLS policy blocking**
```
Symptoms: Query returns empty when data exists
Root cause: RLS policy too restrictive
Fix: Check policy uses auth.uid() correctly
File: supabase/migrations/*.sql
```

---

## File Reference by Component

### Authentication
| Component | Files |
|-----------|-------|
| Login UI | `frontend/app/(auth)/login/page.tsx` |
| Auth callback | `frontend/app/auth/callback/route.ts` |
| Supabase client | `frontend/lib/supabase.ts` |
| User provisioning | `supabase/migrations/016_auto_provision_client.sql` |

### Onboarding
| Component | Files |
|-----------|-------|
| Onboarding UI | `frontend/app/onboarding/page.tsx` |
| Manual entry | `frontend/app/onboarding/manual-entry/page.tsx` |
| Onboarding API | `src/api/routes/onboarding.py` |
| ICP scraper | `src/engines/icp_scraper.py` |
| Apify integration | `src/integrations/apify.py` |

### Campaigns & Leads
| Component | Files |
|-----------|-------|
| Campaign pages | `frontend/app/dashboard/campaigns/*.tsx` |
| Campaign API | `src/api/routes/campaigns.py` |
| Lead pool | `src/services/lead_pool_service.py` |
| Lead allocator | `src/services/lead_allocator_service.py` |
| Scorer | `src/engines/scorer.py` |

### Outreach Engines
| Component | Files |
|-----------|-------|
| Email | `src/engines/email.py` |
| SMS | `src/engines/sms.py` |
| Voice | `src/engines/voice.py` |
| LinkedIn | `src/engines/linkedin.py` |
| Content | `src/engines/content.py` |
| JIT Validator | `src/services/jit_validator.py` |

### Dashboard
| Component | Files |
|-----------|-------|
| Dashboard page | `frontend/app/dashboard/page.tsx` |
| Dashboard API | `src/api/routes/dashboard.py` |
| Dashboard hooks | `frontend/hooks/use-dashboard.ts` |

### Admin
| Component | Files |
|-----------|-------|
| Admin pages | `frontend/app/admin/*.tsx` |
| Admin API | `src/api/routes/admin.py` (1,473 lines) |
| Admin hooks | `frontend/hooks/use-admin.ts` |
| Admin fetchers | `frontend/lib/api/admin.ts` |

---

## Fix Documentation Template

When fixing issues, document in this format:

```markdown
### Fix: J[X].[Step] - [Brief Description]

**Problem:** What failed
**Root Cause:** Why it failed
**Fix:** What was changed
**Files Modified:**
- file1.py
- file2.tsx
**Verified:** Yes - [how you verified]
```

---

## Escalation Rules

Stop and ask human when:
1. **Database schema change needed** — Migration affects production
2. **Credentials missing** — Need API key or secret
3. **Third-party down** — Supabase, Apollo, etc. not responding
4. **Unclear requirement** — Test expectation ambiguous
5. **Breaking change risk** — Fix might affect other features
6. **About to run J3/J4** — Confirm TEST_MODE is deployed and working

---

## Success Criteria

Phase 21 complete when:

1. ✅ J1-J6 all pass
2. ✅ No critical bugs (system doesn't crash)
3. ✅ All fixes documented
4. ✅ Edge cases handled (error states show friendly messages)
5. ✅ Performance acceptable (no operation > 10 seconds)
6. ✅ TEST_MODE verified working before any real outreach

---

*Version 2.0 — Updated to match PHASE_21_E2E_SPEC.md*
