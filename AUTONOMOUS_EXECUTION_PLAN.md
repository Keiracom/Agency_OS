# Agency OS: Autonomous Execution Plan

**Mission:** Production-ready with 10 paying customers
**Owner:** Elliot (autonomous) + Dave (approvals only)
**Created:** 2026-02-06

---

## Part 1: Current State Audit

### What's Built
- [x] Backend skeleton (FastAPI on Railway)
- [x] Frontend skeleton (Next.js on Vercel)
- [x] Database schema (Supabase)
- [x] 22 MCP servers
- [x] SIEGE integrations (siege_waterfall.py, gmb_scraper.py, kaspr.py, abn_client.py)
- [x] Proxy infrastructure (215k Webshare proxies)
- [x] Email infrastructure (Salesforge + WarmForge)

### What's NOT Built
- [ ] SIEGE wired into engines (scout.py, icp_scraper.py)
- [ ] Apollo/Apify fully replaced
- [ ] SDK deprecated, Smart Prompts primary
- [ ] E2E test passing
- [ ] Onboarding flow functional
- [ ] Dashboard connected to real data
- [ ] Payment integration (Stripe)
- [ ] Voice AI working (Telnyx + Vapi)
- [ ] Maya demo system
- [ ] Customer support system

---

## Part 2: Work Streams

### Stream A: Backend Engineering
**Goal:** Fully functional API

| Task | Agent | Priority | Est. Hours |
|------|-------|----------|------------|
| A1: Wire SIEGE into scout.py | Builder | P0 | 4 |
| A2: Wire SIEGE into icp_scraper.py | Builder | P0 | 4 |
| A3: Replace Apollo calls | Builder | P0 | 6 |
| A4: Replace Apify calls | Builder | P0 | 6 |
| A5: Deprecate SDK agents | Builder | P1 | 2 |
| A6: Smart Prompts as primary | Builder | P1 | 4 |
| A7: Voice AI integration (Telnyx) | Builder | P1 | 4 |
| A8: Payment integration (Stripe) | Builder | P1 | 4 |
| A9: Webhook handlers | Builder | P2 | 3 |
| A10: API error handling audit | Auditor | P2 | 2 |

### Stream B: Frontend Engineering  
**Goal:** Production-ready dashboard

| Task | Agent | Priority | Est. Hours |
|------|-------|----------|------------|
| B1: Onboarding page (single page flow) | Builder | P0 | 4 |
| B2: Dashboard → real data connection | Builder | P0 | 6 |
| B3: Campaign creation flow | Builder | P1 | 4 |
| B4: Lead detail view | Builder | P1 | 3 |
| B5: Replies/inbox view | Builder | P1 | 3 |
| B6: Settings/integrations page | Builder | P2 | 3 |
| B7: Billing page (Stripe) | Builder | P1 | 3 |
| B8: Maya UI component | Builder | P2 | 4 |
| B9: Mobile responsiveness | Builder | P2 | 2 |
| B10: Error states + loading | Auditor | P2 | 2 |

### Stream C: Infrastructure
**Goal:** Reliable, scalable, monitored

| Task | Agent | Priority | Est. Hours |
|------|-------|----------|------------|
| C1: Prefect flows health check | Auditor | P0 | 2 |
| C2: Railway deployment pipeline | Builder | P0 | 2 |
| C3: Vercel deployment pipeline | Builder | P0 | 1 |
| C4: Database migrations (055+) | Builder | P0 | 1 |
| C5: Redis cache verification | Auditor | P1 | 1 |
| C6: Monitoring/alerting setup | Builder | P1 | 3 |
| C7: Backup/recovery plan | Builder | P2 | 2 |
| C8: Cost monitoring dashboard | Builder | P2 | 2 |

### Stream D: Testing & QA
**Goal:** Confidence before launch

| Task | Agent | Priority | Est. Hours |
|------|-------|----------|------------|
| D1: E2E test fixing | Fixer | P0 | 4 |
| D2: Integration test suite | Builder | P1 | 4 |
| D3: Load testing | Builder | P2 | 2 |
| D4: Security audit | Auditor | P1 | 3 |
| D5: ACMA compliance check | Auditor | P0 | 2 |

### Stream E: Content & Assets
**Goal:** Sales-ready materials

| Task | Agent | Priority | Est. Hours |
|------|-------|----------|------------|
| E1: Maya face (Midjourney) | Dave | P1 | 1 |
| E2: Maya video avatar setup | Builder | P1 | 3 |
| E3: Demo script templates | Builder | P1 | 2 |
| E4: Email sequence templates | Builder | P1 | 2 |
| E5: Proposal template | Builder | P1 | 1 |
| E6: Contract template | Builder | P1 | 1 |
| E7: Onboarding video scripts | Builder | P2 | 2 |

### Stream F: Sales Infrastructure
**Goal:** Can accept and onboard customers

| Task | Agent | Priority | Est. Hours |
|------|-------|----------|------------|
| F1: Stripe account setup | Dave | P0 | 1 |
| F2: Stripe integration code | Builder | P1 | 4 |
| F3: Calendar booking page | Builder | P1 | 1 |
| F4: Lead pipeline in Supabase | Builder | P1 | 2 |
| F5: Email warmup complete | Auto | P0 | Ongoing |
| F6: Telnyx AU number | Dave | P1 | 1 |

---

## Part 3: Agent Architecture

### Daily Cron Schedule (AEST)

```
05:00 - NIGHT_BUILDER: Heavy compute (scraping, enrichment, data processing)
06:00 - MORNING_BRIEFING: Status report to Dave
09:00 - DAY_BUILDER_1: Frontend/Backend tasks
12:00 - AUDITOR_RUN: Review morning builds
14:00 - DAY_BUILDER_2: Continue building
17:00 - FIXER_RUN: Address audit issues
20:00 - INTEGRATION_TEST: Run E2E suite
22:00 - END_OF_DAY: Summary to Dave, plan tomorrow
```

### Agent Roles

| Agent | Responsibility | Trigger |
|-------|---------------|---------|
| BUILDER | Write code, create files, implement features | Scheduled + on-demand |
| AUDITOR | Review code, check compliance, find bugs | After each build |
| FIXER | Address issues found by Auditor | After audits |
| ORCHESTRATOR (Elliot) | Prioritize work, assign tasks, report to Dave | Always on |
| RESEARCHER | Investigate unknowns, find solutions | When blocked |

### Task Queue (Supabase)

```sql
CREATE TABLE agent_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stream TEXT NOT NULL, -- A/B/C/D/E/F
    task_id TEXT NOT NULL, -- A1, B2, etc.
    title TEXT NOT NULL,
    description TEXT,
    priority INT NOT NULL, -- 0=P0, 1=P1, 2=P2
    status TEXT DEFAULT 'pending', -- pending/in_progress/review/done/blocked
    assigned_agent TEXT,
    estimated_hours DECIMAL,
    actual_hours DECIMAL,
    blocked_by TEXT[], -- task IDs this depends on
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    notes TEXT
);
```

---

## Part 4: Dave's One-Time Setup

### Accounts to Create
- [ ] Telnyx account + ID verification + AU mobile number
- [ ] Stripe account (connect to Keiracom ABN)
- [ ] ABN Lookup GUID (free: https://abr.business.gov.au/Tools/WebServices)
- [ ] Midjourney (for Maya face generation)
- [ ] HeyGen or Synthesia account (for Maya video)
- [ ] Cal.com or Calendly (for demo booking)

### Credentials to Provide
```
TELNYX_API_KEY=
TELNYX_PHONE_NUMBER_ID=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
ABN_LOOKUP_GUID=
HEYGEN_API_KEY=
CALENDLY_API_KEY=
```

### One-Time Actions
- [ ] Run migration 055 in Supabase
- [ ] Generate Maya face in Midjourney
- [ ] Record 30-second intro video for Maya cloning
- [ ] Set spending cap amount (e.g., $2000 AUD/month)
- [ ] Approve contract template
- [ ] Approve pricing ($2,500 Ignition tier)

---

## Part 5: Success Metrics

### Week 1
- [ ] SIEGE fully integrated
- [ ] E2E test passing
- [ ] Onboarding flow works

### Week 2
- [ ] Dashboard shows real data
- [ ] Payment flow works
- [ ] Voice AI makes test call

### Week 3
- [ ] Maya demo system functional
- [ ] 50 leads enriched and scored
- [ ] First outreach sent (dogfooding)

### Week 4
- [ ] 5+ demo calls booked
- [ ] First proposal sent
- [ ] Iterate based on feedback

### Week 6-8
- [ ] 10 paying customers
- [ ] $25K MRR
- [ ] Dave can quit if he wants

---

## Part 6: Escalation Protocol

### I Handle Autonomously
- All coding/building
- All testing
- All deployment (with rollback ready)
- All outreach/follow-up
- All scheduling
- Spending under daily cap

### I Alert Dave (Telegram)
- Contract ready for signature
- Spending approaching cap
- Critical system failure
- Customer complaint
- Strategic decision needed
- Weekly progress report

### Dave Handles
- Final contract signatures
- Payment disputes
- High-stakes demos (until Maya ready)
- Press/PR
- Legal questions

---

## Part 7: Immediate Next Steps

### Tonight (Now)
1. Create task queue table in Supabase
2. Set up first cron jobs
3. Prioritize P0 tasks
4. Start SIEGE Phase 2 (wire integrations)

### Tomorrow
1. Dave: Start account setups (Telnyx, Stripe, ABN)
2. Elliot: Continue backend integration
3. Evening: First full autonomous cycle

### This Week
1. Complete Streams A + C (Backend + Infra)
2. E2E test passing
3. Daily cron cycle running

---

*Plan created by Elliot. Ready for autonomous execution upon Dave's approval.*
