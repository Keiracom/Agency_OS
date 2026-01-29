# Agency OS — Comprehensive Dashboard Specification

*Every page. Every section. All the power visible.*

---

## Navigation Structure

```
┌─────────────────────────────────────────────────────────────────────┐
│  [AGENCY OS LOGO]                                    [Search] [👤]  │
├──────────────┬──────────────────────────────────────────────────────┤
│              │                                                      │
│  📊 Overview │  [Main Content Area]                                 │
│              │                                                      │
│  🎯 Campaigns│                                                      │
│              │                                                      │
│  👥 Leads    │                                                      │
│              │                                                      │
│  📬 Inbox    │                                                      │
│              │                                                      │
│  📈 Analytics│                                                      │
│              │                                                      │
│  🧠 Intel    │  ← NEW: Conversion Intelligence                      │
│              │                                                      │
│  ⚡ Resources│  ← NEW: Infrastructure view                          │
│              │                                                      │
│  ⚙️ Settings │                                                      │
│              │                                                      │
└──────────────┴──────────────────────────────────────────────────────┘
```

---

## 1. OVERVIEW PAGE

### 1.1 Hero Section
```
┌────────────────────────────────────────────────────────────────────────┐
│                                                                        │
│   🎯 12 MEETINGS                    85% SHOW RATE                     │
│      ████████████░░░░               ████████████████░░                │
│      On track for 15-25             +5% vs last month                 │
│                                                                        │
│   ──────────────────────────────────────────────────────────────────  │
│                                                                        │
│   CHANNELS ACTIVE                                                      │
│   📧 1,247    💼 89     📞 23     💬 12     📬 0                      │
│   emails      LinkedIn  calls     SMS       mail                       │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

### 1.2 AI Insight Banner (Rotating)
```
┌────────────────────────────────────────────────────────────────────────┐
│  🧠 AI INSIGHT                                                         │
│  "VP titles convert 3.2x better this month. We're prioritizing them." │
│                                                         [View Intel →] │
└────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Campaign Priority Cards
```
┌────────────────────────────────────────────────────────────────────────┐
│  YOUR CAMPAIGNS                                           Total: 100% │
│  ────────────────────────────────────────────────────────────────────  │
│                                                                        │
│  Tech Decision Makers (AI)                                             │
│  ●━━━━━━━━━━━━━━━━━━━━━━━━●━━━━━━━━━━━━○  40%                         │
│  📧💼📞 │ 6 meetings │ 3.8% reply │ ALS avg: 72                       │
│                                                                        │
│  Series A Startups (AI)                                                │
│  ●━━━━━━━━━━━━━━━━━━●━━━━━━━━━━━━━━━━━━○  35%                         │
│  📧💼   │ 4 meetings │ 2.9% reply │ ALS avg: 68                       │
│                                                                        │
│  My Custom Campaign                                                    │
│  ●━━━━━━━━━━━━━●━━━━━━━━━━━━━━━━━━━━━━━○  25%                         │
│  📧💬   │ 2 meetings │ 1.8% reply │ ALS avg: 54                       │
│                                                                        │
│                                              [Confirm & Activate]      │
└────────────────────────────────────────────────────────────────────────┘
```

### 1.4 Activity + Meetings Row
```
┌──────────────────────────────────────────┬─────────────────────────────┐
│  RECENT ACTIVITY                    Live │  UPCOMING MEETINGS          │
│  ─────────────────────────────────────── │  ───────────────────────────│
│                                          │                             │
│  📧 Sarah Chen opened email       2m ago │  Today 2:00 PM              │
│  💼 Mike Johnson replied         15m ago │  Sarah Chen, TechCorp       │
│  📞 Lisa Park - meeting booked    1h ago │  Discovery • 30min          │
│  💬 David Lee replied             2h ago │                             │
│  📧 Emma Wilson clicked link      3h ago │  Tomorrow 10:00 AM          │
│                                          │  Mike Johnson, StartupXYZ   │
│  [View all activity →]                   │  Demo • 45min               │
│                                          │                             │
└──────────────────────────────────────────┴─────────────────────────────┘
```

### 1.5 Lead Pool Health (Mini)
```
┌────────────────────────────────────────────────────────────────────────┐
│  LEAD POOL                                               [View all →]  │
│  ────────────────────────────────────────────────────────────────────  │
│                                                                        │
│  Hot ██░░░░░░░░░░░░░░░░░░  12 (1%)   Warm █████████░░░░░░  445 (38%)  │
│  Cool ████████░░░░░░░░░░░  389 (33%)  Cold ██████░░░░░░░░  267 (23%) │
│                                                                        │
│  ✅ 92% verified │ ⚡ 34 funding signals │ 📈 89 hiring intent         │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. CAMPAIGNS PAGE

### 2.1 Campaign List View
```
┌────────────────────────────────────────────────────────────────────────┐
│  CAMPAIGNS                                         [+ New Campaign]    │
│  ────────────────────────────────────────────────────────────────────  │
│                                                                        │
│  ┌─ Filters ──────────────────────────────────────────────────────┐   │
│  │ Status: [All ▼]  Type: [All ▼]  Channel: [All ▼]  Sort: [ALS ▼]│   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │ ✨ Tech Decision Makers                           AI CAMPAIGN  │   │
│  │ ────────────────────────────────────────────────────────────── │   │
│  │ Channels: 📧💼📞   Status: ● Active   Priority: 40%           │   │
│  │                                                                │   │
│  │ ┌──────────┬──────────┬──────────┬──────────┬──────────┐      │   │
│  │ │ 312      │ 6        │ 3.8%     │ 72       │ $1,247   │      │   │
│  │ │ Leads    │ Meetings │ Reply    │ Avg ALS  │ Pipeline │      │   │
│  │ └──────────┴──────────┴──────────┴──────────┴──────────┘      │   │
│  │                                                                │   │
│  │ SEQUENCE PROGRESS                                              │   │
│  │ Step 1 ████████████  Step 2 ████████░░  Step 3 █████░░░░░     │   │
│  │ 312 sent             198 sent          89 sent                 │   │
│  │                                                                │   │
│  │ 🧠 Intel: "Tuesday 10am sends have 2.3x reply rate"           │   │
│  │                                              [View Details →]  │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  [More campaigns...]                                                   │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Campaign Detail View
```
┌────────────────────────────────────────────────────────────────────────┐
│  ← Back to Campaigns                                                   │
│                                                                        │
│  TECH DECISION MAKERS                                    ✨ AI CAMPAIGN│
│  ════════════════════════════════════════════════════════════════════ │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ PERFORMANCE                                      Last 30 days ▼ │  │
│  │ ─────────────────────────────────────────────────────────────── │  │
│  │                                                                 │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │  │
│  │  │    6     │ │   3.8%   │ │   61%    │ │    72    │          │  │
│  │  │ Meetings │ │ Reply    │ │ Open     │ │ Avg ALS  │          │  │
│  │  │ Booked   │ │ Rate     │ │ Rate     │ │ Score    │          │  │
│  │  │ +2 ↑     │ │ +0.5% ↑  │ │ -3% ↓    │ │ +4 ↑     │          │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │  │
│  │                                                                 │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ SEQUENCE BREAKDOWN                                              │  │
│  │ ─────────────────────────────────────────────────────────────── │  │
│  │                                                                 │  │
│  │  Step 1: Email (Day 0)                                          │  │
│  │  ████████████████████ 312/312 sent                              │  │
│  │  Open: 61% │ Reply: 2.1% │ Click: 4.3%                         │  │
│  │  🧠 Best subject: "Question about {{company}}'s growth"        │  │
│  │                                                                 │  │
│  │  Step 2: Voice (Day 3)                                          │  │
│  │  ████████████████░░░░ 198/247 attempted                         │  │
│  │  Connect: 34% │ Meeting: 8.2% │ Voicemail: 52%                  │  │
│  │  🧠 Best time: 10am-11am AEST                                   │  │
│  │                                                                 │  │
│  │  Step 3: LinkedIn (Day 5)                                       │  │
│  │  ██████████░░░░░░░░░░ 89/178 sent                               │  │
│  │  Accept: 42% │ Reply: 12.3%                                     │  │
│  │  🧠 Connection note mentioning mutual works +67%                │  │
│  │                                                                 │  │
│  │  Step 4: Email (Day 8)          ░░░░░░░░░░ Upcoming             │  │
│  │  Step 5: SMS (Day 12)           ░░░░░░░░░░ Upcoming             │  │
│  │                                                                 │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ CHANNEL PERFORMANCE                                             │  │
│  │ ─────────────────────────────────────────────────────────────── │  │
│  │                                                                 │  │
│  │  📧 Email       ████████████████████░░░░  78% of sequence      │  │
│  │                 1,247 sent │ 61% open │ 3.2% reply             │  │
│  │                                                                 │  │
│  │  📞 Voice       ████████████░░░░░░░░░░░░  45% of eligible      │  │
│  │                 198 calls │ 34% connect │ 8.2% meeting         │  │
│  │                                                                 │  │
│  │  💼 LinkedIn    ██████████░░░░░░░░░░░░░░  38% of eligible      │  │
│  │                 89 requests │ 42% accept │ 12.3% reply         │  │
│  │                                                                 │  │
│  │  💬 SMS         ░░░░░░░░░░░░░░░░░░░░░░░░  Not yet (Step 5)     │  │
│  │                 Hot leads only (ALS 85+)                        │  │
│  │                                                                 │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ AI INSIGHTS FOR THIS CAMPAIGN                                   │  │
│  │ ─────────────────────────────────────────────────────────────── │  │
│  │                                                                 │  │
│  │  💡 WHO: CTOs convert 2.1x better than VPs in this campaign    │  │
│  │  💡 WHAT: Mentioning "scaling" in subject +45% open rate       │  │
│  │  💡 WHEN: Tue-Thu 9-11am optimal. Avoid Friday PM (-40%)       │  │
│  │  💡 HOW: Email→Voice combo: 3.2x more meetings than email only │  │
│  │                                                                 │  │
│  │                                         [Apply Recommendations] │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. LEADS PAGE

### 3.1 Lead List View
```
┌────────────────────────────────────────────────────────────────────────┐
│  LEADS                                                  [+ Import]     │
│  ────────────────────────────────────────────────────────────────────  │
│                                                                        │
│  ┌─ Filters ──────────────────────────────────────────────────────┐   │
│  │ ALS: [All ▼]  Campaign: [All ▼]  Status: [All ▼]  Search: [__]│   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │ ■ │ Lead           │ Company      │ ALS │ Status    │ Channel │   │
│  ├───┼────────────────┼──────────────┼─────┼───────────┼─────────┤   │
│  │ □ │ 🔥 Sarah Chen  │ TechCorp     │ 92  │ Meeting   │ 📧📞💼 │   │
│  │   │ CTO            │ $50M ARR     │     │ booked    │         │   │
│  │   │ ⚡ Recent funding │ 🔧 React  │     │           │         │   │
│  ├───┼────────────────┼──────────────┼─────┼───────────┼─────────┤   │
│  │ □ │ 🟠 Mike Johnson│ StartupXYZ   │ 78  │ Replied   │ 📧💼   │   │
│  │   │ VP Sales       │ Series A     │     │ interested│         │   │
│  │   │ 📈 Hiring +5   │              │     │           │         │   │
│  ├───┼────────────────┼──────────────┼─────┼───────────┼─────────┤   │
│  │ □ │ 🟡 Lisa Park   │ Acme Inc     │ 65  │ In        │ 📧      │   │
│  │   │ Director Ops   │ Enterprise   │     │ sequence  │         │   │
│  │   │                │              │     │ Step 2/5  │         │   │
│  └───┴────────────────┴──────────────┴─────┴───────────┴─────────┘   │
│                                                                        │
│  Showing 1-25 of 1,247 leads                        [← 1 2 3 ... →]   │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Lead Detail View
```
┌────────────────────────────────────────────────────────────────────────┐
│  ← Back to Leads                                                       │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                                                                  │ │
│  │  [Avatar]  SARAH CHEN                              ALS: 92 🔥   │ │
│  │            Chief Technology Officer                HOT LEAD     │ │
│  │            TechCorp                                              │ │
│  │                                                                  │ │
│  │  📧 sarah@techcorp.com (verified ✓)                             │ │
│  │  💼 linkedin.com/in/sarahchen                                   │ │
│  │  📞 +61 412 345 678                                             │ │
│  │                                                                  │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│  ┌───────────┬───────────┬───────────┬───────────┬───────────┐        │
│  │ ENRICHMENT│ ACTIVITY  │ SCORING   │ TIMELINE  │ AI RESEARCH│        │
│  └───────────┴───────────┴───────────┴───────────┴───────────┘        │
│                                                                        │
│  ═══════════════════════════════════════════════════════════════════  │
│                                                                        │
│  ENRICHMENT DATA (47 fields populated)                                 │
│  ─────────────────────────────────────────────────────────────────────│
│                                                                        │
│  PERSON                           │  COMPANY                           │
│  ─────────────────────────────────│──────────────────────────────────  │
│  Title: CTO                       │  Name: TechCorp                    │
│  Seniority: C-Suite ★            │  Industry: Technology              │
│  Tenure: 3.2 years                │  Employees: 150-500                │
│  LinkedIn: 2,340 connections      │  Revenue: $50M ARR                 │
│  Email verified: Yes ✓            │  Funding: Series B ($25M) ★       │
│  Phone verified: Yes ✓            │  Founded: 2018                     │
│                                   │  Location: Sydney, AU              │
│  SIGNALS                          │                                    │
│  ─────────────────────────────────│  TECH STACK                       │
│  ⚡ Recent funding (14 days)      │  ─────────────────────────────────│
│  📈 Hiring: +5 engineers          │  React, Node.js, AWS, Postgres    │
│  🔧 Tech change: Added Segment    │  Segment (new), HubSpot           │
│  📰 News: Featured in AFR         │                                    │
│                                                                        │
│  ═══════════════════════════════════════════════════════════════════  │
│                                                                        │
│  ALS SCORE BREAKDOWN                                                   │
│  ─────────────────────────────────────────────────────────────────────│
│                                                                        │
│  Total: 92/100                                                         │
│                                                                        │
│  Data Quality    ████████████████████  18/20  (verified, complete)    │
│  Authority       █████████████████████████  24/25  (CTO, C-Suite)     │
│  Company Fit     ████████████████████████  23/25  (revenue, tech)     │
│  Timing          ██████████████████████  14/15  (funding, hiring)     │
│  Risk            █████████████████████  13/15  (no deductions)        │
│                                                                        │
│  ★ SDK deep research applied (Hot lead)                               │
│                                                                        │
│  ═══════════════════════════════════════════════════════════════════  │
│                                                                        │
│  OUTREACH TIMELINE                                                     │
│  ─────────────────────────────────────────────────────────────────────│
│                                                                        │
│  Jan 28  📧 Email sent: "Question about TechCorp's growth"            │
│          └─ Opened (3x) │ Clicked case study link                     │
│                                                                        │
│  Jan 25  📞 Voice call: Connected, 4m 23s                             │
│          └─ Positive, scheduled follow-up                              │
│                                                                        │
│  Jan 23  💼 LinkedIn connection accepted                               │
│          └─ Replied: "Thanks for reaching out!"                        │
│                                                                        │
│  Jan 20  📧 Initial email sent                                         │
│          └─ Opened (5x)                                                │
│                                                                        │
│  ═══════════════════════════════════════════════════════════════════  │
│                                                                        │
│  AI RESEARCH (SDK)                                                     │
│  ─────────────────────────────────────────────────────────────────────│
│                                                                        │
│  📝 SUMMARY                                                            │
│  Sarah Chen is a technical founder-turned-CTO who joined TechCorp     │
│  after their Series A. She's focused on scaling the engineering team  │
│  and recently posted about challenges with outbound hiring.           │
│                                                                        │
│  💡 TALKING POINTS                                                     │
│  • Recent AFR feature on TechCorp's growth trajectory                 │
│  • Engineering hiring challenges (LinkedIn post, Jan 15)              │
│  • Segment integration suggests focus on customer data                │
│                                                                        │
│  ⚠️ AVOID                                                              │
│  • Generic "scale your business" messaging                            │
│  • Competitor mentions (they use HubSpot, not Salesforce)             │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. INBOX PAGE

### 4.1 Unified Inbox
```
┌────────────────────────────────────────────────────────────────────────┐
│  INBOX                                              [All] [Needs Reply]│
│  ════════════════════════════════════════════════════════════════════ │
│                                                                        │
│  ┌─────────────────────────────────┬──────────────────────────────────┐│
│  │ CONVERSATIONS                   │ CONVERSATION                     ││
│  │ ───────────────────────────     │ ───────────────────────────────  ││
│  │                                 │                                  ││
│  │ ● Mike Johnson          15m ago │ Mike Johnson                     ││
│  │   StartupXYZ                    │ VP Sales, StartupXYZ             ││
│  │   💼 "Thanks for the connect..."│ ─────────────────────────────    ││
│  │   🏷️ Interested                 │                                  ││
│  │                                 │ 💼 Jan 28, 10:15am               ││
│  │ ● Sarah Chen            1h ago  │ "Thanks for the connection!      ││
│  │   TechCorp                      │ I saw you work with tech         ││
│  │   📧 "Re: Question about..."    │ companies. We're actually        ││
│  │   🏷️ Meeting Booked             │ looking at this space..."        ││
│  │                                 │                                  ││
│  │ ○ David Lee             2h ago  │ ─────────────────────────────    ││
│  │   Growth Co                     │                                  ││
│  │   💬 "Interested in learning..."│ 📧 Jan 27, 3:00pm (You)          ││
│  │   🏷️ Interested                 │ "Hi Mike, I noticed StartupXYZ   ││
│  │                                 │ just closed your Series A..."    ││
│  │ ○ Emma Wilson           3h ago  │                                  ││
│  │   Scale Labs                    │ ─────────────────────────────    ││
│  │   📧 "Not right now but..."     │                                  ││
│  │   🏷️ Future Interest            │ 🤖 AI SUGGESTED REPLY            ││
│  │                                 │ "Thanks Mike! I'd love to show   ││
│  │                                 │ you how we've helped similar     ││
│  │                                 │ Series A companies..."           ││
│  │                                 │                                  ││
│  │                                 │ [Edit] [Send] [Different tone]   ││
│  │                                 │                                  ││
│  └─────────────────────────────────┴──────────────────────────────────┘│
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 5. ANALYTICS PAGE

### 5.1 Performance Dashboard
```
┌────────────────────────────────────────────────────────────────────────┐
│  ANALYTICS                                          [This Month ▼]     │
│  ════════════════════════════════════════════════════════════════════ │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ FUNNEL OVERVIEW                                                 │  │
│  │ ───────────────────────────────────────────────────────────────│  │
│  │                                                                 │  │
│  │  Leads      Contacted    Replied    Meetings    Showed    Deals │  │
│  │  1,247  →    1,089    →   78    →     12    →    10    →   3   │  │
│  │          87%          7.2%       15.4%       83%        30%     │  │
│  │                                                                 │  │
│  │  ████████████████████████████████████████████████░░░░░░░░░░░   │  │
│  │                                                                 │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌──────────────────────────┬──────────────────────────────────────┐  │
│  │ CHANNEL BREAKDOWN        │ TREND (Last 6 Months)               │  │
│  │ ────────────────────     │ ─────────────────────────────────── │  │
│  │                          │                                      │  │
│  │  📧 Email                │      Meetings Booked                 │  │
│  │  Sent: 1,247             │                    ╭─●               │  │
│  │  Open: 61%               │               ╭───╯                  │  │
│  │  Reply: 3.2%             │          ●───╯                       │  │
│  │  Meeting: 1.8%           │     ╭───╯                            │  │
│  │                          │  ●─╯                                 │  │
│  │  📞 Voice                │  Aug Sep Oct Nov Dec Jan             │  │
│  │  Calls: 198              │                                      │  │
│  │  Connect: 34%            │  Show Rate                           │  │
│  │  Meeting: 8.2%           │                         ●────●       │  │
│  │                          │               ●────●───╯             │  │
│  │  💼 LinkedIn             │     ●────●───╯                       │  │
│  │  Sent: 89                │  ●─╯                                 │  │
│  │  Accept: 42%             │  Aug Sep Oct Nov Dec Jan             │  │
│  │  Reply: 12.3%            │  70% 72% 78% 80% 82% 85%             │  │
│  │                          │                                      │  │
│  └──────────────────────────┴──────────────────────────────────────┘  │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ TOP PERFORMING                                                  │  │
│  │ ───────────────────────────────────────────────────────────────│  │
│  │                                                                 │  │
│  │  Best Campaign: Tech Decision Makers (3.8% reply, 6 meetings)  │  │
│  │  Best Channel: Voice for Hot leads (8.2% meeting rate)         │  │
│  │  Best Day: Tuesday (2.3x avg reply rate)                       │  │
│  │  Best Time: 10am AEST (+45% vs afternoon)                      │  │
│  │  Best Subject: Question format (+67% open rate)                │  │
│  │                                                                 │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 6. INTEL PAGE (NEW — The Differentiator)

### 6.1 Conversion Intelligence Dashboard
```
┌────────────────────────────────────────────────────────────────────────┐
│  🧠 CONVERSION INTELLIGENCE                              System Active │
│  ════════════════════════════════════════════════════════════════════ │
│                                                                        │
│  Your AI has learned from 847 outreach attempts and 23 conversions    │
│  Last learning cycle: 2 hours ago                                      │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ WHO CONVERTS                                    Confidence: 89% │  │
│  │ ───────────────────────────────────────────────────────────────│  │
│  │                                                                 │  │
│  │  TOP CONVERTING ATTRIBUTES                                      │  │
│  │                                                                 │  │
│  │  Title contains "CTO"           ████████████████████  3.2x     │  │
│  │  Company size 50-200            █████████████████     2.8x     │  │
│  │  Series A/B funding             ████████████████      2.5x     │  │
│  │  Seniority: C-Suite             ███████████████       2.3x     │  │
│  │  Industry: Technology           ██████████████        2.1x     │  │
│  │                                                                 │  │
│  │  UNDERPERFORMING                                                │  │
│  │  Title contains "Manager"       ██░░░░░░░░░░░░░░░░   0.4x     │  │
│  │  Company size 500+              ████░░░░░░░░░░░░░░   0.6x     │  │
│  │                                                                 │  │
│  │  💡 RECOMMENDATION: Shift 15% priority from enterprise to SMB  │  │
│  │                                              [Apply to ICP →]   │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ WHAT WORKS                                      Confidence: 84% │  │
│  │ ───────────────────────────────────────────────────────────────│  │
│  │                                                                 │  │
│  │  SUBJECT LINES                                                  │  │
│  │  "Question about {{company}}'s..."      ████████████████  67%  │  │
│  │  "{{first_name}}, quick question"       █████████████     52%  │  │
│  │  "Saw {{company}} in the news"          ████████████      48%  │  │
│  │  Generic greeting                       ████░░░░░░░░░     23%  │  │
│  │                                                                 │  │
│  │  CONTENT PATTERNS                                               │  │
│  │  ✅ Mention specific pain point: +45% reply                    │  │
│  │  ✅ Reference recent news/funding: +38% reply                  │  │
│  │  ✅ Short emails (< 100 words): +28% reply                     │  │
│  │  ❌ Multiple CTAs: -35% reply                                  │  │
│  │  ❌ Formal tone: -22% reply                                    │  │
│  │                                                                 │  │
│  │                                         [Update Content Rules →]│  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ WHEN TO REACH OUT                               Confidence: 91% │  │
│  │ ───────────────────────────────────────────────────────────────│  │
│  │                                                                 │  │
│  │  BEST DAYS                     BEST TIMES (AEST)                │  │
│  │                                                                 │  │
│  │  Mon ████████░░░░  1.2x       6am  ░░░░░░░░░░                  │  │
│  │  Tue ████████████  2.3x       9am  ████████████████  Peak     │  │
│  │  Wed █████████████ 2.1x       12pm ████████████░░░░            │  │
│  │  Thu ████████████  1.9x       3pm  ████████░░░░░░░░            │  │
│  │  Fri ████░░░░░░░░  0.6x       6pm  ██░░░░░░░░░░░░░░            │  │
│  │                                                                 │  │
│  │  ⚠️ AVOID: Friday afternoons (-40%), Monday mornings (-25%)    │  │
│  │                                                                 │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ HOW TO REACH THEM                               Confidence: 87% │  │
│  │ ───────────────────────────────────────────────────────────────│  │
│  │                                                                 │  │
│  │  CHANNEL EFFECTIVENESS BY ALS TIER                              │  │
│  │                                                                 │  │
│  │  Hot (85+)                                                      │  │
│  │  📧→📞→💼→💬  Email→Voice→LinkedIn→SMS                         │  │
│  │  Best combo: Email + Voice = 3.2x meeting rate                 │  │
│  │                                                                 │  │
│  │  Warm (60-84)                                                   │  │
│  │  📧→💼→📞     Email→LinkedIn→Voice                              │  │
│  │  LinkedIn acceptance leads to 2.8x reply on follow-up          │  │
│  │                                                                 │  │
│  │  Cool (35-59)                                                   │  │
│  │  📧→💼        Email→LinkedIn only                               │  │
│  │  Voice not cost-effective at this tier                         │  │
│  │                                                                 │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ FUNNEL HEALTH                                   Confidence: 92% │  │
│  │ ───────────────────────────────────────────────────────────────│  │
│  │                                                                 │  │
│  │  Show Rate:     85% ████████████████████░░░░  (+5% vs avg)     │  │
│  │  Deal Rate:     30% ██████████░░░░░░░░░░░░░░  (industry: 25%)  │  │
│  │  Avg Deal Size: $45K                                            │  │
│  │  Time to Close: 23 days (improving from 31 days)               │  │
│  │                                                                 │  │
│  │  📈 TREND: Your funnel efficiency improving month-over-month   │  │
│  │                                                                 │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 7. RESOURCES PAGE (NEW — Infrastructure Visibility)

### 7.1 Resource Dashboard
```
┌────────────────────────────────────────────────────────────────────────┐
│  ⚡ RESOURCES                                           All Healthy ● │
│  ════════════════════════════════════════════════════════════════════ │
│                                                                        │
│  Your outreach infrastructure. Managed automatically by Agency OS.     │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ EMAIL DOMAINS                                                   │  │
│  │ ───────────────────────────────────────────────────────────────│  │
│  │                                                                 │  │
│  │  Domain              Health    Warmup    Today    Limit         │  │
│  │  ────────────────────────────────────────────────────────────  │  │
│  │  outreach1.co        ● 98%     ✓ Done    42/50   ████████████  │  │
│  │  outreach2.co        ● 95%     ✓ Done    38/50   ██████████░░  │  │
│  │  outreach3.co        ● 92%     ✓ Done    45/50   █████████████ │  │
│  │  outreach4.co        ● 88%     Day 18    28/50   ████████░░░░  │  │
│  │  outreach5.co        ○ 45%     Day 7     10/50   ███░░░░░░░░░  │  │
│  │                                                                 │  │
│  │  Total Capacity: 163/250 emails sent today (65%)               │  │
│  │                                                                 │  │
│  │  ⚠️ outreach5.co still warming. Full capacity in 14 days.     │  │
│  │                                                                 │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ PHONE NUMBERS                                                   │  │
│  │ ───────────────────────────────────────────────────────────────│  │
│  │                                                                 │  │
│  │  Number            Type     Today     Limit     Status          │  │
│  │  ──────────────────────────────────────────────────────────────│  │
│  │  +61 2 4012 6220   Voice    23/50     ████████░░  ● Active     │  │
│  │  +61 2 4012 6221   SMS      12/100    ███░░░░░░░  ● Active     │  │
│  │                                                                 │  │
│  │  DNCR Compliance: ✓ All numbers checked against Do Not Call    │  │
│  │                                                                 │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ LINKEDIN SEATS                                                  │  │
│  │ ───────────────────────────────────────────────────────────────│  │
│  │                                                                 │  │
│  │  Seat              Connections Today    Limit     Status        │  │
│  │  ──────────────────────────────────────────────────────────────│  │
│  │  Agency Seat 1     15/20               ██████████░  ● Active   │  │
│  │  Agency Seat 2     12/20               ████████░░░  ● Active   │  │
│  │  Agency Seat 3     18/20               ███████████  ● Active   │  │
│  │  Agency Seat 4     8/20                █████░░░░░░  ● Active   │  │
│  │                                                                 │  │
│  │  Total: 53/80 connections today (66%)                          │  │
│  │                                                                 │  │
│  │  ⚠️ Conservative limits to avoid LinkedIn flags.               │  │
│  │                                                                 │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ AI EFFICIENCY                                                   │  │
│  │ ───────────────────────────────────────────────────────────────│  │
│  │                                                                 │  │
│  │  This Month                                                     │  │
│  │                                                                 │  │
│  │  Smart Prompts:     1,089 leads     $43.56    ($0.04/lead)     │  │
│  │  SDK Research:      12 Hot leads    $19.80    ($1.65/lead)     │  │
│  │  Reply Handling:    78 replies      $12.48    ($0.16/reply)    │  │
│  │  ────────────────────────────────────────────────────────────  │  │
│  │  Total:                             $75.84                      │  │
│  │                                                                 │  │
│  │  💰 SAVINGS                                                     │  │
│  │  If SDK everywhere: $224.67                                    │  │
│  │  You saved: $148.83 (66%)                                      │  │
│  │                                                                 │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 8. SETTINGS PAGE

### 8.1 Settings Hub
```
┌────────────────────────────────────────────────────────────────────────┐
│  SETTINGS                                                              │
│  ════════════════════════════════════════════════════════════════════ │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ ICP CONFIGURATION                                               │  │
│  │ ───────────────────────────────────────────────────────────────│  │
│  │                                                                 │  │
│  │  Target Titles        [CTO, VP Engineering, Director...]       │  │
│  │  Industries           [Technology, SaaS, FinTech]              │  │
│  │  Company Size         [50-500 employees]                       │  │
│  │  Revenue              [$5M - $50M ARR]                         │  │
│  │  Geography            [Australia, New Zealand]                 │  │
│  │                                                                 │  │
│  │  🧠 AI Suggestion: Add "Head of Growth" — converts 2.1x       │  │
│  │                                                                 │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ CRM INTEGRATION                                                 │  │
│  │ ───────────────────────────────────────────────────────────────│  │
│  │                                                                 │  │
│  │  Connected: HubSpot ✓                                          │  │
│  │  Last sync: 2 hours ago                                        │  │
│  │  Deals pushed: 3 this month                                    │  │
│  │                                                                 │  │
│  │  [Reconnect] [Change CRM]                                      │  │
│  │                                                                 │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ NOTIFICATIONS                                                   │  │
│  │ ───────────────────────────────────────────────────────────────│  │
│  │                                                                 │  │
│  │  ✓ Meeting booked                    Email + Slack             │  │
│  │  ✓ Hot lead reply                    Email + Slack             │  │
│  │  ✓ Weekly performance digest         Email                     │  │
│  │  ○ Every reply                       Off                       │  │
│  │                                                                 │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Summary: What This Spec Delivers

| Page | What It Shows | Backend Power Surfaced |
|------|---------------|------------------------|
| **Overview** | Hero KPIs, campaigns, activity | Multi-channel stats, AI insights |
| **Campaigns** | Campaign details, sequence progress | Channel breakdown, AI recommendations |
| **Leads** | Lead details, enrichment, scoring | 50+ fields, ALS breakdown, SDK research |
| **Inbox** | Unified conversations, AI replies | Closer engine, intent classification |
| **Analytics** | Funnel, trends, performance | Channel comparison, best performers |
| **Intel** | CIS 5 detectors visualized | WHO/WHAT/WHEN/HOW/FUNNEL learning |
| **Resources** | Domains, phones, LinkedIn, AI cost | Resource pool, warmup, efficiency |
| **Settings** | ICP, CRM, notifications | AI-powered suggestions |

**Total new visibility:** 
- 5 CIS detectors surfaced
- 9 engines visible through their outputs
- 50+ enrichment fields accessible
- Resource management transparent
- AI cost optimization visible

This is the Bloomberg Terminal for Client Acquisition.
