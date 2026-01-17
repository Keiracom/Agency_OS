# E2E Task Breakdown — What We're Really Testing

**Status:** In Progress
**Last Updated:** January 11, 2026
**Purpose:** Define comprehensive sub-tasks for each journey that test EVERYTHING

---

## Why This Document Exists

Previous E2E testing was **surface-level** — it tested "does the button work?" but NOT:

- Is the button wired to the correct backend?
- Is the backend actually implemented or stubbed?
- Are environment variables pointing to production?
- Is Prefect hitting self-hosted or cloud?
- Are there TODO/FIXME/pass statements hiding issues?

This document defines sub-tasks that test **both the wiring AND the functionality**.

---

## Testing Philosophy

### Every Sub-Task Has Two Parts

```
Part A: CODE & WIRING VERIFICATION
├── Read the actual source files
├── Trace the code path from trigger to completion
├── Check for incomplete implementations
├── Verify configuration is correct
└── Create missing files if needed

Part B: LIVE EXECUTION TEST
├── Execute the actual functionality
├── Observe behavior and logs
├── Compare to expected results
└── Document pass/fail
```

### What We're Looking For

| Category | Examples |
|----------|----------|
| **Missing Implementation** | TODO, FIXME, `pass`, `NotImplementedError`, stub returns |
| **Wrong Configuration** | Env vars pointing to wrong service, hardcoded dev URLs |
| **Incomplete Wiring** | API endpoint exists but doesn't call the engine |
| **Silent Failures** | Try/except that swallows errors without logging |
| **Missing Error Handling** | No try/catch, no user-friendly error messages |
| **Wrong Dependencies** | Importing from wrong layer, circular imports |
| **Missing Database** | Tables/columns referenced but don't exist |
| **Missing Files** | Code imports file that doesn't exist |

---

## Journey Structure Overview

**11 Journeys, ~136 Sub-Tasks Total**

| Journey | Name | Focus | Sub-Tasks |
|---------|------|-------|-----------|
| J0 | Infrastructure & Wiring Audit | System health before testing | 8 |
| J1 | Signup & Onboarding | New user flow | 15 |
| J2 | Campaign & Leads | Campaign creation, lead pipeline | 8 |
| J3 | Email Outreach | Salesforge/Resend, threading, warmup | 12 |
| J4 | SMS Outreach | Twilio, DNCR compliance, rate limits | 12 |
| J5 | Voice Outreach | Vapi, ElevenLabs, recordings | 13 |
| J6 | LinkedIn Outreach | HeyReach, rate limiting, connection requests | 13 |
| J7 | Reply Handling | Webhooks, intent classification, threading | 12 |
| J8 | Meeting & Deals | Calendar webhooks, deals, CRM push | 13 |
| J9 | Dashboard Validation | Metrics accuracy, real-time updates | 16 |
| J10 | Admin Dashboard | Platform-wide admin functionality | 14 |

---

## Journey Breakdown Status

| Journey | Status | Sub-Tasks Defined |
|---------|--------|-------------------|
| J0 | 🔴 Pending CEO Review | 8 (draft) |
| J1 | 🔴 Pending CEO Review | 15 (draft) |
| J2 | 🔴 Pending CEO Review | 8 (draft) |
| J3 | 🔴 Pending CEO Review | 12 (draft) |
| J4 | 🔴 Pending CEO Review | 12 (draft) |
| J5 | 🔴 Pending CEO Review | 13 (draft) |
| J6 | 🔴 Pending CEO Review | 13 (draft) |
| J7 | 🔴 Pending CEO Review | 12 (draft) |
| J8 | 🔴 Pending CEO Review | 13 (draft) |
| J9 | 🔴 Pending CEO Review | 16 (draft) |
| J10 | 🔴 Pending CEO Review | 14 (draft) |

---

## J0: Infrastructure & Wiring Audit

**Purpose:** Catch infrastructure issues BEFORE testing user flows.

| Sub-Task | What We're Really Checking |
|----------|---------------------------|
| J0.1 Railway Services | Are all 3 services deployed and healthy? Not just "exists" but actually responding? |
| J0.2 Environment Variables | Every required env var exists in Railway AND has valid value format? |
| J0.3 Prefect Configuration | Is PREFECT_API_URL pointing to self-hosted? Trace the actual code path! |
| J0.4 Database Connection | Using port 6543 (Transaction Pooler) not 5432? Pool settings correct? |
| J0.5 Integration Wiring | For EACH integration: Is the client configured? API key valid? Actually calls the API? |
| J0.6 Code Completeness | Search entire codebase for TODO, FIXME, pass, NotImplementedError |
| J0.7 Import Hierarchy | Any violations that would cause circular imports? |
| J0.8 Docker Build | Does the Dockerfile actually build? All dependencies included? |

**Why This Matters:** Found issue where Prefect was going to Cloud even though self-hosted was deployed.

---

## J1: Signup & Onboarding

**Purpose:** Test complete new user flow from landing to dashboard.

| Sub-Task | Part A: Wiring Check | Part B: Live Test |
|----------|---------------------|-------------------|
| J1.1 Login Page | Does login/page.tsx exist? Does it import Supabase correctly? | Does page render? Form elements present? |
| J1.2 Signup Validation | What validation rules in code? Match Supabase settings? | Submit invalid data, check errors |
| J1.3 User Creation | Trace: Form → Supabase Auth → What happens? | Create user, verify in auth.users |
| J1.4 Auth Callback | Read callback/route.ts — what does it do? Error handling? | Click confirm link, observe redirect |
| J1.5 Auto-Provision | Read migration 016 — trigger exists? Function complete? | Check clients/users/memberships tables |
| J1.6 Onboarding Redirect | What logic determines redirect? Middleware check? | Verify new user → /onboarding |
| J1.7 CRM Connect | Is HubSpot/Pipedrive integration implemented or stubbed? | Skip or connect, verify state |
| J1.8 Sender Profile | What fields required? Where saved? | Fill form, verify persistence |
| J1.9 Customer Import | Is CSV parsing implemented? Error handling? | Upload CSV, check parsing |
| J1.10 ICP Extraction | Full waterfall implemented? Each tier? | Submit URL, observe tier usage |
| J1.11 ICP Review | Edit functionality wired? Save to correct table? | Edit and save, verify DB |
| J1.12 LinkedIn Connect | HeyReach integration complete? Credential storage? | Enter creds, verify encrypted |
| J1.13 Webhook URL | Validation logic? Storage location? | Enter URL, test button |
| J1.14 Completion | What sets onboarding_completed? Activity logged? | Complete flow, verify state |
| J1.15 Edge Cases | Error boundaries? Session handling? | Test failures, refresh, etc. |

---

## J2: Campaign & Leads

**Purpose:** Test campaign creation and lead pipeline.

| Sub-Task | What We're Really Checking |
|----------|---------------------------|
| J2.1 Campaign List | API returns real data? Frontend handles empty state? |
| J2.2 Create Form | All fields wired to API? Validation matches backend? |
| J2.3 Lead Sourcing | Apollo integration complete? Credits tracked? |
| J2.4 Pool Assignment | lead_pool and lead_assignments tables working? Exclusivity enforced? |
| J2.5 ALS Scoring | Scorer engine complete? All signals implemented? Hot = 85+ not 80+? |
| J2.6 Deep Research | Triggers at 85+? LinkedIn scraping works? Icebreakers generated? |
| J2.7 Content Generation | Content engine complete? All channels? Personalization works? |
| J2.8 Activation | Status change triggers outreach flow? Prefect deployment exists? |

---

## J3: Email Outreach

**Purpose:** Test email channel specifically (Salesforge/Resend).

| Sub-Task | What We're Really Checking |
|----------|---------------------------|
| J3.1 TEST_MODE Email | Does email engine check TEST_MODE? Redirects to test recipient? |
| J3.2 Salesforge Integration | Client complete? API key valid? Send endpoint works? |
| J3.3 Resend Integration | Client complete? Fallback from Salesforge working? |
| J3.4 Email Threading | Message-ID headers? In-Reply-To? Thread continuity? |
| J3.5 Email Warmup | Warmup schedule tracking? Daily limit enforcement? |
| J3.6 Mailbox Health | Reputation monitoring? Auto-pause on issues? |
| J3.7 Sequence Logic | Multi-step sequences work? Timing respected? |
| J3.8 Personalization | Variables replaced? AI personalization triggers? |
| J3.9 Attachment Support | If enabled, files attached correctly? Size limits? |
| J3.10 Bounce Handling | Webhook receives bounces? Lead status updated? |
| J3.11 Unsubscribe Links | Link generated? Works when clicked? |
| J3.12 Activity Logging | Email send creates activity? All fields populated? |

---

## J4: SMS Outreach

**Purpose:** Test SMS channel specifically (Twilio).

| Sub-Task | What We're Really Checking |
|----------|---------------------------|
| J4.1 TEST_MODE SMS | Does SMS engine check TEST_MODE? Redirects to test number? |
| J4.2 Twilio Integration | Client complete? Account SID/Auth Token valid? |
| J4.3 DNCR Compliance | Do Not Call Registry check implemented? Blocks listed numbers? |
| J4.4 Rate Limiting | Per-minute limits? Per-day limits? Respects carrier rules? |
| J4.5 Message Formatting | 160 char limit handling? Unicode handling? |
| J4.6 Sender ID | From number configured? Verified with Twilio? |
| J4.7 Opt-Out Handling | STOP keyword detection? Auto-suppression? |
| J4.8 Delivery Status | Status callbacks configured? Updates lead status? |
| J4.9 Sequence Timing | SMS sequence timing different from email? |
| J4.10 Personalization | Variables replaced in SMS? Length recalculated? |
| J4.11 Error Handling | Invalid number handling? Carrier rejection handling? |
| J4.12 Activity Logging | SMS send creates activity? All fields populated? |

---

## J5: Voice Outreach

**Purpose:** Test voice channel specifically (Vapi + ElevenLabs).

| Sub-Task | What We're Really Checking |
|----------|---------------------------|
| J5.1 TEST_MODE Voice | Does voice engine check TEST_MODE? Redirects to test number? |
| J5.2 Vapi Integration | Client complete? API key valid? Agent creation works? |
| J5.3 ElevenLabs Integration | Voice cloning? Voice ID configured? Audio quality? |
| J5.4 Call Script | Script passed to Vapi? Variables replaced? |
| J5.5 Caller ID | From number configured? CNAM display? |
| J5.6 Call Scheduling | Respects business hours? Timezone handling? |
| J5.7 Voicemail Detection | AMD (Answering Machine Detection) configured? |
| J5.8 Voicemail Drop | Pre-recorded message dropped? Timing correct? |
| J5.9 Live Conversation | AI responds appropriately? Objection handling? |
| J5.10 Call Recording | Recording enabled? Storage location? |
| J5.11 Call Outcome | Outcome logged? (answered, voicemail, no answer, busy) |
| J5.12 Transfer Capability | Warm transfer to human? Transfer number configured? |
| J5.13 Activity Logging | Call creates activity? Duration logged? |

---

## J6: LinkedIn Outreach

**Purpose:** Test LinkedIn channel specifically (HeyReach).

| Sub-Task | What We're Really Checking |
|----------|---------------------------|
| J6.1 TEST_MODE LinkedIn | Does LinkedIn engine check TEST_MODE? Uses test account? |
| J6.2 HeyReach Integration | Client complete? API key valid? Campaign creation works? |
| J6.3 LinkedIn Account Link | OAuth flow? Account connected? Permissions granted? |
| J6.4 Connection Request | Request sent? Personalized note included? |
| J6.5 Rate Limiting (CRITICAL) | Daily connection limit (20-50)? Weekly limit? Monthly limit? |
| J6.6 LinkedIn Warmup | New account warmup period? Gradual increase? |
| J6.7 Profile View | Profile view before connect? Timing delay? |
| J6.8 Message After Connect | Triggered on acceptance? Delay before message? |
| J6.9 InMail (if premium) | InMail credits tracked? Fallback to connection? |
| J6.10 Sequence Logic | Multi-step LinkedIn sequence? Timing between steps? |
| J6.11 Personalization | LinkedIn-specific variables? (job title, company, mutual connections) |
| J6.12 Response Detection | HeyReach webhook? Detects replies? |
| J6.13 Activity Logging | LinkedIn action creates activity? Action type logged? |

---

## J7: Reply Handling

**Purpose:** Test inbound reply processing across all channels.

| Sub-Task | What We're Really Checking |
|----------|---------------------------|
| J7.1 Email Reply Webhook | Salesforge webhook endpoint? Authentication? Payload parsing? |
| J7.2 SMS Reply Webhook | Twilio webhook endpoint? Signature validation? |
| J7.3 Reply Analyzer | Claude integration? Intent categories correct? |
| J7.4 Sentiment Analysis | Positive/neutral/negative? Influences lead score? |
| J7.5 Objection Detection | Types identified? Strategy assigned? |
| J7.6 Thread Creation | Conversation thread created? Linked to lead? |
| J7.7 Thread Message Logging | All messages logged? Inbound and outbound? |
| J7.8 Lead Status Update | Status reflects reply? ALS boost for positive? |
| J7.9 Client Notification | Notified on hot reply? Email and in-app? |
| J7.10 Unsubscribe Handling | Detected? Lead suppressed? No further contact? |
| J7.11 Auto-Response | If enabled, appropriate response sent? |
| J7.12 Activity Logging | Reply creates activity? Intent logged? |

---

## J8: Meeting & Deals

**Purpose:** Test meeting booking and deal pipeline.

| Sub-Task | What We're Really Checking |
|----------|---------------------------|
| J8.1 Meeting Webhook | Calendly/Cal.com webhook? Authentication? Payload parsing? |
| J8.2 Meeting Creation | meetings table populated? Linked to lead and campaign? |
| J8.3 Meeting Types | Types defined? Affects deal stage? |
| J8.4 Meeting Reminder | Reminder scheduled? Sent before meeting? |
| J8.5 Deal Creation | Auto-created on meeting? deals table populated? |
| J8.6 Deal Pipeline | Stages defined? Progression logic works? |
| J8.7 Deal Value | Value estimation? Tier affects value? |
| J8.8 Downstream Outcomes | downstream_outcomes table? Meeting outcome logged? |
| J8.9 Revenue Attribution | Linked to campaign? Linked to lead source? |
| J8.10 CRM Push (HubSpot) | Deal pushed? Contact updated? |
| J8.11 CRM Push (Pipedrive) | Deal pushed? Person updated? |
| J8.12 Client Webhook | Webhook fires on meeting? Payload correct? |
| J8.13 Activity Logging | Meeting creates activity? Deal creates activity? |

---

## J9: Dashboard Validation

**Purpose:** Verify data accuracy across client UI.

| Sub-Task | What We're Really Checking |
|----------|---------------------------|
| J9.1 Page Load | Components render? No console errors? |
| J9.2 API Endpoint | Returns all required data? Response structure correct? |
| J9.3 Total Leads | Count matches database query? |
| J9.4 Hot Leads | Count where ALS >= 85? (not 80!) |
| J9.5 Warm/Cool/Cold | Each tier count accurate? |
| J9.6 Emails Sent | Count matches activities table? |
| J9.7 Meetings Booked | Count matches meetings table? |
| J9.8 Activity Feed | Recent activities? Paginated? Chronological? |
| J9.9 Campaign List | All campaigns? Status accurate? |
| J9.10 Lead List | Leads shown? ALS tiers colored correctly? |
| J9.11 Lead Detail | Click through works? All fields shown? Activity history? |
| J9.12 Real-Time Updates | New data appears without refresh? |
| J9.13 Date Filters | Filter changes counts? |
| J9.14 Campaign Filter | Scopes data to campaign? |
| J9.15 Charts | Render with real data? Accurate? |
| J9.16 Reports | Export works? Data accurate? |

---

## J10: Admin Dashboard

**Purpose:** Test platform-wide admin functionality.

| Sub-Task | What We're Really Checking |
|----------|---------------------------|
| J10.1 Access Control | is_platform_admin flag? RLS policies? Route protection? |
| J10.2 Page Load | All admin pages render? No console errors? |
| J10.3 Command Center | MRR accurate? Client count? Leads today? AI spend? |
| J10.4 System Status | Health check? Service status accurate? |
| J10.5 Client List | All clients? Tier display? Status display? |
| J10.6 Client Detail | Detail page? Client metrics? Impersonation? |
| J10.7 Revenue Metrics | MRR by tier? Churn? LTV? |
| J10.8 Platform Activity | All clients' activity? Filterable? |
| J10.9 Sentry Integration | Errors shown? Links to Sentry? |
| J10.10 AI Cost Tracking | ai_usage_logs? By client? By model? |
| J10.11 Prefect Status | Flow runs shown? Failed flow alerts? |
| J10.12 Integration Health | Status per integration? API key validation? |
| J10.13 Client Provisioning | Admin can create client? Reset password? |
| J10.14 Platform Settings | Settings page? Global config? |

---

## How Claude Code Should Use This Document

1. **Before starting a journey:** Read this document to understand what we're really testing
2. **For each sub-task:** Execute Part A (wiring) then Part B (live test)
3. **When issues found:** Log to ISSUES_FOUND.md with full context
4. **When fixes applied:** Log to FIXES_APPLIED.md with before/after
5. **When blocked:** Stop and report to CEO with options

---

## Success Criteria

E2E testing is complete when:

1. All journeys J0-J10 have defined sub-tasks (✅ Draft complete)
2. All sub-tasks have been executed (Part A + Part B)
3. All critical issues resolved
4. All fixes documented
5. System works end-to-end with real data
