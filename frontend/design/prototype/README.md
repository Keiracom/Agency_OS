# Agency OS Dashboard Prototype

**Purpose:** Complete UI prototype for collaboration and design iteration.
**Location:** `frontend/design/prototype/`

---

## Quick Start

To view the prototype, import any page component and render it:

```tsx
import { DashboardHome } from "@/design/prototype/components/dashboard";
import { CampaignList } from "@/design/prototype/components/campaigns";
import { LeadList } from "@/design/prototype/components/leads";
```

---

## Structure

```
prototype/
├── DESIGN_SYSTEM.md          # Colors, typography, patterns
├── README.md                 # This file
├── components/
│   ├── layout/               # Shell, Sidebar, Header
│   ├── dashboard/            # KPIs, Activity, Meetings, ALS
│   ├── campaigns/            # Priority sliders, list, detail
│   ├── leads/                # ALS cards, timeline, list, detail
│   ├── replies/              # Reply inbox
│   ├── reports/              # Charts, analytics
│   └── settings/             # ICP, LinkedIn, Profile, Notifications
└── index.ts                  # Master export
```

---

## Pages

| Page | Component | Features |
|------|-----------|----------|
| **Dashboard Home** | `DashboardHome` | KPIs, campaigns, activity, meetings |
| **Campaigns List** | `CampaignList` | Priority sliders, allocation |
| **Campaign Detail** | `CampaignDetail` | Metrics, sequences, leads |
| **New Campaign** | `CampaignNew` | Creation form |
| **Leads List** | `LeadList` | Tier filters, table |
| **Lead Detail** | `LeadDetail` | ALS breakdown, timeline |
| **Replies** | `ReplyInbox` | Split view inbox |
| **Reports** | `ReportsPage` | Charts, metrics |
| **Settings Hub** | `SettingsHub` | Navigation cards |
| **ICP Settings** | `ICPSettings` | ICP form |
| **LinkedIn Settings** | `LinkedInSettings` | Connection status |
| **Profile Settings** | `ProfileSettings` | Company profile |
| **Notifications** | `NotificationSettings` | Alert preferences |

---

## Design Tokens

See `DESIGN_SYSTEM.md` for full token reference.

### Key Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--sidebar-bg` | `#1E3A5F` | Sidebar background |
| `--accent-blue` | `#3B82F6` | Primary actions |
| `--tier-hot` | `#EF4444` | Hot leads (85-100) |
| `--tier-warm` | `#F97316` | Warm leads (60-84) |
| `--tier-cool` | `#3B82F6` | Cool leads (35-59) |

---

## Collaboration Workflow

### Making Changes

1. Open any component in your editor
2. Modify styles, layout, or content
3. View changes in browser (if rendering)
4. Discuss and iterate

### What's Static (Demo Data)

All components use inline static data. To change demo values, edit the `demoData` objects in each component file.

### What's Real (Structure)

- Component interfaces match the real API types
- Layout structure matches the production app
- Colors and tokens are production-ready

---

## Wiring to Real Data

When ready to use these components in the real app:

1. Move component to `frontend/components/`
2. Replace `demoData` with React Query hooks
3. Import from `@/hooks/use-*`
4. Add loading/error states

Example:
```tsx
// Before (prototype)
const demoData = { meetings: 12, showRate: 85 };

// After (production)
const { data, isLoading, error } = useDashboardStats();
if (isLoading) return <Skeleton />;
```

---

## Architecture Alignment

These components implement the specs from:

- `docs/architecture/frontend/DASHBOARD.md`
- `docs/architecture/frontend/CAMPAIGNS.md`
- `docs/architecture/frontend/LEADS.md`
- `docs/architecture/frontend/SETTINGS.md`

---

## Building Agents

This prototype was built by parallel agents:

1. **Layout Agent** - Shell, Sidebar, Header
2. **Dashboard Agent** - KPIs, Activity, Meetings
3. **Campaigns Agent** - Priority sliders, list, detail
4. **Leads Agent** - ALS components, list, detail
5. **Settings Agent** - All settings pages
6. **Replies Agent** - Reply inbox
7. **Reports Agent** - Charts, analytics
