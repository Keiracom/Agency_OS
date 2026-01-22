# Metrics Display Decisions

**Status:** Planning
**Last Updated:** 2026-01-22

---

## Guiding Principle

> Show outcomes the client cares about, not implementation details.

---

## Metrics Hierarchy

### Tier 1: Hero Metrics (Always Visible)

| Metric | Display | Source |
|--------|---------|--------|
| **Meetings Booked** | "12 meetings booked" | `meetings` table, this month |
| **Show Rate** | "85% show rate" | `showed_up` / total meetings |
| **On Track Indicator** | "On track" / "Ahead" / "Behind" | vs tier average |

### Tier 2: Campaign Performance (Per Campaign)

| Metric | Display | Source |
|--------|---------|--------|
| **Meetings from Campaign** | "6 meetings" | Per-campaign meetings count |
| **Reply Rate** | "3.8%" | replies / contacted |
| **Show Rate** | "85%" | showed_up / meetings (optional) |

### Tier 3: Activity (Proof of Work)

| Metric | Display | Source |
|--------|---------|--------|
| **Recent Activity** | Feed of actions | `activities` table |
| **Active Sequences** | "89 in outreach" | Leads with pending sequence steps |

### Tier 4: Hidden (Internal Only)

| Metric | Why Hidden | Used By |
|--------|------------|---------|
| Lead count | Commoditizes | Backend pacing |
| Credits remaining | Transactional | Billing only |
| Enrichment status | Implementation | Debugging |
| Apollo/Clay usage | Implementation | Cost tracking |

---

## What We Show vs Hide

### Dashboard Home

| Show | Hide |
|------|------|
| Meetings booked this month | Total leads in system |
| Show rate % | Leads contacted count |
| Reply rate % | Credits remaining |
| Active campaigns count | Lead allocation numbers |
| Recent activity feed | Enrichment queue |
| Upcoming meetings | Channel allocation % |

### Campaign Detail

| Show | Hide |
|------|------|
| Meetings from this campaign | Lead count assigned |
| Reply rate | Leads contacted |
| Show rate | Sequence step breakdown |
| Priority slider (%) | Raw lead numbers |
| Channel badges | Channel allocation % |

### Reports Page

| Show | Hide |
|------|------|
| Meetings by campaign | Leads by campaign |
| Reply rate trends | Lead burn rate |
| Conversion funnel | Credit usage |
| Channel effectiveness (by reply rate) | Channel allocation % |

---

## Metric Calculations

### Meetings Booked (This Month)
```sql
SELECT COUNT(*)
FROM meetings
WHERE client_id = :client_id
  AND booked_at >= DATE_TRUNC('month', NOW())
```

### Show Rate
```sql
SELECT
  COUNT(*) FILTER (WHERE showed_up = TRUE)::FLOAT /
  NULLIF(COUNT(*), 0) * 100 as show_rate
FROM meetings
WHERE client_id = :client_id
  AND scheduled_at < NOW()  -- Only past meetings
```

### On Track Indicator
```python
tier_avg_meetings = {
    "starter": 7,    # 5-10 range, midpoint
    "growth": 20,    # 15-25 range
    "scale": 40,     # 30-50 range
    "enterprise": 60 # 50+ range
}

days_elapsed = current_day_of_month
days_in_month = total_days_in_month
expected = tier_avg * (days_elapsed / days_in_month)

if meetings_booked >= expected * 1.1:
    status = "ahead"
elif meetings_booked >= expected * 0.9:
    status = "on_track"
else:
    status = "behind"
```

### Reply Rate
```sql
SELECT
  COUNT(*) FILTER (WHERE status = 'replied')::FLOAT /
  NULLIF(COUNT(*) FILTER (WHERE status IN ('sent', 'replied', 'bounced')), 0) * 100
FROM leads
WHERE campaign_id = :campaign_id
```

---

## Formatting Rules

### Numbers
| Value | Format |
|-------|--------|
| 0-999 | As-is: "12" |
| 1,000-999,999 | Comma: "1,234" |
| 1M+ | Abbreviated: "1.2M" |

### Percentages
| Context | Format |
|---------|--------|
| Show rate | "85%" (no decimals) |
| Reply rate | "3.8%" (one decimal) |
| Conversion rate | "1.2%" (one decimal) |

### Time
| Context | Format |
|---------|--------|
| Activity feed | "2m ago", "1h ago", "Yesterday" |
| Meeting time | "Today 2:00 PM", "Tomorrow 10 AM" |
| Historical | "Jan 15", "Dec 2025" |

---

## Comparison Indicators

### vs Last Month
```
12 meetings booked
↑ 3 vs last month
```

### vs Tier Average
```
On track for 18-22 meetings
████████████░░░░░ 65% of month elapsed
```

### Trend Direction
| Trend | Icon | Color |
|-------|------|-------|
| Up > 10% | ↑ | Green |
| Flat ±10% | → | Gray |
| Down > 10% | ↓ | Red |

---

## Empty States

### No Meetings Yet
```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│     📅  No meetings booked yet this month                   │
│                                                             │
│     Your outreach is active. Meetings typically             │
│     start appearing within the first 1-2 weeks.             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### No Activity
```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│     ⏳  Getting started...                                   │
│                                                             │
│     We're preparing your campaigns.                         │
│     Activity will appear here once outreach begins.         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Bad Month Handling

When results are below target, transparency helps:

```
┌─────────────────────────────────────────────────────────────┐
│  5 Meetings Booked                                          │
│  ████░░░░░░░░░░░░ Below target                              │
├─────────────────────────────────────────────────────────────┤
│  This Month's Activity                                      │
│  ────────────────────                                       │
│  2,847 prospects researched                                 │
│  1,204 contacted across 4 channels                          │
│  89 conversations active                                    │
│  45 replies (3.7% reply rate)                               │
│                                                             │
│  💡 Reply rate is healthy. Consider reviewing ICP           │
│     targeting if meetings remain low.                       │
└─────────────────────────────────────────────────────────────┘
```

The activity data shows we're doing the work. The suggestion invites collaboration rather than blame.

---

## API Response Shape

### GET /api/v1/clients/{id}/dashboard-metrics

```json
{
  "period": "2026-01",

  "outcomes": {
    "meetings_booked": 12,
    "show_rate": 85,
    "meetings_showed": 10,
    "deals_created": 8,
    "status": "on_track"
  },

  "comparison": {
    "meetings_vs_last_month": 3,
    "meetings_vs_last_month_pct": 33,
    "tier_target_low": 15,
    "tier_target_high": 25
  },

  "activity": {
    "prospects_in_pipeline": 2847,
    "active_sequences": 89,
    "replies_this_month": 45,
    "reply_rate": 3.7
  },

  "campaigns": [
    {
      "id": "uuid",
      "name": "Tech Decision Makers",
      "priority_pct": 40,
      "meetings_booked": 6,
      "reply_rate": 3.8,
      "show_rate": 85
    }
  ]
}
```

**Note:** No `leads_count`, `credits_remaining`, or `leads_contacted` in response.

---

## Migration Path

### Phase 1: Add New Metrics
- Add meetings_booked to dashboard
- Add show_rate display
- Keep existing metrics temporarily

### Phase 2: Reposition Existing
- Move "Total Leads" to secondary position
- Rename "Conversions" to "Meetings Booked"
- Add activity feed

### Phase 3: Remove Commodity Metrics
- Remove credits badge from header
- Remove lead counts from campaign cards
- Replace with priority sliders

---

## Related Files

| File | Changes Needed |
|------|----------------|
| `frontend/lib/api/reports.ts` | Add `getDashboardMetrics()` |
| `frontend/app/dashboard/page.tsx` | New hero metrics |
| `frontend/components/dashboard/` | New metric cards |
| `src/api/routes/reports.py` | New endpoint |
| `src/services/meeting_service.py` | Add `get_dashboard_metrics()` |
