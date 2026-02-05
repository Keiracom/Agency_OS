# Agency OS Capability Audit
## Dashboard Differentiation Opportunities

**Generated:** 2026-02-03  
**Purpose:** Identify unique capabilities to surface in customer dashboard  
**Status:** Complete

---

## 1. Executive Summary — Top 5 Differentiators

These are capabilities we have that competitors DON'T show to customers:

### 1. **ALS (Agency Lead Score) with 7+ Signal Components**
Not just a score — we show exactly WHY a lead is hot. Competitors show generic scores; we decompose into Data Quality, Authority, Company Fit, Timing, Risk, LinkedIn Activity, and Buyer Signals.

**Dashboard Opportunity:** "Lead DNA" view showing radar chart of all scoring components.

### 2. **Conversion Intelligence with Self-Learning Patterns**
4 AI Detectors (WHO/WHAT/WHEN/HOW + Funnel) continuously learn which leads, content, and timing convert. The system gets smarter weekly.

**Dashboard Opportunity:** "What's Working" insights panel showing title lift, industry winners, and optimal send times specific to THIS client.

### 3. **Multi-Channel Orchestration with Tier-Based Routing**
Hot leads get 5 channels (Email, SMS, LinkedIn, Voice AI, Direct Mail). Warm gets 3. Cool gets 2. We automatically route based on score.

**Dashboard Opportunity:** "Channel Mix" visualization showing outreach distribution by tier.

### 4. **Voice AI with Transcripts & Meeting Detection**
Real voice calls with AI-generated knowledge bases, transcripts, objection handling via hybrid LLM (Groq fast + Claude complex), and automatic meeting detection.

**Dashboard Opportunity:** Call recordings, transcripts, and outcome tagging in lead timeline.

### 5. **2-Way SMS with Intent Classification**
Not blast SMS — conversational. Replies are classified by AI for sentiment and intent, then auto-responded or escalated.

**Dashboard Opportunity:** SMS conversation thread view with sentiment indicators.

---

## 2. Data Signals Available — What We Track

### 2.1 ALS Scoring Components (from `scorer.py`)

| Component | Max Points | What We Track |
|-----------|------------|---------------|
| Data Quality | 20 | Email verified, phone verified, LinkedIn present, personal email |
| Authority | 25 | Title seniority (CEO=25, VP=18, Manager=7, etc.) |
| Company Fit | 25 | Industry match, employee count (5-50 ideal), Australia |
| Timing | 15 | New role (<6mo), company hiring, recent funding |
| Risk | 15 | Bounce history, unsubscribe, competitor, bad title |
| **Buyer Boost** | +15 | Known agency buyer from platform signals |
| **LinkedIn Boost** | +10 | Recent posts, 500+ connections, company activity |
| **Funnel Boost** | +12 | Tier's historical show rate, deal rate, win rate |

**Code Reference:** `src/engines/scorer.py` lines 20-120

**Unique Dashboard Elements:**
- Radar chart showing all 5 base components
- "Why Hot?" badges showing which signals triggered
- Buyer signal indicator ("Known Agency Buyer")
- LinkedIn activity indicator ("Active on LinkedIn")

### 2.2 Engagement Signals (from `activity.py`)

| Signal | Storage Field | What We Can Show |
|--------|--------------|------------------|
| Email Opens | `email_opened`, `email_open_count`, `email_opened_at` | Open rate, time to open |
| Email Clicks | `email_clicked`, `email_click_count`, `email_clicked_at` | Click-through rate, which links |
| Time Metrics | `time_to_open_minutes`, `time_to_click_minutes`, `time_to_reply_minutes` | Engagement velocity |
| Touch Context | `touch_number`, `days_since_last_touch`, `sequence_position` | Cadence intelligence |
| Timezone | `lead_local_time`, `lead_timezone`, `lead_local_day_of_week` | "Sent at their 10am" |
| Links Clicked | `link_clicked`, `links_included[]` | Which CTAs work |
| Device | `device_type` | Mobile vs desktop engagement |

**Code Reference:** `src/models/activity.py` lines 100-180

**Unique Dashboard Elements:**
- "Time to Engage" histogram (how fast leads respond)
- "Best Day/Time" heatmap specific to this client
- Device breakdown (optimize for mobile if needed)

### 2.3 Lead Data Depth (from `lead.py` and `lead_pool`)

**Person Fields We Capture:**
- Name, title, seniority level
- LinkedIn URL, personal email, phone
- Employment start date (for "new role" detection)
- Timezone (for send optimization)
- SDK enrichment (deep research for hot leads)
- Deep research data (company news, pain points)

**Organization Fields:**
- Industry, employee count, founded year
- Is hiring (boolean)
- Latest funding date
- Website, LinkedIn URL
- Country, location

**Compliance Fields:**
- DNCR checked/result (Australian Do Not Call Register)
- Email verified, phone verified
- Bounce count, unsubscribe status

**Code Reference:** `src/models/lead.py` lines 60-200

### 2.4 Rejection & Objection Tracking (Phase 24D)

| Field | Values | Dashboard Use |
|-------|--------|---------------|
| `rejection_reason` | timing, budget, competitor, authority, need, bad_experience, etc. | Objection pie chart |
| `rejection_notes` | Free text | Objection details |
| `objections_raised[]` | Array of objection strings | Objection history |

**Code Reference:** `src/models/lead.py` lines 155-175

**Unique Dashboard Element:** "Why They Said No" breakdown showing common objection patterns.

---

## 3. Automation Features — What Runs in Background

### 3.1 Multi-Channel Orchestration

**Tier-Based Channel Routing (from `scorer.py`):**
```
Hot (85-100):  Email + SMS + LinkedIn + Voice + Direct Mail
Warm (60-84):  Email + LinkedIn + Voice + SMS
Cool (35-59):  Email + LinkedIn
Cold (20-34):  Email only
Dead (0-19):   Suppressed
```

**Dashboard Opportunity:** "Outreach Plan" showing exactly which channels each lead will receive based on their score.

### 3.2 Automated Flows (from `/orchestration/flows/`)

| Flow | Trigger | What It Does |
|------|---------|--------------|
| `warmup_monitor_flow` | Daily 6am AEST | Checks WarmForge, marks domains ready when Heat Score ≥85 |
| `pattern_learning_flow` | Weekly | Runs 4 detectors (WHO/WHAT/WHEN/HOW) + weight optimizer |
| `daily_pacing_flow` | Daily | Distributes outreach across hours to avoid spam flags |
| `outreach_flow` | Daily | Executes scheduled sends per tier/channel rules |
| `reply_recovery_flow` | Hourly | Catches missed webhook replies via polling |
| `crm_sync_flow` | Configurable | Syncs converted leads to client CRM |
| `daily_digest_flow` | Daily | Sends transparency email to clients |
| `linkedin_health_flow` | Daily | Monitors LinkedIn seat health |
| `persona_buffer_flow` | Daily | Ensures persona email domains stay warm |

**Code Reference:** `src/orchestration/flows/`

**Dashboard Opportunities:**
- "System Health" panel showing flow statuses
- "Warmup Progress" bar for domains
- "Last Sync" timestamps for CRM

### 3.3 Persona/Domain Provisioning System

**What We Manage:**
- Email domains (via Salesforge/InfraForge)
- Warmup status (via WarmForge) — Heat Score tracking
- Dedicated phone numbers per client (ClickSend)
- LinkedIn seats (via Unipile)

**Key Metric:** Heat Score ≥85 = production ready

**Code Reference:** `src/orchestration/flows/warmup_monitor_flow.py`

**Dashboard Opportunity:** "Sending Infrastructure" card showing:
- X domains warming → X ready
- Y mailboxes at Heat Score 85+
- Phone number assigned: +614xxxxxxxx

### 3.4 2-Way SMS System (NEW - Spec'd)

**Capabilities:**
- Dedicated number per client ($19 AUD/mo)
- Inbound webhook handling
- AI intent classification on replies
- Automated response or human escalation
- STOP/unsubscribe handling

**Code Reference:** `memory/2026-02-03-channel-infrastructure-decisions.md`

**Dashboard Opportunity:** SMS conversation threads with sentiment badges.

### 3.5 Voice AI Retry Logic

**Smart Retry System:**
- Busy → Retry in 2 hours
- No answer → Retry next business day
- Max 3 attempts
- Respects business hours (9am-5pm, skip lunch 12-1pm)

**Code Reference:** `src/engines/voice.py` lines 50-100, `src/services/voice_retry_service.py`

**Dashboard Opportunity:** "Call Attempts" tracker showing retry schedule.

---

## 4. AI Features — Intelligence We Generate

### 4.1 Content Personalization Engine (from `content.py`)

**Smart Prompt System:**
- Pulls ALL available data (lead, company, engagement history, client proof points)
- Generates email/SMS/LinkedIn/Voice content
- Fact-check gate prevents hallucination (Item 40)
- Safe fallback if fact-check fails twice (Item 42)

**What Gets Personalized:**
- Email subject lines and bodies
- SMS messages (<160 chars)
- LinkedIn connection requests (<300 chars)
- Voice call knowledge bases (opening hooks, objection responses)

**Code Reference:** `src/engines/content.py`, `src/engines/smart_prompts.py`

**Dashboard Opportunity:** "Content Preview" showing AI-generated messages before they send.

### 4.2 Voice AI Knowledge Base Generation

**Per-Lead Voice KB Contains:**
- Recommended opener (personalized)
- Opening hooks (3-5 options)
- Pain point questions
- Objection responses (timing, budget, competitor, etc.)
- Meeting ask wording
- Topics to avoid

**Hybrid LLM Architecture:**
- Groq (90%): Fast responses, booking flow (~200ms)
- Claude Haiku (10%): Complex objections, competitor comparisons (~400ms)
- Silent handoff between them

**Code Reference:** `src/engines/voice.py` lines 200-400

**Dashboard Opportunity:** "Call Script Preview" showing what AI will say to this lead.

### 4.3 Conversion Intelligence (4 Detectors)

**WHO Detector** (`src/detectors/who_detector.py`):
- Learns which job titles convert best
- Learns which industries convert best
- Finds ideal company size range
- Tracks timing signal lift (new role, hiring, funded)
- **Phase 24D:** Tracks objection patterns by segment

**WHAT Detector** (`src/detectors/what_detector.py`):
- Learns which subject lines get opens
- Learns which content themes get replies
- Tracks personalization field effectiveness
- Compares templates and A/B variants

**WHEN Detector** (`src/detectors/when_detector.py`):
- Learns best day of week to send
- Learns best hour of day
- Tracks lead timezone optimization
- Calculates response velocity patterns

**HOW Detector** (`src/detectors/how_detector.py`):
- Learns best channel sequences
- Tracks touch count before conversion
- Identifies diminishing returns point
- Compares multi-channel vs single-channel

**FUNNEL Detector** (`src/detectors/funnel_detector.py`):
- Tracks show rate (booked → attended)
- Tracks meeting-to-deal rate
- Tracks win rate by tier
- Feeds back into ALS scoring

**Dashboard Opportunities:**
- "What's Working" card showing top insights
- "Best Times" heatmap
- "Top Titles" leaderboard
- "Channel Performance" comparison

### 4.4 Reply Analysis & Intent Classification

**AI Classifies Every Reply:**
- Sentiment: positive, neutral, negative, mixed
- Intent: interested, question, objection, not_interested, meeting_request, referral
- Objection Type: timing, budget, authority, need, competitor, trust
- Questions: Extracted for follow-up

**Code Reference:** `src/services/reply_analyzer.py`, `src/engines/closer.py`

**Dashboard Opportunity:** Reply list with sentiment icons and intent tags.

### 4.5 Client Intelligence Scraping

**What We Scrape Per Client:**
- Website (case studies, testimonials, services)
- LinkedIn company page
- Twitter, Facebook, Instagram
- Review platforms (Trustpilot, G2, Capterra, Google)

**What We Extract:**
- Proof metrics (e.g., "40% lift in leads")
- Proof clients (logos)
- Common pain points
- Differentiators
- Ratings across platforms

**Code Reference:** `src/engines/client_intelligence.py`

**Dashboard Opportunity:** "Your Proof Points" card showing extracted social proof.

---

## 5. Dashboard Ideas — Specific UI Components

### 5.1 Lead Card — "Lead DNA" View

```
┌─────────────────────────────────────────────┐
│ Sarah Chen                          ALS: 92 │
│ CMO at Velocity Growth                  HOT │
├─────────────────────────────────────────────┤
│                                             │
│  [Radar Chart]     Why Hot:                 │
│                    ✓ CEO-level authority    │
│  Data  Authority   ✓ New role (3 months)    │
│    ▲               ✓ Company is hiring      │
│   ╱ ╲              ✓ Active on LinkedIn     │
│  ╱   ╲             ✓ Known agency buyer     │
│ ╱     ╲                                     │
│ Timing  Fit        Channels Unlocked:       │
│                    📧 Email  💬 SMS          │
│  Risk              🔗 LinkedIn  📞 Voice    │
│                    📮 Direct Mail           │
└─────────────────────────────────────────────┘
```

### 5.2 Campaign Performance — "What's Working"

```
┌─────────────────────────────────────────────┐
│ 📊 What's Working This Week                 │
├─────────────────────────────────────────────┤
│                                             │
│ TOP TITLES:                                 │
│ • CEO/Founder — 2.3x conversion lift        │
│ • Marketing Director — 1.8x lift            │
│ • Head of Growth — 1.5x lift                │
│                                             │
│ TOP INDUSTRIES:                             │
│ • SaaS — 34% conversion rate                │
│ • Professional Services — 28%               │
│ • Healthcare — 22%                          │
│                                             │
│ BEST TIMES:                                 │
│ • Tuesday 10am — highest open rate          │
│ • Wednesday 2pm — highest reply rate        │
│                                             │
│ Updated: 2 hours ago (runs weekly)          │
└─────────────────────────────────────────────┘
```

### 5.3 Voice AI Performance

```
┌─────────────────────────────────────────────┐
│ 📞 Voice AI Calls — Last 7 Days             │
├─────────────────────────────────────────────┤
│                                             │
│ Calls Made: 47    Connected: 31    Book: 8  │
│                                             │
│ Connection Rate: 66%                        │
│ Meeting Book Rate: 26%                      │
│ Avg Call Duration: 2:34                     │
│                                             │
│ Recent Calls:                               │
│ ✅ Sarah Chen — Booked (3:12)    [Listen]   │
│ ⏳ Mike Ross — Follow-up (1:45)  [Listen]   │
│ ❌ Lisa Wang — Not interested    [Listen]   │
│                                             │
│ Top Objections Handled:                     │
│ • "We're using another agency" — 12 calls   │
│ • "Not the right time" — 8 calls            │
└─────────────────────────────────────────────┘
```

### 5.4 Sending Infrastructure Health

```
┌─────────────────────────────────────────────┐
│ 🔧 Sending Infrastructure                   │
├─────────────────────────────────────────────┤
│                                             │
│ EMAIL DOMAINS:                              │
│ ████████████████████░░░░ 4/5 ready          │
│                                             │
│ agencyxos-reach.com    Heat: 90 ✅ LIVE     │
│ agencyxos-growth.com   Heat: 47 🔄 Warming  │
│ agencyxos-leads.com    Heat: 47 🔄 Warming  │
│                                             │
│ SMS NUMBER: +61 485 031 611 ✅              │
│ VOICE NUMBER: +61 4XX XXX XXX ✅            │
│ LINKEDIN SEAT: Connected ✅                 │
│                                             │
│ Daily Capacity: 150 emails, 30 SMS, 20 calls│
└─────────────────────────────────────────────┘
```

### 5.5 SMS Conversation Thread

```
┌─────────────────────────────────────────────┐
│ 💬 SMS with Mike Ross                       │
├─────────────────────────────────────────────┤
│                                             │
│ YOU (Jan 28, 2:15pm)                        │
│ Mike — saw Velocity's expansion to QLD.     │
│ How's lead gen going for the new territory? │
│                                             │
│ MIKE (Jan 28, 4:32pm) 😊 Positive           │
│ Hey! Yeah it's been crazy. Actually we      │
│ could use some help there. What do you do?  │
│                                             │
│ YOU (Jan 28, 4:35pm)                        │
│ We run multi-channel outreach for agencies. │
│ 15 min call to see if we're a fit?          │
│                                             │
│ MIKE (Jan 29, 9:01am) 📅 Meeting Request    │
│ Sure, how about Thursday?                   │
│                                             │
│ [Reply...                        ] [Send]   │
└─────────────────────────────────────────────┘
```

### 5.6 Lead Timeline (Activity Stream)

```
┌─────────────────────────────────────────────┐
│ 📋 Sarah Chen — Activity Timeline           │
├─────────────────────────────────────────────┤
│                                             │
│ ● Jan 30, 2:15pm — MEETING BOOKED           │
│   Booked via voice call (3:12 duration)     │
│   [Listen to recording] [View transcript]   │
│                                             │
│ ● Jan 29, 11:30am — VOICE CALL              │
│   Attempted, busy — retry scheduled         │
│                                             │
│ ● Jan 28, 3:45pm — EMAIL REPLY              │
│   Intent: Interested 🟢                     │
│   "Sounds interesting, tell me more..."     │
│                                             │
│ ● Jan 28, 10:15am — EMAIL OPENED            │
│   Opened on mobile, 2hr after send          │
│                                             │
│ ● Jan 28, 8:00am — EMAIL SENT               │
│   Subject: "Sarah, quick question"          │
│   [Preview content]                         │
│                                             │
│ ● Jan 27 — LEAD SCORED                      │
│   ALS: 92 (Hot) — Buyer boost +10           │
└─────────────────────────────────────────────┘
```

---

## 6. Implementation Priority

Based on differentiation value and development effort:

### Tier 1 — High Impact, Unique (Build First)
1. **Lead DNA / ALS Breakdown** — Shows our scoring sophistication
2. **What's Working Insights** — Conversion Intelligence in action
3. **Voice AI with Transcripts** — Competitors don't have this
4. **Lead Timeline** — Shows multi-channel orchestration

### Tier 2 — High Value, Expected
5. **Sending Infrastructure Health** — Transparency on warmup
6. **Channel Mix Visualization** — Shows tier-based routing
7. **SMS Conversation Threads** — 2-way SMS differentiation

### Tier 3 — Nice to Have
8. **Content Preview** — What AI will send
9. **Device/Time Heatmaps** — Engagement analytics
10. **Objection Analysis** — Why leads say no

---

## 7. Code Reference Summary

| Capability | Primary File | Key Functions |
|------------|--------------|---------------|
| ALS Scoring | `src/engines/scorer.py` | `score_lead()`, `_get_buyer_boost()`, `_get_linkedin_boost()` |
| Voice AI | `src/engines/voice.py` | `send()`, `generate_voice_kb()`, `create_campaign_squad()` |
| SMS | `src/engines/sms.py` | `send()`, `send_batch()` |
| Content Gen | `src/engines/content.py` | `generate_email()`, `_fact_check_content()` |
| Reply Analysis | `src/services/reply_analyzer.py` | `analyze()` |
| WHO Patterns | `src/detectors/who_detector.py` | `detect()`, `_analyze_titles()` |
| WHAT Patterns | `src/detectors/what_detector.py` | `detect()` |
| WHEN Patterns | `src/detectors/when_detector.py` | `detect()` |
| HOW Patterns | `src/detectors/how_detector.py` | `detect()` |
| Warmup Monitor | `src/orchestration/flows/warmup_monitor_flow.py` | `warmup_monitor_flow()` |
| Daily Digest | `src/services/digest_service.py` | `get_digest_data()` |
| Client Intel | `src/engines/client_intelligence.py` | `scrape_client()` |

---

## 8. Key Decisions Referenced

- **SMS:** ClickSend (Perth-based), 1 dedicated number per client, 2-way enabled
- **Voice:** Vapi + Telnyx (AU mobile) + Groq/Claude hybrid
- **LinkedIn Data:** Proxycurl ($299/mo = 20 clients)
- **Warmup:** WarmForge, Heat Score ≥85 = ready

Source: `memory/2026-02-03-channel-infrastructure-decisions.md`

---

*This audit identifies what makes Agency OS unique. The dashboard should surface these capabilities to justify the $2,500-$7,500/month price point.*
