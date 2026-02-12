# MEMORY.md — DEPRECATED

**Migrated to Supabase `elliot_internal.memories` on 2026-02-12.**
**Read-only reference only. Do not add new entries here.**

---

# MEMORY.md — What I Know (ARCHIVED)

## Dave

- **Role:** Founder & CEO. The visionary. Works full-time as NBN tech, builds this in the margins.
- **Stakes:** Wife, 2 kids, 3rd due March 2026. Mortgage. This is his exit strategy.
- **Style:** Direct communication. Prefers hard truths early. Wants recommendations, not questions.
- **Fear:** Me breaking things or burning API credits on useless loops.
- **Goal:** $8K MRR = quit day job.

## Agency OS

**"The Bloomberg Terminal for Client Acquisition"**

- **Target:** Australian marketing agencies (nationwide), $2.5k-$7.5k/month
- **Geographic Scope:** Australia-wide (NSW, VIC, QLD, WA, SA, TAS, NT, ACT)
- **Core:** Multi-channel outreach (Email, SMS, LinkedIn, Voice AI, Direct Mail)
- **Moat:** Proprietary lead scoring (ALS), Siege Waterfall intelligence engine
- **Stack:** FastAPI (Railway), Next.js (Vercel), Supabase (Postgres), Prefect

**Product philosophy:**
- Dashboard IS the product. If it doesn't look like $7.5k value, backend doesn't matter.
- Show Rate is the only metric that matters. Emails/calls are vanity. Booked meetings are truth.
- Kitchen vs Table: Never show internal metrics (warmup, AI costs) to customers. Only outcomes.

## Active Decisions

| Decision | Status |
|----------|--------|
| **Autonomous Execution Architecture** | ✅ SET UP 2026-02-06 — Hourly crons, mission chains, wake triggers |
| **Gap Analysis: 16% Market Ready** | ⚠️ 98/116 gaps identified — Trust infra before features |
| **FCO-002: SDK Deprecation + Smart Prompts** | ✅ RATIFIED 2026-02-05 — 70% margin target |
| **SMS Extended to Warm Tier** | ✅ RATIFIED 2026-02-06 — ALS 60+ gets SMS (margin stays 72.9%+) |
| **Velocity Price = $4,000** | ✅ CONFIRMED 2026-02-06 — Not $5,000 |
| **Railway API Access** | ✅ FIXED 2026-02-06 — Two tokens: workspace (projects) + account (me) |
| **Siege Waterfall (5-Tier Manufacturing)** | ✅ DOCTRINE — Engines built, strategy ratified |
| **Smart Prompts (Content Generation)** | ✅ PRIMARY — Replaces SDK for content |
| **Maya (Digital Employee UI)** | 📋 Spec'd, pending Midjourney face |
| Dashboard V2 Premium Prototype | ✅ Complete (2026-02-03) |
| Dashboard V4 redesign | ✅ Live |
| HTML Prototype Suite V3 | ⏳ New flow built, industry dropdown pending |
| Onboarding Simplification | ✅ Spec'd — single page (URL + CRM + LinkedIn) |
| Campaign Lead Allocation | ✅ Spec'd — sliders share 100% pool, locked on launch |
| **MCP Ecosystem** | ✅ 22 MCPs built (17 custom + 5 config) |
| **LAW VI Governance** | ✅ MCP-First Operations added to AGENTS.md |
| **Blueprint v4.0** | ✅ Updated with Siege Waterfall, Smart Prompts |
| **System Audit** | ✅ 6/10 decisions implemented, 4 blockers identified |
| Persona Provisioning | ⏳ PR ready |
| Ignition Campaign (1,250 leads, $131.10 AUD/mo) | ⏳ Ready to launch |
| Voice AI Stack (Telnyx + Groq 90% + Claude 10%) | ✅ RATIFIED 2026-02-05 |
| Channel Infrastructure (SMS/Voice/Scraping) | ✅ Decisions made 2026-02-03 |
| Telnyx Setup (AU mobile for Voice) | ⏳ Dave to create account |
| Proxycurl Integration (LinkedIn scan) | ⏳ Elliot to test trial |
| 2-Way SMS Implementation | 📋 Spec'd, ~2-3 days work |
| E2E Test | ⏳ Blocked on Unipile (401 auth) |
| **SIEGE: System Overhaul** | 📋 PLANNED — 21 files, 6 weeks, 48%→70% margin |

## SIEGE: System Overhaul (2026-02-05) 📋 PLANNED

**Master Plan:** `memory/system-overhaul-siege.md` + `Agency_OS/INTEGRATION_MASTER_PLAN.md`

**Mission:** Replace Apollo + Apify + SDK with Siege Waterfall + Autonomous Browser + Smart Prompts

| Remove | Cost | Replace With |
|--------|------|--------------|
| Apollo | ~$150/mo | Siege Waterfall (5-Tier) |
| Apify | ~$15-50/mo | Autonomous Stealth Browser |
| SDK Agents | ~$385/mo | Smart Prompts |
| **Total Savings** | **~$550/mo** | 21 files to modify |

**Timeline:** 6 weeks (Foundation → Enrichment → Scraping → SDK → Voice → Frontend → Cleanup)

**Blockers:** Dave to create Telnyx account, run migration 055, sign off on plan.

---

## FCO-003: Apify Replacement (2026-02-05) ✅ RATIFIED

**Decision:** Build DIY GMB scraper using Autonomous Stealth Browser + Webshare proxies.
- Replaces Apify dependency (~$15/mo savings)
- Uses existing proxy_waterfall.py
- Build: `src/integrations/gmb_scraper.py`

---

## FCO-002: SDK Deprecation (2026-02-05) ✅ RATIFIED

**Decision:** Smart Prompts replaces SDK for content generation. SDK Enrichment deprecated.

| Component | Action |
|-----------|--------|
| SDK Enrichment | ❌ DEPRECATE — Siege Waterfall provides data |
| SDK Email | ❌ DEPRECATE — Smart Prompts handles |
| SDK Voice KB | ❌ DEPRECATE — Smart Prompts handles |
| SDK Objection Handling | ✅ KEEP — 10% Claude routing for complex |
| Smart Prompts | ✅ PRIMARY — All content generation |

**Cost Impact:**
- SDK costs: $400/mo → $6/mo
- FCO-002 savings: ~$385/mo
- Ignition margin: 48% → **70%**

**Implementation Files:**
- `src/engines/smart_prompts.py` — PRIMARY content engine
- `src/engines/content.py` — Update to Smart Prompts only
- `src/engines/voice.py` — Update to Smart Prompts for KB
- Deprecate: `sdk_agents/enrichment_agent.py`, `sdk_agents/email_agent.py`, `sdk_agents/voice_kb_agent.py`

**Full details:** `memory/2026-02-05-fco-002-decision.md`

---

## Maya — Digital Employee UI (2026-02-05) 📋 PENDING DESIGN

**Vision:** Maya is the face of Agency OS — a photorealistic digital employee who guides users, reports status, and makes the platform feel premium.

**What Maya IS vs ISN'T:**
| Maya IS | Maya ISN'T |
|---------|------------|
| Dashboard hologram/companion | Lead-facing avatar |
| Onboarding guide | Video outreach tool |
| Navigation assistant | Live call handler |
| AI support rep | Visible to prospects |
| The "sender" persona | An extra cost center |

**User Experience:**
1. User logs in → Maya appears (bottom-right circular frame)
2. Onboarding: Cards glow while Maya explains each section
3. Daily briefings: Voice + text updates on campaign performance
4. Support: Text chat with Maya's personality (LLM-powered)
5. Activity feed shows "Maya sent..." for all outreach

**Implementation Stack:**
| Touchpoint | Solution | Cost |
|------------|----------|------|
| **Maya's face** | Photorealistic image (Midjourney) | ~$30 one-time |
| **Onboarding** | Pre-rendered video library | ~$100 one-time |
| **Daily updates** | LLM + Cartesia TTS (pre-rendered) | ~$0.013/user/day |
| **Reporting** | Same as updates | Included |
| **Support** | Text chat (LLM only) | ~$0.005/interaction |
| **Dashboard presence** | Avatar + text cards | Zero marginal |

**Cost at Scale:**
- 100 users × daily update × 30 days = ~$39 AUD/month
- 1.6% of Ignition tier revenue ($2,500)

**Competitive Position:**
- Artisan's Ava = text chat + static avatar icon
- Agency OS Maya = visual hologram + voice + glowing UI guidance
- We leapfrog them on UX premium

**Design Status:** Pending Midjourney face generation + UI component design

**Reference:** `~/clawd/maya-concepts/` (DALL-E drafts, need Midjourney for final)

---

## Siege Waterfall — Australian B2B Intelligence Engine (2026-02-04) ✅ DOCTRINE

**Strategic Pivot:** From "Renting Data" (Apollo SPOF) to "Manufacturing Intel" (5-Tier Siege Waterfall)

**Why:**
- Apollo was Single Point of Failure — stale data = wrong ALS
- 50-60% cost savings (~$0.10/lead weighted average)
- 95%+ coverage vs 70-85% with single source
- Multi-source verification = +15 ALS bonus

### The 5 Tiers

| Tier | Name | Source | Cost (AUD) | Gate |
|------|------|--------|------------|------|
| **1** | ABN Bulk | data.gov.au | FREE | Always (seed) |
| **2** | GMB/Ads Signals | Google Maps + Meta Ads | ~$0.006 | Always |
| **3** | Hunter.io | hunter.io API | ~$0.012 | Email needed |
| **4** | LinkedIn Pulse | Proxycurl | ~$0.024 | Social context |
| **5** | Identity Gold | Kaspr/Lusha | ~$0.45 | **ALS ≥ 85 ONLY** |

### Waterfall Flow
```
ABN Bulk (FREE) — 3.5M+ Australian businesses
    ↓
GMB/Ads Signals ($0.006) — Phone, website, intent signals
    ↓
Hunter.io ($0.012) — Professional email verification
    ↓
LinkedIn Pulse ($0.024) — Decision maker identification
    ↓ [ALS ≥ 85]
Identity Gold ($0.45) — Verified mobile for Voice AI/SMS
```

### Ignition Tier Modeling
| Metric | Value |
|--------|-------|
| Leads/month | **1,250** |
| Avg cost/lead | $0.105 AUD (weighted) |
| Monthly spend | **$131.10 AUD** |

*Note: Not all leads reach Tier 5. Weighted average assumes 20% hit Identity Gold.*

### Identity Escalation Protocol
When generic inbox detected (info@, admin@):
1. Scrape Team/About page for names
2. LinkedIn employee search via Proxycurl
3. ASIC Director Hunt (ACN → Company Extract)
4. Mobile enrichment via Kaspr/Lusha (ALS ≥85 only)

### Channel Mapping
| Channel | Field | Source |
|---------|-------|--------|
| SMS | `mobile_number_verified` | Kaspr/Lusha |
| Voice AI | `mobile_number_verified` | Kaspr/Lusha |
| Email | `work_email_verified` | Hunter.io |
| Direct Mail | `registered_office_address` | ABN/GMB |
| LinkedIn | `linkedin_profile_url` | Proxycurl |

### ALS Enhancement
- **+15 bonus** for 3+ source verification (triple-check)
- Tier 5 gate: ALS ≥ 85 (HOT leads only)

### Key Infrastructure
| File | Purpose |
|------|---------|
| `src/engines/waterfall_verification_worker.py` | Tiers 1-4 + ZeroBounce escalation |
| `src/engines/identity_escalation.py` | Tier 5 + Director Hunt |
| `AGENCY_OS_STRATEGY.md` | Master strategy document |

### Migration Status
- `055_waterfall_enrichment_architecture.sql` — Ready for Supabase execution
- Adds `enrichment_lineage` JSONB (full audit trail)
- Adds intent signal columns
- Adds `lead_lineage_log` table
- Adds composite + BRIN indexes for 10M+ scale

### Mobile Enrichment Research (2026-02-04)
- **Neither Lusha nor Kaspr ideal for AU mobiles** (~40-55% accuracy)
- **Kaspr wins on value:** $0.43-0.56 AUD/phone, API on Starter plan
- **Cognism** is gold standard for APAC ($2.3K-$38K AUD/year, 87%+ accuracy)
- Recommendation: Kaspr for LinkedIn-sourced, waterfall to multiple sources

### ACMA Compliance
- **DNCR Wash:** Every 30 days before Voice AI calls (SOAP API)
- **Hours:** Weekdays 9am-8pm, Sat 9am-5pm, NO Sundays/public holidays
- **SMS Alpha Tags:** Mandatory registration by **1 July 2026** (Twilio Trust Hub)
- **Penalties:** Up to $2.22M AUD/day per violation

**Full details:** `AGENCY_OS_STRATEGY.md`, `memory/daily/2026-02-04.md`

---

## Hard-Won Lessons

**Trust:**
- SSH Incident: Never change system auth without sign-off
- YouTube Incident: Building without planning = trust violation
- Current trust level: Rebuilding. Prove planning discipline.

**Technical:**
- Iteration > Intelligence: GPT-3.5 + reflection beats GPT-4 zero-shot
- Simple first: Single LLM calls usually enough. Don't over-engineer agents.
- Accept slow: Agentic workflows take minutes/hours. Stop expecting instant.
- Escape hatches: Max iterations, cost caps, timeouts on ALL loops.

**Economics:**
- Build vs Buy: Don't clone SaaS tools until 50+ customers. Break-even is 17+ months at current scale.

**Tools:**
- Salesforge auth: Plain `Authorization: {api_key}` NOT Bearer
- WarmForge: No webhooks, must poll for warmup completion
- Heat Score ≥85 = ready for production
- yek: Fast file serializer for LLM context
- LocalTunnel unreliable for mobile preview. Use Vercel preview instead.

## Voice AI Stack (Research 2026-02)

- **Optimal:** Vapi + Groq + Cartesia = ~465ms latency, ~$0.32/call
- **Latency:** STT 90ms + LLM 200ms + TTS 75ms + Network 100-600ms
- **Cartesia > ElevenLabs:** 10x cheaper, same quality
- **Critical:** Tune Vapi turn detection, default adds 1.5s delay
- **Strategy:** Groq for 90% of calls, route complex objections to Claude via Squads

## Phase 3: Dashboard Port (HTML → React) — 2026-02-09 🚀 ACTIVE

**Mission:** Port HTML prototypes to production Next.js dashboard

### Sprint Plan

| Sprint | Scope | Status |
|--------|-------|--------|
| **Sprint 1** | Theme alignment + shared layout shell (sidebar, header, Maya placeholder) + onboarding-simple.html | 🚀 ACTIVE |
| **Sprint 2** | Dashboard + Leads list + Lead Detail (with modals) — demo flow | ⏳ Pending |
| **Sprint 3** | Campaigns + Campaign Detail + New Campaign + Replies + Reply Detail | ⏳ Pending |
| **Sprint 4** | Reports + Settings + Billing + empty states + loading states + Maya drawer | ⏳ Pending |

### Design SSOT

**Source of Truth:** HTML prototypes uploaded by Dave in `/home/elliotbot/clawd/agency-os-html/`
- v2 files for main pages
- **`onboarding-v3.html`** (saved as onboarding-simple) for onboarding — NOT onboarding-v2.html

**Copy audit fixes:** Apply DURING port (not separate pass)

### HTML Prototype Inventory (16 files)

| File | Page | Lines |
|------|------|-------|
| dashboard-v3.html | Command Center | 767 |
| campaigns-v4.html | Campaigns | 865 |
| leads-v2.html | Leads | 1,169 |
| lead-detail-v2.html | Lead Detail | 2,000 |
| campaign-detail-v2.html | Campaign Detail | 1,419 |
| campaign-new-v2.html | New Campaign | 2,112 |
| replies-v2.html | Inbox | 1,266 |
| reply-detail-v2.html | Conversation | 1,461 |
| reports-v2.html | Analytics | 1,784 |
| billing-v2.html | Billing | 1,376 |
| settings-v2.html | Settings | 1,187 |
| **onboarding-v3.html** | Get Started (simple) | 349 |

### Tech Stack (Frontend)

- **Framework:** Next.js 14 (App Router)
- **UI:** Radix UI + shadcn/ui pattern
- **Styling:** Tailwind CSS 3.4 + CSS variables
- **Charts:** Tremor + Recharts
- **Animations:** Framer Motion 12
- **Components:** 150+ in `/components/ui/`

---

## Dashboard V2.2 Premium Prototype (2026-02-03) ✅ COMPLETE

**Location:** `~/clawd/agency-os-html/*-v2.html` (12 pages, 107KB zipped)
**Design:** "Bloomberg Terminal meets Linear" — dark mode, information-dense, premium
**Status:** Enterprise-ready, all emojis replaced with SVG icons

**Pages (12 total):**
- dashboard-v2.html — Command Center with 5-Channel Orchestration wheel
- leads-v2.html — "Why Hot?" badges, tier filters, channel touch icons
- lead-detail-v2.html — Engagement Profile (was Lead DNA), transcript highlights, modals
- campaigns-v2.html — War room style, live pulse animations
- campaign-detail-v2.html — Funnel viz, sequence flow, A/B results
- campaign-new-v2.html — NEW: 5-step campaign creation wizard
- replies-v2.html — Intent classification badges [Meeting Request], AI suggestions
- reply-detail-v2.html — Score breakdown sidebar, chat bubbles, sentiment
- reports-v2.html — Bloomberg density, 5-channel matrix, ROI summary
- settings-v2.html — Tabbed nav, integrations grid (no provider names)
- billing-v2.html — Correct tiers: Ignition $2.5K / Velocity $5K / Dominance $7.5K
- onboarding-v2.html — Website input → ICP AI analysis → targeting suggestions

**Design System:** `research/DESIGN_SPEC.md` (34KB)
**Research:** `research/COMPETITOR_AUDIT.md`, `research/MOAT_VISUALIZATION.md`
**Copy Audit:** `COPY_AUDIT.md` — "Voice AI" → "Smart Calling", no tool names exposed

**Color:** #0A0A12 base, #7C3AED purple accent
**Fonts:** Inter + JetBrains Mono (tabular nums)
**Icons:** All SVG (no emojis)

**Key Features Built:**
- 5-Channel Orchestration wheel (Email, LinkedIn, SMS, Voice, Mail)
- "Why Hot?" explainable badges on leads
- ICP scraping flow in onboarding (website → AI analysis → suggestions)
- Intent classification on replies
- Correct pricing tiers with outcomes (meetings/clients per tier)
- Campaign creation wizard with audience preview

## Channel Infrastructure (2026-02-03)

**SMS:**
- Provider: ClickSend (Perth-based, keep current)
- Strategy: 1 dedicated number per client ($19 AUD/mo)
- Direction: 2-way (replies enabled) — NEW CAPABILITY
- Eligibility: Hot + Warm (ALS 60+) — EXPANDED from Hot only
- Personalization: Hot = deep research, Warm = light merge fields

**Voice AI:**
- Orchestration: Vapi (keep current)
- Telephony: Telnyx (NEW — replaces Twilio for AU mobile caller ID)
- Number: Australian mobile (+614xx) for trust
- Action needed: Dave creates Telnyx account, ID verification

**LinkedIn Data Scraping (for ALS):**
- Provider: Proxycurl (Nubela) — NOT Coresignal (6-7x cheaper)
- Plan: Growth ($299/mo = 25,000 credits = 20 clients)
- Purpose: Social Activity score (0-10 points) before ALS scoring
- Data: Recent posts, engagement, profile activity

**ALS Scoring Change:**
- NEW: Lightweight LinkedIn scan for ALL leads (before scoring)
- NEW: Social Activity component (0-10 points)
- Catches intent signals that push 75 → 85 (Warm → Hot)

**Compliance:**
- Alpha tag registration deadline: July 2026 (Twilio Trust Hub)
- Decision: Use dedicated numbers, not alpha tags (enables replies)
- DNCR wash: Every 30 days for voice

**Full details:** `memory/2026-02-03-channel-infrastructure-decisions.md`

## Market Context (2026-02)

- MCP becoming universal tool integration layer
- Browser automation wave: browser-use, Stagehand, Skyvern
- LangChain fatigue: industry moving to simpler direct patterns
- Market wants reliable agents, not occasionally impressive ones
- Position: Orchestrate agents, don't compete with them. Human-in-the-loop is the moat.
