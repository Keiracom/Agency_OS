# Agency OS Staffing Plan & Org Structure (REVISED)

**Document Type:** Organizational Planning  
**Version:** 2.0  
**Date:** January 2026  
**Prepared By:** Duncan Lennox, General Manager  
**Revision Note:** Engineering hire moved earlier per CEO feedback (non-technical founder)
**Currency:** AUD (Australian Dollars)

---

## Executive Summary (Revised)

Dave,

You're right. I was thinking like we had a technical co-founder — we don't.

**The Reality:**
- You built this with AI agents, which is impressive
- But AI agents can't be on-call at 2am when Twilio's API changes
- They can't hop on a call with a frustrated customer to debug their webhook
- They can't proactively monitor for security vulnerabilities
- They can't make judgment calls about technical debt

**Revised Recommendation:**
- **Engineer moves from M19 → M3** (before first paying customer)
- This is your most critical hire, not CS Lead
- Total Y1 headcount: 5 (was 4)
- Total Y2 headcount: 11 (unchanged)

**The Engineer Profile We Need:**
- Full-stack, can work autonomously
- Comfortable with AI-assisted development (works WITH your agent pipeline)
- Python + TypeScript (your stack)
- API integration experience (critical)
- Startup mentality — will do whatever's needed

Let me revise the entire plan.

---

## Part 1: Revised Y1 Staffing Plan

### 1.1 Y1 Hiring Timeline (REVISED)

| Month | Role | Location | Type | Monthly Cost | Priority |
|-------|------|----------|------|--------------|----------|
| M1-M2 | Founder (Dave) | AU | Full-time | $0 | — |
| **M3** | **Engineer (Full-Stack)** | **Poland/Ukraine** | **Full-time** | **$7,000** | **CRITICAL** |
| **M4** | **CS Lead** | **AU Remote** | **Full-time** | **$9,000** | **HIGH** |
| **M6** | **Tech Support** | **Philippines** | **Full-time** | **$2,500** | **MEDIUM** |
| **M9** | **Marketing Coordinator** | **Philippines** | **Full-time** | **$2,000** | **MEDIUM** |

### 1.2 Why Engineer at M3 (Not M19)

| Without Engineer | With Engineer |
|------------------|---------------|
| You debug production issues | Engineer debugs, you focus on sales |
| AI agents make changes, you hope they work | Engineer reviews AI output, ensures quality |
| API provider changes = panic | Engineer handles integrations proactively |
| Security vulnerabilities = unknown | Engineer monitors and patches |
| Customer asks for feature = "let me try" | Engineer scopes and delivers |
| 2am outage = you wake up | Engineer on-call rotation |
| Technical debt compounds | Engineer manages tech health |

**Bottom line:** You can sell without a CS Lead for a few months. You cannot run a SaaS without engineering support when you're non-technical.

### 1.3 Engineer Role Description (M3)

#### Full-Stack Engineer — Eastern Europe (Remote)

| Attribute | Detail |
|-----------|--------|
| **Location** | Poland, Ukraine, or Romania (remote) |
| **Salary** | $84,000/yr AUD (~$7,000/mo) |
| **Reports to** | CEO (Dave) |
| **Start** | M3 (before first paying customer) |

**Why Eastern Europe:**
- Strong technical talent pool
- Cost-effective ($7K vs $15K+ for AU/US)
- Good timezone overlap with AU (6-8 hours)
- Excellent English in tech sector
- Culture of autonomous work

**Responsibilities:**
- Production support and bug fixes (PRIMARY)
- Monitor system health, uptime, errors
- Handle API integration issues
- Review and refine AI-generated code
- Implement high-priority feature requests
- Security patches and updates
- On-call rotation (shared with you initially)
- Document technical decisions

**Profile:**
- 4+ years full-stack experience
- **Python** (FastAPI, async) — REQUIRED
- **TypeScript/React** — REQUIRED
- PostgreSQL, Redis, Supabase
- API integration experience (REST, webhooks)
- Comfortable with AI coding assistants
- Can work autonomously with minimal supervision
- Startup experience preferred
- Strong written English

**Interview Focus:**
- Live debugging exercise
- API integration scenario
- "How would you handle a 2am production outage?"
- Code review of AI-generated code sample

---

### 1.4 Revised Y1 Monthly Staffing Costs

| Month | Headcount | Roles | Monthly Cost | Cumulative |
|-------|-----------|-------|--------------|------------|
| M1 | 1 | Founder | $0 | $0 |
| M2 | 1 | Founder | $0 | $0 |
| M3 | 2 | + Engineer | $7,000 | $7,000 |
| M4 | 3 | + CS Lead | $16,000 | $23,000 |
| M5 | 3 | — | $16,000 | $39,000 |
| M6 | 4 | + Tech Support | $18,500 | $57,500 |
| M7 | 4 | — | $18,500 | $76,000 |
| M8 | 4 | — | $18,500 | $94,500 |
| M9 | 5 | + Marketing | $20,500 | $115,000 |
| M10 | 5 | — | $20,500 | $135,500 |
| M11 | 5 | — | $20,500 | $156,000 |
| M12 | 5 | — | $20,500 | $176,500 |

**Y1 Total Staffing: $176,500** (was $106,500)
**Increase: +$70,000**

### 1.5 Revised Y1 Org Chart (M12)

```
                    ┌─────────────────┐
                    │   CEO (Dave)    │
                    │   Strategy,     │
                    │   Sales, Vision │
                    └────────┬────────┘
                             │
     ┌───────────────────────┼───────────────────────┐
     │                       │                       │
┌────▼────┐           ┌──────▼──────┐         ┌─────▼─────┐
│Engineer │           │  CS Lead    │         │  Marketing│
│(Poland) │           │  (AU)       │         │  (PH)     │
│$7,000/mo│           │  $9,000/mo  │         │  $2,000/mo│
│         │           │             │         │           │
│• Bugs   │           │• Onboarding │         │• Content  │
│• APIs   │           │• Retention  │         │• Social   │
│• Monitor│           │• Upsells    │         │• Outreach │
└─────────┘           └──────┬──────┘         └───────────┘
                             │
                      ┌──────▼──────┐
                      │ Tech Support│
                      │ (PH)        │
                      │ $2,500/mo   │
                      │             │
                      │• Tier 1 Tix │
                      │• Docs       │
                      └─────────────┘
```

---

## Part 2: Revised Y2 Staffing Plan

### 2.1 Y2 Hiring Timeline (REVISED)

Since we now have an engineer from M3, the M19 hire becomes a **second engineer** for scale:

| Month | Role | Location | Monthly Cost | Rationale |
|-------|------|----------|--------------|-----------|
| **M13** | **US CSM** | USA Remote | $12,000 | USA launch |
| **M15** | **Tech Support (US hrs)** | Colombia | $3,500 | US coverage |
| **M16** | **UK CSM** | UK Remote | $10,000 | UK launch |
| **M18** | **SDR** | South Africa | $4,000 | Scale outbound |
| **M19** | **Engineer #2** | Poland/Ukraine | $7,000 | Scale engineering |
| **M21** | **Tech Support (UK hrs)** | South Africa | $3,000 | UK coverage |
| **M24** | **Ops Manager** | Philippines | $3,500 | Operations |

### 2.2 Engineering Team Evolution

| Period | Engineers | Capacity | Focus |
|--------|-----------|----------|-------|
| M3-M18 | 1 | Maintenance + small features | Stability, integrations |
| M19-M24 | 2 | Maintenance + medium features | New channels, scale |
| Y3+ | 3-4 | Full product development | Platform expansion |

**Engineer #2 Profile (M19):**
- Can be more junior (3+ years)
- Same stack (Python, TypeScript)
- Focus on feature development
- Engineer #1 becomes tech lead

### 2.3 Revised Y2 Monthly Staffing Costs

| Month | Headcount | New Hire | Monthly Cost | Y2 Cumulative |
|-------|-----------|----------|--------------|---------------|
| M13 | 6 | US CSM | $32,500 | $32,500 |
| M14 | 6 | — | $32,500 | $65,000 |
| M15 | 7 | Tech Support (COL) | $36,000 | $101,000 |
| M16 | 8 | UK CSM | $46,000 | $147,000 |
| M17 | 8 | — | $46,000 | $193,000 |
| M18 | 9 | SDR | $50,000 | $243,000 |
| M19 | 10 | Engineer #2 | $57,000 | $300,000 |
| M20 | 10 | — | $57,000 | $357,000 |
| M21 | 11 | Tech Support (SA) | $60,000 | $417,000 |
| M22 | 11 | — | $60,000 | $477,000 |
| M23 | 11 | — | $60,000 | $537,000 |
| M24 | 12 | Ops Manager | $63,500 | $600,500 |

**Y2 Total Staffing: $600,500** (was $522,500)
**Increase: +$78,000**

### 2.4 Revised Y2 Org Chart (M24)

```
                              ┌─────────────────┐
                              │   CEO (Dave)    │
                              │   Strategy,     │
                              │   Sales, Vision │
                              └────────┬────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        │                              │                              │
┌───────▼───────┐             ┌────────▼────────┐            ┌───────▼───────┐
│  Engineering  │             │ Customer Success│            │  Operations   │
│               │             │                 │            │               │
└───────┬───────┘             └────────┬────────┘            └───────┬───────┘
        │                              │                             │
   ┌────┴────┐              ┌──────────┼──────────┐           ┌──────┴──────┐
   │         │              │          │          │           │             │
┌──▼──┐   ┌──▼──┐        ┌──▼──┐   ┌───▼───┐  ┌───▼───┐   ┌───▼───┐    ┌───▼───┐
│Eng 1│   │Eng 2│        │CS   │   │US CSM │  │UK CSM │   │Ops Mgr│    │Mkt    │
│(PL) │   │(PL) │        │Lead │   │(USA)  │  │(UK)   │   │(PH)   │    │Coord  │
│$7K  │   │$7K  │        │(AU) │   │$12K   │  │$10K   │   │$3.5K  │    │(PH)   │
│Lead │   │Dev  │        │$9K  │   │       │  │       │   │       │    │$2K    │
└─────┘   └─────┘        └──┬──┘   └───────┘  └───────┘   └───────┘    └───────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
         ┌──▼──┐         ┌──▼──┐         ┌──▼──┐         ┌──────┐
         │Tech │         │Tech │         │Tech │         │ SDR  │
         │Supp │         │Supp │         │Supp │         │ (SA) │
         │(PH) │         │(COL)│         │(SA) │         │ $4K  │
         │$2.5K│         │$3.5K│         │$3K  │         │      │
         └─────┘         └─────┘         └─────┘         └──────┘
```

**Y2 End: 12 employees (was 11), $63,500/mo**

---

## Part 3: Updated Financial Impact

### 3.1 Y1 P&L Impact (Revised)

| Line Item | Previous | Revised | Delta |
|-----------|----------|---------|-------|
| Revenue | $1,798,500 | $1,798,500 | — |
| COGS | $551,286 | $551,286 | — |
| **Staffing** | **$106,500** | **$176,500** | **+$70,000** |
| Other OpEx | $74,570 | $74,570 | — |
| **Net Profit** | $1,066,144 | **$995,644** | -$70,000 |
| Ad Spend (70%) | $746,301 | $696,951 | -$49,350 |
| Founder Draw | $159,922 | $149,347 | -$10,575 |
| Retained | $159,922 | $149,347 | -$10,575 |

### 3.2 Y2 P&L Impact (Revised)

| Line Item | Previous | Revised | Delta |
|-----------|----------|---------|-------|
| Revenue | $6,673,000 | $6,673,000 | — |
| COGS | $2,357,265 | $2,357,265 | — |
| **Staffing** | **$522,500** | **$600,500** | **+$78,000** |
| Other OpEx | $419,498 | $419,498 | — |
| **Net Profit** | $3,397,737 | **$3,319,737** | -$78,000 |
| Ad Spend (70%) | $2,378,416 | $2,323,816 | -$54,600 |
| Founder Draw | $509,660 | $497,961 | -$11,699 |
| Retained | $509,660 | $497,961 | -$11,699 |

### 3.3 Two-Year Summary (Revised)

| Metric | Y1 | Y2 | Total |
|--------|----|----|-------|
| Revenue | $1,798,500 | $6,673,000 | **$8,471,500** |
| COGS | $551,286 | $2,357,265 | $2,908,551 |
| **Staffing** | **$176,500** | **$600,500** | **$777,000** |
| Other OpEx | $74,570 | $419,498 | $494,068 |
| **Net Profit** | **$995,644** | **$3,319,737** | **$4,315,381** |
| Ad Spend | $696,951 | $2,323,816 | $3,020,767 |
| Founder Draw | $149,347 | $497,961 | **$647,308** |
| Retained | $149,347 | $497,961 | **$647,308** |

---

## Part 4: Engineer Hiring Playbook

### 4.1 Where to Find Eastern European Engineers

| Platform | Best For | Notes |
|----------|----------|-------|
| **Lemon.io** | Pre-vetted senior devs | $5K-10K/mo, fast matching |
| **Turing.com** | AI-vetted engineers | Good quality control |
| **Arc.dev** | Remote developers | Strong vetting process |
| **LinkedIn** | Direct sourcing | Search Poland/Ukraine + Python |
| **Upwork** | Trial/contract first | Test before full-time |
| **TopTal** | Top 3% claim | Expensive but quality |

### 4.2 Interview Process

**Stage 1: Async Technical Screen (30 min)**
- Review their GitHub/portfolio
- Send take-home: Debug a real issue from your codebase
- Evaluate: Code quality, problem-solving, communication

**Stage 2: Live Technical (60 min)**
- Live coding: API integration scenario
- System design: "How would you add a new outreach channel?"
- AI workflow: Show them your agent pipeline, get their thoughts

**Stage 3: Culture Fit (30 min)**
- Scenario: "2am, system is down, what do you do?"
- Work style: Timezone, communication preferences
- Motivation: Why a startup? Why this problem?

**Stage 4: Paid Trial (1-2 weeks)**
- Real tasks from your backlog
- Evaluate: Speed, quality, communication, autonomy
- Convert to full-time if successful

### 4.3 Compensation Benchmarks (Eastern Europe)

| Level | Poland | Ukraine | Romania |
|-------|--------|---------|---------|
| Junior (1-3 yrs) | $3,500-5,000 | $2,500-4,000 | $3,000-4,500 |
| Mid (3-5 yrs) | $5,000-7,500 | $4,000-6,000 | $4,500-6,500 |
| Senior (5+ yrs) | $7,000-10,000 | $5,500-8,000 | $6,000-8,500 |
| Lead (7+ yrs) | $9,000-12,000 | $7,000-10,000 | $8,000-11,000 |

**Our Target: Mid-Senior, $7,000/mo AUD**

### 4.4 Contract Structure

**Recommendation: Contractor → Employee**

| Phase | Duration | Structure |
|-------|----------|-----------|
| Trial | 2 weeks | Hourly contractor |
| Probation | 3 months | Monthly contractor |
| Permanent | Ongoing | Use Deel/Remote.com as EOR |

**EOR (Employer of Record) Costs:**
- Deel: $599/mo per employee
- Remote.com: $599/mo per employee
- This handles local compliance, taxes, benefits

---

## Part 5: Founder Role Evolution

### 5.1 Your Time Allocation (Before Engineer)

| Activity | % Time | Hours/Week |
|----------|--------|------------|
| Bug fixes & technical issues | 30% | 15 |
| Sales & demos | 25% | 12 |
| Customer support | 20% | 10 |
| Product decisions | 15% | 8 |
| Strategy & planning | 10% | 5 |
| **Total** | 100% | 50+ |

### 5.2 Your Time Allocation (After Engineer — M3+)

| Activity | % Time | Hours/Week |
|----------|--------|------------|
| Sales & demos | 35% | 14 |
| Strategy & planning | 25% | 10 |
| Product decisions | 20% | 8 |
| Customer relationships | 15% | 6 |
| Engineering oversight | 5% | 2 |
| **Total** | 100% | 40 |

**Key Shift:** Technical work → Engineer. You focus on revenue and vision.

---

## Part 6: Risk Mitigation

### 6.1 "What if the engineer doesn't work out?"

| Scenario | Mitigation |
|----------|------------|
| Bad hire | 2-week paid trial before committing |
| Quits suddenly | Document everything, cross-train AI agents |
| Underperforms | Clear KPIs, 3-month probation |
| Timezone issues | Require 4-hour overlap with AU |
| Communication issues | Daily async standups, weekly video calls |

### 6.2 Bus Factor

Until Y2 when we hire Engineer #2, bus factor is 1 for engineering. Mitigations:

1. **Documentation:** Engineer documents all systems, decisions, processes
2. **AI Agents:** Keep your agent pipeline functional as backup
3. **Code Quality:** Enforce PR reviews, clean code standards
4. **Knowledge Base:** Internal wiki with runbooks for common issues
5. **Contractor Network:** Have 2-3 vetted contractors on standby

---

## Part 7: Revised Recommendations

### Immediate (M1-M2)
1. ✅ Begin engineer search NOW (takes 4-6 weeks to hire well)
2. ✅ Set up accounts on Lemon.io, Arc.dev, LinkedIn
3. ✅ Prepare technical interview questions
4. ✅ Document your current architecture for handoff
5. ⏳ Begin CS Lead search M2

### M3 (Critical)
1. **Engineer starts** — highest priority hire
2. First 2 weeks: Onboarding, codebase familiarization
3. Week 3-4: Own first production issue independently
4. You shift focus to sales for Founding 20

### M4-M6
1. CS Lead starts M4
2. Engineer handles all technical support escalations
3. Tech Support (PH) starts M6
4. Engineer + Tech Support cover most issues, you focus on growth

### M7-M12
1. Marketing Coordinator starts M9
2. Engineering team stable
3. Prepare for Y2 scale (document, optimize)
4. Begin US CSM search M10

---

## Part 8: Final Staffing Summary

### Complete Hiring Timeline (Y1 + Y2)

| Month | Role | Location | Monthly | Cumulative Head |
|-------|------|----------|---------|-----------------|
| M3 | Engineer #1 | Poland | $7,000 | 2 |
| M4 | CS Lead | AU | $9,000 | 3 |
| M6 | Tech Support | Philippines | $2,500 | 4 |
| M9 | Marketing Coord | Philippines | $2,000 | 5 |
| M13 | US CSM | USA | $12,000 | 6 |
| M15 | Tech Support (US) | Colombia | $3,500 | 7 |
| M16 | UK CSM | UK | $10,000 | 8 |
| M18 | SDR | South Africa | $4,000 | 9 |
| M19 | Engineer #2 | Poland | $7,000 | 10 |
| M21 | Tech Support (UK) | South Africa | $3,000 | 11 |
| M24 | Ops Manager | Philippines | $3,500 | 12 |

### Total Staffing Investment

| Period | Staffing Cost | Employees (EOY) |
|--------|---------------|-----------------|
| Y1 | $176,500 | 5 |
| Y2 | $600,500 | 12 |
| **Total** | **$777,000** | **12** |

---

## Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| General Manager | Duncan Lennox | | |
| CEO | Dave | | |

---

**END OF STAFFING PLAN (REVISED)**

---

*"You can outsource a lot of things. You cannot outsource the person who keeps your product running."*

— Duncan
