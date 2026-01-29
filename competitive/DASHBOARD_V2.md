# Agency OS Dashboard — V2 Design

*Designed from one question: "What makes a $7,500/month client say 'worth every dollar'?"*

---

## Design Principle

Every element answers one of three questions:
1. **Is this working?**
2. **How well is it working?**
3. **What should I do next?**

If it doesn't answer one of these, it doesn't belong.

---

## Navigation

```
📊 Overview
🎯 Campaigns
👥 Prospects
📬 Inbox  
📈 Performance
🧠 Intelligence
```

Six pages. No settings bloat in the nav. No resource pages. No admin.

---

## 1. OVERVIEW

The client logs in. In 5 seconds they know: are we on track this month?

```
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│  JANUARY 2026                                           On Track ● │
│                                                                    │
│        12 Meetings Booked                                          │
│        ████████████░░░░░░░░░░░░░░░                                │
│        Target: 15–25 this month                                    │
│                                                                    │
│        10 showed  │  3 deals started  │  +3 vs last month          │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│  THIS MONTH'S OUTREACH                                             │
│                                                                    │
│  📧  1,247 emails      │  61% opened   │  3.2% replied            │
│  💼  89 LinkedIn        │  42% accepted │  12.3% replied           │
│  📞  23 voice calls     │  34% connected│  8.2% to meeting         │
│  💬  12 SMS             │  33% replied  │  2 conversations         │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────┬────────────────────────────────┐
│                                   │                                │
│  CAMPAIGNS                        │  UPCOMING MEETINGS             │
│                                   │                                │
│  Tech Decision Makers       40%   │  Today 2:00 PM                 │
│  6 meetings │ 3.8% reply          │  Sarah Chen — TechCorp         │
│                                   │  Discovery │ 30min             │
│  Series A Startups          35%   │                                │
│  4 meetings │ 2.9% reply          │  Tomorrow 10:00 AM             │
│                                   │  Mike Johnson — StartupXYZ     │
│  My Custom Campaign         25%   │  Demo │ 45min                  │
│  2 meetings │ 1.8% reply          │                                │
│                                   │  Thu 3:30 PM                   │
│  [Adjust priorities →]            │  Lisa Park — Acme Inc          │
│                                   │  Follow-up │ 30min             │
│                                   │                                │
└───────────────────────────────────┴────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│  RECENT ACTIVITY                                          Live ●   │
│                                                                    │
│  📧  Sarah Chen (TechCorp) opened your email              2m ago   │
│  💼  Mike Johnson (StartupXYZ) replied on LinkedIn        15m ago   │
│  📞  Lisa Park (Acme Inc) — meeting booked from call       1h ago   │
│  💬  David Lee (Growth Co) replied to SMS                  2h ago   │
│  📧  Emma Wilson (Scale Labs) clicked case study link      3h ago   │
│                                                                    │
│  [View all activity →]                                             │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

**What this answers:**
- Is this working? → "12 meetings, on track, +3 vs last month"
- How well? → Channel-level proof across all 4 active channels
- What next? → Upcoming meetings to prepare for

---

## 2. CAMPAIGNS

Each campaign shows its full story: what it's doing, how it's performing, what the AI recommends.

### Campaign List
```
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│  CAMPAIGNS                                      [+ New Campaign]   │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  TECH DECISION MAKERS                         ✨ AI Campaign │  │
│  │  ──────────────────────────────────────────────────────────  │  │
│  │  📧💼📞  │  Priority: 40%  │  ● Active                      │  │
│  │                                                              │  │
│  │  6 meetings  │  3.8% reply rate  │  85% show rate            │  │
│  │                                                              │  │
│  │  Sequence: Step 3 of 5 in progress                           │  │
│  │  ████████████████░░░░░░░░░░                                  │  │
│  │  312 total → 198 voice → 89 LinkedIn → email next → SMS last │  │
│  │                                                              │  │
│  │  🧠 "Voice calls on Tuesday AM are booking 2.3x more"       │  │
│  │                                                              │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### Campaign Detail

```
┌────────────────────────────────────────────────────────────────────┐
│  ← Campaigns                                                       │
│                                                                    │
│  TECH DECISION MAKERS                         ✨ AI Campaign       │
│  ════════════════════════════════════════════════════════════════  │
│                                                                    │
│  6 meetings     3.8% reply     61% open     85% show rate          │
│  +2 vs last     +0.5% ↑       -3% ↓        +5% ↑                  │
│                                                                    │
│  ──────────────────────────────────────────────────────────────── │
│                                                                    │
│  SEQUENCE                                                          │
│                                                                    │
│  Day 0: Email                                                      │
│  312 sent │ 61% opened │ 2.1% replied │ 4.3% clicked              │
│  ✉️ Best subject: "Question about {{company}}'s growth"            │
│                                                                    │
│  Day 3: Voice                                                      │
│  198 attempted │ 34% connected │ 8.2% booked meeting               │
│  📞 Tuesdays 10am AEST: 2.3x better connect rate                  │
│                                                                    │
│  Day 5: LinkedIn                                                   │
│  89 sent │ 42% accepted │ 12.3% replied                            │
│  💼 Connection notes mentioning mutual connections: +67%           │
│                                                                    │
│  Day 8: Email follow-up                          ░░░ Upcoming      │
│  Day 12: SMS                                     ░░░ Upcoming      │
│                                                                    │
│  ──────────────────────────────────────────────────────────────── │
│                                                                    │
│  BEST PERFORMING CONTENT                                           │
│                                                                    │
│  "Question about TechCorp's growth" → Sarah Chen replied, booked   │
│  "Saw your Series B announcement" → 5x opened, clicked case study  │
│  "Quick question, {{first_name}}" → 3 replies                      │
│                                                                    │
│  ──────────────────────────────────────────────────────────────── │
│                                                                    │
│  AI RECOMMENDATIONS                                                │
│                                                                    │
│  💡 CTOs convert 2.1x better than VPs in this campaign             │
│  💡 Short emails (<100 words) get +28% more replies                │
│  💡 Avoid Friday afternoons — reply rate drops 40%                 │
│                                                                    │
│                                          [Apply recommendations]   │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

**What this answers:**
- Is this working? → Meetings, reply rate, show rate per campaign
- How well? → Step-by-step performance through the sequence
- What next? → AI recommendations to improve + best content examples

---

## 3. PROSPECTS

Every lead the system is working. Full enrichment visible. Score breakdown transparent.

### Prospect List
```
┌────────────────────────────────────────────────────────────────────┐
│  PROSPECTS                                                 1,247   │
│  ────────────────────────────────────────────────────────────────  │
│                                                                    │
│  [Score ▼] [Status ▼] [Campaign ▼] [Channel ▼]     🔍 Search      │
│                                                                    │
│  🔥 92  Sarah Chen          CTO, TechCorp           📅 Meeting     │
│         Series B ($25M) │ 150 employees │ 📧💼📞                   │
│                                                                    │
│  🟠 78  Mike Johnson        VP Sales, StartupXYZ    💬 Replied     │
│         Series A │ Hiring +5 engineers │ 📧💼                      │
│                                                                    │
│  🟡 65  Lisa Park           Director Ops, Acme      📧 Step 2/5   │
│         Enterprise │ Tech: React, AWS │ 📧                         │
│                                                                    │
│  🟢 42  James Wilson        Marketing Mgr, Bolt     📧 Step 1/5   │
│         Seed stage │ 25 employees │ 📧                             │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### Prospect Detail
```
┌────────────────────────────────────────────────────────────────────┐
│  ← Prospects                                                       │
│                                                                    │
│  SARAH CHEN                                         Score: 92 🔥   │
│  Chief Technology Officer                                          │
│  TechCorp │ Technology │ Sydney, AU                                │
│  ════════════════════════════════════════════════════════════════  │
│                                                                    │
│  WHY THIS SCORE                                                    │
│                                                                    │
│  Authority       ████████████████████████  24/25   CTO, C-Suite    │
│  Company Fit     ███████████████████████   23/25   Revenue, tech   │
│  Data Quality    ███████████████████       18/20   All verified    │
│  Timing          █████████████████████     14/15   Funding, hiring │
│  Risk            ████████████████████      13/15   Clean           │
│                                                                    │
│  ──────────────────────────────────────────────────────────────── │
│                                                                    │
│  COMPANY                          │  SIGNALS                       │
│                                   │                                │
│  Revenue: $50M ARR                │  ⚡ Series B — 14 days ago     │
│  Employees: 150-500               │  📈 Hiring: +5 engineers       │
│  Founded: 2018                    │  🔧 Added Segment recently     │
│  Tech: React, Node, AWS, HubSpot │  📰 Featured in AFR            │
│                                   │                                │
│  ──────────────────────────────────────────────────────────────── │
│                                                                    │
│  OUTREACH HISTORY                                                  │
│                                                                    │
│  Jan 28  📧 Opened email 3x, clicked case study                   │
│  Jan 25  📞 Voice call — connected, 4min, positive                 │
│  Jan 23  💼 LinkedIn accepted — replied "Thanks!"                  │
│  Jan 20  📧 Initial email sent — opened 5x                         │
│                                                                    │
│  ──────────────────────────────────────────────────────────────── │
│                                                                    │
│  AI RESEARCH                                                       │
│                                                                    │
│  Sarah is scaling TechCorp's engineering team post-Series B.       │
│  Recently posted about outbound hiring challenges on LinkedIn.     │
│                                                                    │
│  Talking points:                                                   │
│  • AFR feature on TechCorp's growth                                │
│  • Engineering hiring challenges (LinkedIn, Jan 15)                │
│  • Segment integration — focused on customer data                  │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

**What this answers:**
- Is this working? → Status of every prospect in the pipeline
- How well? → Full enrichment, signals, outreach history
- What next? → AI research gives talking points for meetings

---

## 4. INBOX

Every reply, every conversation, across every channel. AI suggests responses.

```
┌────────────────────────────────────────────────────────────────────┐
│  INBOX                              [All] [Needs Reply] [Meetings] │
│  ════════════════════════════════════════════════════════════════  │
│                                                                    │
│  ┌──────────────────────┬─────────────────────────────────────────┐│
│  │                      │                                         ││
│  │  ● Mike Johnson 15m  │  Mike Johnson                           ││
│  │    StartupXYZ        │  VP Sales, StartupXYZ                   ││
│  │    💼 Replied        │                                         ││
│  │    Interested        │  💼 Jan 28                              ││
│  │                      │  "Thanks for the connection! We're      ││
│  │  ● David Lee    2h   │  actually looking at this space..."     ││
│  │    Growth Co         │                                         ││
│  │    💬 Replied        │  📧 Jan 27 (You)                       ││
│  │    Interested        │  "Hi Mike, noticed StartupXYZ just      ││
│  │                      │  closed your Series A..."               ││
│  │  ○ Emma Wilson  3h   │                                         ││
│  │    Scale Labs        │  ────────────────────────────────────── ││
│  │    📧 Replied        │                                         ││
│  │    Future interest   │  🤖 SUGGESTED REPLY                     ││
│  │                      │  "Thanks Mike! Would love to show you   ││
│  │                      │  how we've helped similar Series A      ││
│  │                      │  companies book 15+ meetings/month..."  ││
│  │                      │                                         ││
│  │                      │  [Send] [Edit] [Different tone]         ││
│  │                      │                                         ││
│  └──────────────────────┴─────────────────────────────────────────┘│
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

**What this answers:**
- Is this working? → Replies are coming in across channels
- What next? → AI suggests response, one click to send

---

## 5. PERFORMANCE

Deep dive. Trends over time. Funnel conversion. Channel comparison.

```
┌────────────────────────────────────────────────────────────────────┐
│  PERFORMANCE                                    [This Month ▼]     │
│  ════════════════════════════════════════════════════════════════  │
│                                                                    │
│  FUNNEL                                                            │
│                                                                    │
│  Prospects    Contacted    Replied    Meetings    Showed    Deals  │
│  1,247    →    1,089    →    78    →     12    →    10    →   3    │
│           87%           7.2%       15.4%       83%        30%      │
│                                                                    │
│  ──────────────────────────────────────────────────────────────── │
│                                                                    │
│  CHANNEL COMPARISON                                                │
│                                                                    │
│  Channel     Sent   Reply%  Meeting%  Best For                     │
│  ───────     ────   ──────  ────────  ────────                     │
│  📧 Email    1,247  3.2%    1.8%      Opening conversations        │
│  💼 LinkedIn 89     12.3%   4.5%      Warm leads (60-84)           │
│  📞 Voice    23     34.8%   8.2%      Hot leads (85+)              │
│  💬 SMS      12     33.3%   8.3%      Follow-up after email        │
│                                                                    │
│  ──────────────────────────────────────────────────────────────── │
│                                                                    │
│  TRENDS (Last 6 Months)                                            │
│                                                                    │
│  Meetings ──────────────╭──●                                       │
│                    ╭───╯                                           │
│              ●───╯                                                 │
│         ╭───╯                                                      │
│      ●─╯                                                           │
│  Aug  Sep  Oct  Nov  Dec  Jan                                      │
│  4    6    7    9    10   12                                        │
│                                                                    │
│  Show Rate ─────────────────●────●                                 │
│                       ●────●                                       │
│                 ●────●                                              │
│            ●───╯                                                    │
│  Aug  Sep  Oct  Nov  Dec  Jan                                      │
│  70%  72%  78%  80%  82%  85%                                      │
│                                                                    │
│  ──────────────────────────────────────────────────────────────── │
│                                                                    │
│  TOP CONTENT                                                       │
│                                                                    │
│  📧 "Question about {{company}}'s growth" → 67% open, 3 meetings  │
│  📧 "Saw your Series B announcement" → 5x opens, clicked CTA      │
│  📞 Tuesday 10am calls → 2.3x connect rate                        │
│  💼 Mutual connection notes → +67% acceptance                      │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

**What this answers:**
- How well is it working? → Full funnel with conversion at every stage
- How well? → Channel-by-channel comparison shows where value comes from
- What next? → Top content shows what patterns to double down on

---

## 6. INTELLIGENCE

The page no competitor has. What the AI has learned about YOUR market.

```
┌────────────────────────────────────────────────────────────────────┐
│  🧠 INTELLIGENCE                                                   │
│  ════════════════════════════════════════════════════════════════  │
│                                                                    │
│  Your AI has analyzed 847 outreach attempts and 23 conversions.    │
│  These insights improve automatically every week.                  │
│                                                                    │
│  ──────────────────────────────────────────────────────────────── │
│                                                                    │
│  WHO RESPONDS                                      Confidence: 89% │
│                                                                    │
│  Best converting titles:                                           │
│  CTO              ████████████████████  3.2x more likely           │
│  VP Engineering   █████████████████     2.8x                       │
│  Director Ops     ████████████████      2.5x                       │
│                                                                    │
│  Best company size: 50-200 employees (2.8x)                        │
│  Best signal: Recent funding within 30 days (3.1x)                 │
│                                                                    │
│  Underperforming: Managers (0.4x), Enterprise 500+ (0.6x)         │
│                                                                    │
│  ──────────────────────────────────────────────────────────────── │
│                                                                    │
│  WHAT WORKS                                        Confidence: 84% │
│                                                                    │
│  Top subject lines:                                                │
│  "Question about {{company}}'s..."          67% open rate          │
│  "{{first_name}}, quick question"           52% open rate          │
│  "Saw {{company}} in the news"              48% open rate          │
│                                                                    │
│  ✅ Mention specific pain point: +45% reply                        │
│  ✅ Reference recent news: +38% reply                              │
│  ✅ Keep under 100 words: +28% reply                               │
│  ❌ Multiple CTAs: -35% reply                                      │
│  ❌ Formal tone: -22% reply                                        │
│                                                                    │
│  ──────────────────────────────────────────────────────────────── │
│                                                                    │
│  WHEN TO REACH OUT                                 Confidence: 91% │
│                                                                    │
│  Best days:    Tue (2.3x) │ Wed (2.1x) │ Thu (1.9x)               │
│  Best time:    9-11am AEST                                         │
│  Avoid:        Friday PM (-40%) │ Monday AM (-25%)                 │
│                                                                    │
│  ──────────────────────────────────────────────────────────────── │
│                                                                    │
│  CHANNEL PLAYBOOK                                  Confidence: 87% │
│                                                                    │
│  Hot prospects (85+):                                              │
│  Email → Voice → LinkedIn → SMS                                    │
│  Email + Voice combo = 3.2x meeting rate                           │
│                                                                    │
│  Warm prospects (60-84):                                           │
│  Email → LinkedIn → Voice                                          │
│  LinkedIn acceptance → 2.8x reply on email follow-up               │
│                                                                    │
│  Cool prospects (35-59):                                           │
│  Email → LinkedIn only                                             │
│  Voice not effective at this tier                                  │
│                                                                    │
│  ──────────────────────────────────────────────────────────────── │
│                                                                    │
│  PIPELINE QUALITY                                  Confidence: 92% │
│                                                                    │
│  Show rate: 85% (industry avg: 65%)                                │
│  Avg deal size: $45K                                               │
│  Time from meeting to deal: 23 days (was 31 last quarter)          │
│  Best converting campaign: Tech Decision Makers (15.4% to meeting) │
│                                                                    │
│  These insights automatically adjust your targeting,               │
│  timing, and channel mix every week.                               │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

**What this answers:**
- Is this working? → The AI is actively learning from your data
- How well? → Confidence scores show how reliable each insight is
- What next? → Actionable patterns: who to target, what to say, when to send

**Why this page matters:**
This is the page the client shows their boss. "Look — the AI learned that CTOs convert 3.2x better, and it automatically shifted our targeting." No competitor has anything like this.

---

## What's NOT In This Dashboard

| Excluded | Why |
|----------|-----|
| Lead counts | Commodity metric — we sell meetings |
| Credits remaining | Subscription model, not credits |
| AI costs / savings | Internal operational detail |
| Domain warmup status | Infrastructure they don't manage |
| Resource counts | Plumbing they shouldn't see |
| LinkedIn seat numbers | Operational detail |
| Phone numbers | Infrastructure |
| Allocation percentages | Replaced with priority language |

---

## API Coverage

Every section maps to existing backend endpoints:

| Section | Endpoint |
|---------|----------|
| Overview hero | `GET /reports/clients/{id}/dashboard-metrics` |
| Channel stats | `GET /reports/clients/{id}` (channel_performance) |
| Campaigns | `GET /reports/clients/{id}/campaigns/performance` |
| Campaign detail | `GET /reports/campaigns/{id}` |
| Campaign sequence | `GET /reports/campaigns/{id}/daily` |
| Prospect list | `GET /leads` with filters |
| Prospect detail | `GET /reports/leads/{id}/engagement` |
| Prospect score | Scorer engine data (lead model) |
| Inbox | `GET /reports/clients/{id}/activities` filtered to replies |
| Performance funnel | `GET /reports/clients/{id}` |
| Performance trends | `GET /reports/campaigns/{id}/daily` with date ranges |
| Top content | `GET /reports/clients/{id}/best-of` |
| Intelligence WHO | `GET /patterns/who` |
| Intelligence WHAT | `GET /patterns/what` |
| Intelligence WHEN | `GET /patterns/when` |
| Intelligence HOW | `GET /patterns/how` |
| Pipeline quality | `GET /patterns` (funnel detector) |
| Activity feed | `GET /reports/clients/{id}/activities` |
| Meetings | Meeting service data |
| ALS distribution | `GET /reports/leads/distribution` |
| Pool analytics | `GET /reports/pool/clients/{id}/analytics` |

Every section is backed by existing backend code. No new endpoints needed.
