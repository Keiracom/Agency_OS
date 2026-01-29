# Competitor Dashboard Layouts Analysis

*Based on marketing site screenshots — 2026-01-28*

---

## AiSDR Dashboard (Best Example Found)

**Screenshot:** `/competitive/screenshots/aisdr-site-1.png`

### Layout Structure

```
┌─────────────────────────────────────────────────────────────────────┐
│  [Logo]  Campaign Dashboard           [Period: Last 30 days ▼]  ○27│
├──────────┬──────────────────────────────────────────────────────────┤
│          │                                                          │
│ Dashboard│   Performance Overview                                   │
│          │   ┌──────────┐ ┌──────────┐ ┌──────────┐                │
│ Campaign │   │ 📧 1,217 │ │ 👥 903   │ │ 📅 3     │                │
│ Builder  │   │ Emails   │ │ Leads    │ │ Meetings │                │
│          │   │ Sent     │ │ Engaged  │ │ Booked   │                │
│ Campaigns│   └──────────┘ └──────────┘ └──────────┘                │
│          │   ┌──────────┐ ┌──────────┐ ┌──────────┐                │
│ Leads    │   │ 📊 7.12% │ │ 📬 61.23%│ │ ✅ 2.17% │                │
│          │   │ Response │ │ Open     │ │ Positive │                │
│ Personas │   │ Rate     │ │ Rate     │ │ Response │                │
│          │   └──────────┘ └──────────┘ └──────────┘                │
│ Settings │                                                          │
│          │                                                          │
│ Admin    │                                                          │
│          │                                                          │
└──────────┴──────────────────────────────────────────────────────────┘
```

### Key Data Points Displayed
1. **Hero metric** — Circular badge showing "27 Emails sent per day"
2. **6 KPI cards** (2 rows × 3):
   - Total Emails Sent (1,217)
   - Leads Engaged (903)
   - Total Meetings Booked (3)
   - Response Rate (7.12%)
   - Open Rate (61.23%)
   - Positive Response Rate (2.17%)
3. **Period selector** — Last 30 days dropdown
4. **Campaign filter** — All campaigns dropdown

### Visual Design
- Dark sidebar (navy blue)
- Light content area
- Purple/blue accent colors
- Colored icon backgrounds in KPI cards
- Real-time notification popup for meeting bookings

---

## Artisan Dashboard (Partial View)

**Screenshot:** `/competitive/screenshots/artisan-site-1.png`

### Layout Structure (from mockup)
```
┌─────────────────────────────────────────────────────────────────────┐
│  [Artisan Logo]                                                     │
├──────────┬──────────────────────────────────────────────────────────┤
│          │                                                          │
│          │   Inbox                                                  │
│ [Nav]    │   ┌────────────────────────────────────────────────┐    │
│          │   │ Contact list with messages                     │    │
│          │   │ - Prospect name                                │    │
│          │   │ - Preview of conversation                      │    │
│          │   │ - Timestamp                                    │    │
│          │   └────────────────────────────────────────────────┘    │
│          │                                                          │
│          │   [Contact detail panel with avatar: "Blake"]           │
│          │                                                          │
└──────────┴──────────────────────────────────────────────────────────┘
```

### Key Elements
- **Unified inbox** as primary view
- Contact list with conversation previews
- Contact detail panel with avatar
- Dark theme with purple gradient accents

---

## 11x (Limited Data)

**Screenshot:** `/competitive/screenshots/11x-site-1.png`

### What We Can See
- "Alice the SDR" messaging card with email preview
- "Ask Julian" chat widget in bottom-right corner
- Enterprise customer logos (Xerox, Sage, Questex, etc.)

### Missing
- No dashboard screenshots available on public marketing site
- Platform page returns 404

---

## Regie.ai (No Dashboard)

**Screenshot:** `/competitive/screenshots/regie-site-1.png`

- Footer only captured
- No dashboard mockups on marketing site
- Hides actual UI behind demo requests

---

## Instantly (No Dashboard)

**Screenshots:** Both return 404 errors
- Features page moved/removed
- Dashboard page requires login

---

## Key Patterns to Steal

### 1. KPI Card Layout (AiSDR)
```
┌───────────────────┐
│  [Icon]           │
│  1,217            │  ← Large number
│  Total Emails     │  ← Label below
│  Sent             │
└───────────────────┘
```
**Why it works:** Scannable at a glance, icon provides context

### 2. Hero Metric Badge (AiSDR)
```
        ┌─────┐
        │  27 │  ← Primary action metric
        │ /day│
        └─────┘
```
**Why it works:** Single most important number impossible to miss

### 3. Real-time Notifications (AiSDR)
```
┌─────────────────────────────────────┐
│ 🎉 Meeting booked with m.smith!    │
│    [Go to campaign]                 │
└─────────────────────────────────────┘
```
**Why it works:** Creates "wow" moment, proves system is working

### 4. Unified Inbox (Artisan)
- Conversation-centric view
- Mimics email/Slack UX users already know
- Activity feels tangible, not abstract

---

## What Agency OS Should Display

Based on competitor analysis + your spec:

### Above the Fold
| Priority | Metric | Why |
|----------|--------|-----|
| 1 | **Meetings Booked** | Primary outcome clients pay for |
| 2 | **Show Rate** | Quality indicator (your differentiator) |
| 3 | **On Track Indicator** | Instant confidence/anxiety check |

### Secondary KPIs (2nd row)
| Metric | Notes |
|--------|-------|
| Active Sequences | Proof of work |
| Reply Rate | Engagement quality |
| This Week's Activity | Momentum indicator |

### What NOT to Show (per your spec)
- ❌ Lead counts
- ❌ Credits remaining
- ❌ Allocation percentages

### Visual Elements to Include
- ✅ Real-time activity feed (proof of work)
- ✅ Meeting notification popups
- ✅ ALS score visualization (your secret sauce)
- ✅ Campaign priority sliders

---

## Screenshots Location
All captured screenshots saved to:
`/home/elliotbot/clawd/competitive/screenshots/`

Files:
- `artisan-site-1.png`, `artisan-site-2.png`
- `11x-site-1.png`, `11x-site-2.png`
- `aisdr-site-1.png`, `aisdr-site-2.png`
- `regie-site-1.png`, `regie-site-2.png`
- `instantly-site-1.png`, `instantly-site-2.png`
