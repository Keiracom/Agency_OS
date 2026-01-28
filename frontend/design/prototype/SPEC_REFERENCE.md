# Prototype Spec Reference

**Purpose:** Single source of truth for prototype development. Read this instead of searching docs/architecture.
**Source:** Compiled from docs/architecture audits on 2026-01-23.

---

## 1. Terminology Rules

### Banned Terms (NEVER use)
- "Credits remaining"
- "Lead count" / "Lead allocation %"
- "Hot Leads" (as a section title)
- "Lead budget"
- "Leads contacted"

### Approved Terms
- "Meetings booked"
- "Prospects in pipeline"
- "Priority" (for sliders)
- "Show rate"
- "Active sequences"

---

## 2. ALS Tier Display

### Internal vs Client Labels

| Tier | Score | Internal Label | Client Label | Color |
|------|-------|----------------|--------------|-------|
| Hot | 85-100 | "Hot" | "High Priority" | orange-500 |
| Warm | 60-84 | "Warm" | "Engaged" | yellow-500 |
| Cool | 35-59 | "Cool" | "Nurturing" | blue-500 |
| Cold | 20-34 | "Cold" | "Low Activity" | slate-400 |
| Dead | <20 | "Dead" | "Inactive" | slate-300 |

### Visibility Rules
- **Clients see:** Tier labels (High Priority, Engaged, etc.)
- **Clients DON'T see:** Raw ALS scores (0-100), enrichment costs, source waterfall

---

## 3. Metric Visibility Tiers

| Tier | Visibility | Metrics |
|------|------------|---------|
| **T1 Hero** | Always visible | Meetings booked, Show rate, Deals created, On-track status |
| **T2 Campaign** | Per campaign | Meetings, Reply rate, Show rate, Open rate |
| **T3 Activity** | Proof of work | Activity feed, Active sequences, Replies count |
| **T4 Hidden** | INTERNAL ONLY | Lead counts, Credits, Enrichment status, Costs |

---

## 4. Permission Modes

| Mode | Behavior | Icon |
|------|----------|------|
| `autopilot` | System sends automatically | Sparkles |
| `co_pilot` | Human reviews/approves before send | Eye |
| `manual` | Human triggers each send manually | MousePointer |

**Key rule:** JIT validation blocks outreach if `permission_mode = MANUAL`

---

## 5. Dashboard Components

### Hero Stats (T1)
- Meetings Booked (number + vs last month %)
- Show Rate (percentage)
- Deals Created (number)
- Campaign Status ("On Track" / "Ahead" / "Behind")

### Required Sections
- Priority Sliders (campaign allocation)
- Live Activity Feed
- Upcoming Meetings
- Quick Actions
- Emergency Pause Button

### NOT on Dashboard
- AI Campaign Suggestions (belongs on Campaigns page)
- Raw lead counts
- Cost metrics

---

## 6. Campaign Specs

### Priority Sliders
- Range: 10% min, 80% max per campaign
- Must sum to 100%
- Auto-balance when one changes

### AI Campaign Suggestions
- **Location:** Campaigns page (NOT Dashboard)
- **Source:** CampaignSuggesterEngine
- **When:** Generated during onboarding, regeneratable
- **Output:** name, description, targets, allocation %, reasoning, priority

### Campaign Card Shows
- Name, status, permission mode badge
- Channels (icons)
- Meetings, Reply rate, Show rate
- **NOT:** Lead count

### Campaign Slots by Tier
| Tier | AI-Suggested | Custom | Total |
|------|--------------|--------|-------|
| Ignition | 3 | 2 | 5 |
| Velocity | 6 | 4 | 10 |
| Dominance | 12 | 8 | 20 |

---

## 7. Leads Specs

### Lead Table Columns (Client View)
- Name, Company, Title
- Tier Badge (client-friendly label)
- Status (New, Enriched, In Sequence, Meeting Booked, Replied)
- Last Activity
- **NOT:** Raw ALS score, enrichment source, SDK cost

### Lead Statuses
| Status | Client Label |
|--------|--------------|
| new | New |
| enriched | Enriched |
| scored | Scored |
| in_sequence | In Sequence |
| converted | Meeting Booked |
| replied | Replied |
| unsubscribed | Unsubscribed |
| bounced | Bounced |

### Tier Filter Cards
Show count per tier with client-friendly labels.

---

## 8. Replies Specs

### Intent Classifications (8 types)
| Intent | Description |
|--------|-------------|
| meeting_interest | Wants to meet |
| question | Has questions |
| positive_engagement | Interested but not ready |
| not_interested | Polite decline |
| out_of_office | Auto-reply OOO |
| wrong_person | Not the right contact |
| referral | Suggests someone else |
| angry_or_complaint | Negative response |

### Reply Card Shows
- Lead name, company
- Channel icon
- Intent badge
- Message preview
- AI suggested response
- Actions: Archive, Respond, Forward

---

## 9. Reports Specs

### Available Metrics (Client-Visible)
- Meetings booked (trend chart)
- Show rate
- Reply rate
- Open rate
- Campaign performance comparison
- Funnel visualization

### NOT Available to Clients
- Cost per lead
- Cost per meeting
- Credit usage
- Enrichment costs

---

## 10. Settings Specs

### Implemented
- **ICP Settings:** Industries, titles, company sizes, locations, pain points
- **LinkedIn Settings:** Connection status, daily limits, account health

### NOT Implemented (Show "Coming Soon")
- **Profile Settings:** Company info
- **Notification Settings:** Alert preferences

### Emergency Pause
- Required on Dashboard
- Pauses ALL outreach immediately
- Red styling, confirmation required

---

## 11. API Endpoints Reference

### Dashboard
- `GET /clients/{id}/dashboard-metrics` - Hero metrics
- `GET /clients/{id}/activities` - Activity feed
- `GET /clients/{id}/meetings?upcoming=true` - Meetings

### Campaigns
- `GET /clients/{id}/campaigns` - List
- `POST /clients/{id}/campaigns` - Create
- `GET /clients/{id}/campaigns/suggestions` - AI suggestions
- `POST /clients/{id}/campaigns/allocate` - Update priorities

### Leads
- `GET /clients/{id}/leads` - List with filters
- `GET /clients/{id}/leads/{id}` - Detail

### Replies
- `GET /clients/{id}/replies` - List
- `PATCH /replies/{id}/handled` - Mark handled

---

## 12. Color Tokens

| Token | Value | Usage |
|-------|-------|-------|
| Sidebar BG | #1E3A5F | Navy sidebar |
| Accent Blue | #3B82F6 | Primary actions |
| Hot/High Priority | orange-500 | ALS 85-100 |
| Warm/Engaged | yellow-500 | ALS 60-84 |
| Cool/Nurturing | blue-500 | ALS 35-59 |
| Cold/Low Activity | slate-400 | ALS 20-34 |
| Dead/Inactive | slate-300 | ALS <20 |
| Success | emerald-500 | Positive states |
| Warning | amber-500 | Needs attention |
| Error | red-500 | Critical/pause |

---

## 13. Quick Checklist

Before showing any metric, ask:
- [ ] Is this T1-T3 visible? (T4 = hidden)
- [ ] Using client-friendly tier labels?
- [ ] No banned terminology?
- [ ] No raw ALS scores?
- [ ] No cost/credit data?

Before adding a component:
- [ ] Is it in the spec?
- [ ] Does the API endpoint exist?
- [ ] Is it implemented or "Coming Soon"?

---

**Last Updated:** 2026-01-23
**Maintainer:** Update when architecture docs change
