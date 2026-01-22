# Dashboard Redesign Overview

**Status:** Planning
**Last Updated:** 2026-01-22

---

## The Problem

Current dashboard uses **commodity language** that devalues our service:
- "1,250 leads remaining" → Client thinks: "I'm paying per lead"
- "Credits" → Transactional, not partnership
- Focus on inputs (leads) instead of outcomes (meetings)

**We are not a lead vendor. We are a meetings-as-a-service platform.**

---

## Design Principles

### 1. Outcome-Focused
Show what clients actually care about:
- **Meetings booked** (not leads contacted)
- **Show rate** (who showed up)
- **Conversion rate** (meetings → deals)

### 2. Transparency as Proof of Work
When results fluctuate, activity data explains why:
- "We contacted 1,200 prospects, got 45 replies... maybe ICP needs adjusting?"
- Activity protects us in slow months - shows effort, invites collaboration

### 3. No Commodity Language
| Don't Say | Say Instead |
|-----------|-------------|
| "Credits remaining" | Remove entirely, or "Monthly capacity" |
| "1,250 leads" | "Prospects in pipeline" or just hide |
| "Lead allocation" | "Campaign priority" |
| "Leads contacted" | "Active sequences" or "In outreach" |

### 4. Priority Over Percentages
Campaigns compete for monthly focus via "priority sliders" - client thinks in terms of effort allocation, not lead counts.

---

## Terminology Decisions

### Approved Terms

| Concept | Term to Use | Notes |
|---------|-------------|-------|
| Monthly quota | Don't show | Internal detail |
| Booked calls | "Meetings booked" | Primary metric |
| Attendance | "Show rate" | Secondary metric |
| Leads in system | "Prospects" or "Pipeline" | If must show |
| Campaign % | "Priority" | Slider label |
| AI-generated campaign | "AI Suggested" | Badge |
| Activity log | "Recent activity" | Proof of work |

### Banned Terms

| Term | Reason |
|------|--------|
| Credits | Transactional, commoditizes |
| Lead count | Makes us comparable to lead lists |
| Allocation % | Too abstract |
| Lead budget | Implies we're selling leads |

---

## Dashboard Sections (Proposed)

### 1. Hero Metrics (Top)
```
┌─────────────────────────────────────────────────────────────┐
│  12 Meetings Booked        │  85% Show Rate                 │
│  ████████████░░░  On track │  ↑ 5% vs last month            │
└─────────────────────────────────────────────────────────────┘
```

### 2. Campaign Priority Cards
```
┌─────────────────────────────────────────────────────────────┐
│ YOUR CAMPAIGNS                                              │
│                                                             │
│ Tech Decision Makers (AI)     Priority: ●━━━━━━━━○── 40%   │
│ 6 meetings booked │ 3.8% reply rate                        │
│                                                             │
│ Series A Startups (AI)        Priority: ○━━━━━●──── 35%    │
│ 4 meetings booked │ 2.9% reply rate                        │
│                                                             │
│ My Custom Campaign            Priority: ○━━━●───── 25%     │
│ 2 meetings booked │ 1.8% reply rate                        │
│                                                             │
│ ──────────────────────────────────────────────────────────  │
│ Total: 100%              [ Confirm & Activate ]            │
└─────────────────────────────────────────────────────────────┘
```

### 3. Activity Feed (Proof of Work)
```
┌─────────────────────────────────────────────────────────────┐
│ RECENT ACTIVITY                                   Live ●    │
│                                                             │
│ ✉️  Email opened by Sarah Chen (TechCorp)         2m ago    │
│ 💬  Reply from Mike Johnson (StartupXYZ)          15m ago   │
│ 📅  Meeting booked with Lisa Park (Acme)          1h ago    │
│ 📞  Voice call completed with David Lee           2h ago    │
└─────────────────────────────────────────────────────────────┘
```

### 4. Upcoming Meetings
```
┌─────────────────────────────────────────────────────────────┐
│ UPCOMING MEETINGS                                           │
│                                                             │
│ Today 2:00 PM    Sarah Chen, TechCorp         Discovery    │
│ Tomorrow 10 AM   Mike Johnson, StartupXYZ     Demo         │
│ Thu 3:00 PM      Lisa Park, Acme Inc          Follow-up    │
└─────────────────────────────────────────────────────────────┘
```

---

## Campaign Allocation Flow

### User Action
1. Client adjusts priority sliders
2. Sliders auto-balance to 100%
3. Client clicks "Confirm & Activate"

### System Response (Instant)
1. Calculate lead counts from percentages
2. Source prospects from Apollo/pool immediately
3. Enrich instantly (no batching)
4. Assign to campaigns
5. Outreach begins

### UI During Processing
```
┌─────────────────────────────────────────────────────────────┐
│     ◐  Preparing your campaigns...                          │
│        Finding ideal prospects                              │
│        Researching & qualifying                             │
└─────────────────────────────────────────────────────────────┘
```

### UI After Complete
```
┌─────────────────────────────────────────────────────────────┐
│     ✓  Campaigns ready                                      │
│        Outreach will begin during business hours            │
└─────────────────────────────────────────────────────────────┘
```

**What we DON'T show:** "Sourcing 625 leads...", "312 leads assigned"

---

## Files to Modify

| File | Change |
|------|--------|
| `frontend/app/dashboard/page.tsx` | Hero metrics, activity feed |
| `frontend/app/dashboard/campaigns/page.tsx` | Priority sliders |
| `frontend/components/dashboard/` | New components |
| `frontend/lib/api/reports.ts` | Add meetings metrics |
| `docs/architecture/frontend/DASHBOARD.md` | Technical spec |

---

## Open Questions

1. **Mid-month reallocation** - When client adjusts sliders mid-month:
   - Source NEW leads to fill new allocation?
   - Re-allocate existing uncontacted leads?
   - Both?

2. **Show rate display** - Show at campaign level or only dashboard level?

3. **Historical comparison** - Show "vs last month" or just current?

---

## Related Docs

- `campaigns.md` - Detailed campaign allocation UI spec
- `metrics.md` - Metrics display decisions
- `docs/architecture/frontend/DASHBOARD.md` - Technical implementation
