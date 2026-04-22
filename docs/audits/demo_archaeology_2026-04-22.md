# Demo Archaeology — agencyxos.ai/demo

Date: 2026-04-22
Auditors: Elliot + Aiden
Source: frontend/landing/demo/index.html (2360 lines)

## 1. Product Thesis

The demo is NOT a dashboard — it's a SALES INTELLIGENCE BRIEFING SYSTEM. Each prospect card is a complete meeting prep document: opening hooks, discovery questions, objection handling, close options, vulnerability grades, communication style notes. The product doesn't just find prospects — it tells you exactly how to close them.

## 2. Information Architecture

### Sidebar (3 sections):
- Workspace: Dashboard, Pipeline, Inbox, Cycles, Sequences
- Intelligence: Signals, Reports
- Account: Settings

### Mobile Navigation:
- Bottom nav bar (5 items): Home, Pipeline, Inbox, Cycles, Signals — these are the DAILY touchpoints
- Hamburger sidebar also available for full navigation
- Bottom nav items = what an operator checks every day. Everything else is configuration or periodic.

## 3. Design System (from demo)

- Background: cream #F7F3EE (LIGHT MODE DEFAULT — not dark)
- Surface: #EDE8E0
- Ink: #0C0A08 (warm charcoal)
- Amber: #D4956A
- Copper: #C46A3E
- Green: #6B8E5A (operational status)
- Red: #B55A4C (kill switch, alerts)
- Fonts: Playfair Display (headlines), DM Sans (body), JetBrains Mono (data)
- Sidebar: dark (#0C0A08 background) with amber active states
- Cards: white background with subtle border (var(--rule))

## 4. Home Page — Status Glance

Headline: "Your acquisition engine, running on schedule."

### Cycle Progress Hero:
- "Cycle 3 · Day 14 of 30"
- "SEO Services — Sydney Metro · Started 1 May 2026"
- Progress bar (14/30 = 47%)
- 4 stats: 247 Contacted, 31 Replies, 8 Meetings, 600 Total Records

### Performance Metrics (4 cards):
- Open Rate: 47% (AU B2B benchmark: 21%)
- Reply Rate: 8.2% (AU B2B benchmark: 3.1%)
- Meeting Rate: 1.4% (AU B2B benchmark: 0.8%)
- Avg Reply Time: 23h

### 3-Column Grid:
- Hot Replies: 4 threaded reply previews with heat indicators
- Meetings Booked: 4 upcoming meetings with date pills + names
- System Health: 6 status dots (Email Delivery, LinkedIn Queue, Voice AI, SMS Gateway, Data Enrichment, Prospect Pipeline)

### Today's Outreach Progress:
- 4-channel bar chart: Email 18/50, LinkedIn 12/20, Voice AI 5/10, SMS 8/25
- "43 of 105 completed"

## 5. Pipeline — State-Aware Prospect View

The pipeline page CHANGES based on the cycle state:

### Review State (pre-release):
- Prospects sorted by intent band
- Filters: Top 10, Top 50, All, Struggling, Trying, Dabbling
- Purpose: quality check before release to outreach
- "Release All" button with confirmation modal

### Outreach State (live campaign):
- Prospects sorted by outreach status
- Filters: All, In Outreach, Replied, Meeting Booked, Suppressed, Not Started
- Status badges per prospect (Not Started / Contacted / Replied / Meeting Booked / Suppressed)

### Complete State:
- Cycle results view

## 6. Prospect Briefing Card (the PRODUCT)

Each prospect has ~40 fields — a complete sales briefing:

### Company Profile:
- name, suburb, state, industry, intent band, score, staff count, established year, revenue

### Decision Maker:
- name, title, email, phone, LinkedIn status
- tenure, previous roles
- communication style (e.g., "Direct and numbers-focused. Responds well to ROI data.")
- LinkedIn activity pattern

### Intelligence:
- signals[] with timestamps (e.g., "Active Google Ads spend detected ($2,400/mo)")
- affordability score, intent score, composite score
- vulnerability narrative (paragraph-length analysis)
- vulnerability grades: A-F across 6 axes (website, SEO, reviews, ads, social, content)
- AI summary (2-3 sentence context)

### Sales Briefing:
- triggerSignal: what prompted outreach
- triggerMessage: which message got the reply
- prospectReply: verbatim reply text
- sentiment analysis
- timeToMeeting: "37 minutes from reply to booking"
- meeting details (date, time, platform, countdown)
- competitors: list of the prospect's competitors
- recommendedAngle: strategic framing for the meeting
- pricingRange: "$2,800–$4,200/month AUD"
- openingHook: exact script for the first 2 minutes
- discoveryQuestions: 3-5 questions to ask
- objections: objection + response pairs
- closeOptions: 2-3 specific pricing packages

### Outreach Timeline:
- Day-by-day event log: email_sent, email_opened, linkedin_sent, linkedin_accepted, voice_sent, email_replied, meeting_booked
- Each event has label + timestamp

## 7. Cycles Page

- Cycle state machine: review → outreach → complete
- Configure modal: service checkboxes + geographic scope (Metro/State/National)
- Release confirmation modal: "We recommend reviewing at least 10 prospects before releasing"
- Cycle-scoped metrics reset per cycle
- Time-boxed: "Day 14 of 30" — 30-day window

## 8. Inbox

- Threaded conversation view
- Left panel: conversation list with channel icon + heat indicator
- Right panel: message thread with sent/received bubbles
- AI-suggested reply at bottom

## 9. Sequences

- 7-step outreach cadence timeline
- Day 1 Email → Day 3 LinkedIn → Day 5 Email → Day 7 Voice → etc.
- Template editor surface (periodic, not daily)

## 10. Signals

- Configurable signal cards with ON/OFF toggles
- Each signal type: name, description, stat, toggle
- "Recent detections" feed with dot indicators + timestamps
- Signals are per-agency configuration — you choose which intent signals to track

## 11. Reports

- Cycle-scoped performance metrics
- Funnel visualization
- Channel comparison

## 12. Settings

- Settings navigation tabs on left side
- Forms for agency configuration

## 13. Kill Switch

- "Pause all" button in topbar — ALWAYS VISIBLE
- Red border, red text, JetBrains Mono uppercase
- Also appears in mobile topbar
- Confirms before pausing: alert('Pause all outreach — confirm?')

## 14. Data Source Mapping

### Exists in Pipeline F v2.1:
- vulnerability grades → Stage 10 VR
- evidence statements → Stage 10 VR
- recommended service → Stage 5 signal scoring
- outreach angle → Stage 10 VR
- competitors → Stage 2/4 DFS signals
- DM profile → Stage 6 BDM enrichment
- signals → Stage 4/5 DFS + GMB

### Needs NEW generation (briefing-gen LLM):
- openingHook: LLM combining prospect signals + agency capabilities + comm style
- discoveryQuestions: LLM tuned to vulnerability grades
- objections: LLM + objection library per vertical
- closeOptions: Agency Profile pricing tiers cross-ref
- communicationStyle: LinkedIn profile analysis
- pricingRange: Agency Profile service pricing

### Needs NEW backend APIs:
1. Cycle aggregates (funnel counts per cycle_id)
2. Briefing-gen LLM endpoint (prospect_id → hook+questions+objections)
3. Cycle state machine (review/outreach/complete transitions)
4. Signal toggle config (per-agency on/off)
5. Cycle scheduling (auto-generate next cycle)

## 15. What Our v3 Got Wrong

| Demo Has | Our v3 Had | Gap |
|----------|-----------|-----|
| Light mode default | Dark mode default | Wrong default |
| Kill switch always visible | No kill switch | Missing critical element |
| Cycles (time-boxed releases) | Campaigns (generic) | Wrong abstraction |
| Pipeline = prospect view + briefing | Leads table (data rows) | Wrong depth |
| State-aware UI (review/outreach/complete) | Static dashboard | No workflow awareness |
| Sales briefing per prospect (40 fields) | Contact card (10 fields) | Missing the product |
| Bottom nav on mobile | Hamburger only | Missing daily-touchpoint nav |
| Sidebar: Workspace/Intelligence/Account | Flat nav list | No information grouping |
| Cycle progress hero | 9-panel overview | Wrong home page structure |
| AU B2B benchmarks on metrics | Raw numbers only | Missing context |
| System health dots | No health display | Missing ops visibility |

## 16. v4 Approach

v4 should START from the demo HTML (frontend/landing/demo/index.html) as the base file, then extend with:
1. Real Pipeline F data shapes replacing sample data
2. BDM fields from business_decision_makers table
3. SSE live pipeline stream (usePipelineStream — already built)
4. Briefing-gen placeholder (shows the fields, notes "LLM endpoint needed")
5. Mobile responsive refinements
6. Dark mode toggle (demo is light-default; add dark as secondary)
