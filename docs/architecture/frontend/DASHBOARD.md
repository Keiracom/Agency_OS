# Frontend Dashboard Architecture

**Purpose:** Architecture spec for the Agency OS client dashboard.
**Last Updated:** 2026-01-22
**Status:** Specification Complete

---

## 1. Overview

### Purpose

The client dashboard is the primary interface for Agency OS customers. It communicates **outcomes** (meetings booked, show rates) rather than **inputs** (lead counts, credits).

### Design Philosophy

| Principle | Description |
|-----------|-------------|
| **Outcome-Focused** | Show meetings booked, NOT lead counts |
| **Transparency as Proof of Work** | Activity data explains result fluctuations |
| **No Commodity Language** | Avoid "credits", "lead allocation %" |
| **Priority Sliders** | Clients think in effort allocation, not numbers |

### Terminology Rules

| Approved Term | Banned Term | Reason |
|---------------|-------------|--------|
| "Meetings booked" | "Credits remaining" | Transactional, commoditizes service |
| "Prospects in pipeline" | "Lead count" | Makes us comparable to lead vendors |
| "Priority" | "Lead allocation %" | Too abstract for clients |
| "Show rate" | "Lead budget" | Implies selling leads |
| "Active sequences" | "Leads contacted" | Focuses on process, not commodity |

---

## 2. Routes

### Dashboard Route Structure

```
/dashboard                     → Overview (Hero metrics, activity, meetings)
/dashboard/campaigns           → Campaign list with priority sliders
/dashboard/campaigns/[id]      → Campaign detail + sequences
/dashboard/campaigns/new       → New campaign creation
/dashboard/leads               → Lead list (ALS filtered)
/dashboard/leads/[id]          → Lead detail + Co-Pilot view
/dashboard/replies             → Reply inbox
/dashboard/reports             → Analytics and trends
/dashboard/settings            → General settings
/dashboard/settings/icp        → ICP configuration
/dashboard/settings/linkedin   → LinkedIn seat management
```

### Route Files

| Route | File | Purpose |
|-------|------|---------|
| `/dashboard` | `frontend/app/dashboard/page.tsx` | Main overview |
| `/dashboard/campaigns` | `frontend/app/dashboard/campaigns/page.tsx` | Campaign list |
| `/dashboard/campaigns/[id]` | `frontend/app/dashboard/campaigns/[id]/page.tsx` | Campaign detail |
| `/dashboard/campaigns/new` | `frontend/app/dashboard/campaigns/new/page.tsx` | New campaign |
| `/dashboard/leads` | `frontend/app/dashboard/leads/page.tsx` | Lead list |
| `/dashboard/leads/[id]` | `frontend/app/dashboard/leads/[id]/page.tsx` | Lead detail |
| `/dashboard/replies` | `frontend/app/dashboard/replies/page.tsx` | Reply inbox |
| `/dashboard/reports` | `frontend/app/dashboard/reports/page.tsx` | Analytics |
| `/dashboard/settings` | `frontend/app/dashboard/settings/page.tsx` | Settings |
| `/dashboard/settings/icp` | `frontend/app/dashboard/settings/icp/page.tsx` | ICP config |
| `/dashboard/settings/linkedin` | `frontend/app/dashboard/settings/linkedin/page.tsx` | LinkedIn |
| Layout | `frontend/app/dashboard/layout.tsx` | Auth + sidebar wrapper |

---

## 3. Data Available

### Metric Tiers

| Tier | Visibility | Metrics |
|------|------------|---------|
| **T1 Hero** | Always visible | Meetings booked, Show rate, On track indicator |
| **T2 Campaign** | Per campaign | Meetings, Reply rate, Show rate |
| **T3 Activity** | Proof of work | Recent activity feed, Active sequences |
| **T4 Hidden** | Internal only | Lead counts, Credits, Enrichment status |

### TypeScript Interfaces

```typescript
// frontend/lib/api/types.ts

// Current dashboard stats (what exists)
interface DashboardStats {
  total_leads: number;           // T4 Hidden - internal
  leads_contacted: number;       // T4 Hidden - internal
  leads_replied: number;         // T3 Activity (as reply count)
  leads_converted: number;       // T1 Hero (as meetings)
  active_campaigns: number;      // T2 Campaign
  credits_remaining: number;     // T4 Hidden - NEVER show
  reply_rate: number;            // T2 Campaign
  conversion_rate: number;       // T1 Hero (as show rate)
}

// Proposed hero metrics (what we need)
interface HeroMetrics {
  period: string;                // "2026-01"
  outcomes: {
    meetings_booked: number;     // T1 Hero
    show_rate: number;           // T1 Hero (percentage)
    meetings_showed: number;     // Internal
    deals_created: number;       // T1 Hero
    status: "ahead" | "on_track" | "behind";
  };
  comparison: {
    meetings_vs_last_month: number;
    meetings_vs_last_month_pct: number;
    tier_target_low: number;
    tier_target_high: number;
  };
  activity: {
    prospects_in_pipeline: number;  // T3 Activity
    active_sequences: number;       // T3 Activity
    replies_this_month: number;     // T3 Activity
    reply_rate: number;             // T2 Campaign
  };
}

// Activity feed item
interface Activity {
  id: string;
  client_id: string;
  campaign_id: string;
  lead_id: string;
  channel: "email" | "sms" | "linkedin" | "voice" | "mail";
  action: string;
  provider_message_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  lead?: Lead;
  campaign?: Campaign;
}

// Meeting
interface Meeting {
  id: string;
  lead_id: string;
  lead_name: string;
  lead_company: string | null;
  scheduled_at: string | null;
  duration_minutes: number;
  meeting_type: "discovery" | "demo" | "follow_up";
  calendar_link: string | null;
  status: "scheduled" | "completed" | "cancelled" | "no_show";
  created_at: string;
}

// ALS distribution
interface ALSDistribution {
  tier: "hot" | "warm" | "cool" | "cold" | "dead";
  count: number;
  percentage: number;
}

// Campaign performance
interface CampaignPerformance {
  campaign_id: string;
  campaign_name: string;
  status: "draft" | "active" | "paused" | "completed";
  total_leads: number;           // T4 Hidden
  contacted: number;             // T4 Hidden
  replied: number;               // T3 Activity
  converted: number;             // T1 Hero (meetings)
  reply_rate: number;            // T2 Campaign
  conversion_rate: number;       // T2 Campaign
}
```

### Data Sources

| Data | Source Table | API Endpoint |
|------|--------------|--------------|
| Meetings booked | `meetings` | `GET /api/v1/clients/{id}/meetings` |
| Show rate | `meetings.showed_up` | `GET /api/v1/clients/{id}/dashboard-metrics` |
| Activity feed | `activities` | `GET /api/v1/clients/{id}/activities` |
| Campaign metrics | `campaigns` + `leads` | `GET /api/v1/reports/clients/{id}` |
| ALS distribution | `leads.als_tier` | `GET /api/v1/reports/leads/distribution` |
| Replies | `lead_replies` | `GET /api/v1/clients/{id}/replies` |

---

## 4. User Actions

### Dashboard Home Actions

| Action | Component | API Call | Status |
|--------|-----------|----------|--------|
| View hero metrics | HeroMetricsCard | `GET /dashboard-metrics` | NOT IMPLEMENTED |
| View activity feed | ActivityFeed | `GET /activities` | NOT IMPLEMENTED |
| View upcoming meetings | MeetingsWidget | `GET /meetings?upcoming=true` | IMPLEMENTED |
| Navigate to campaign | CampaignCard | - | IMPLEMENTED |
| Navigate to replies | - | - | IMPLEMENTED |
| Emergency pause all outreach | PauseButton | `POST /clients/{id}/pause` | NOT IMPLEMENTED |

### Campaign Page Actions

| Action | Component | API Call | Status |
|--------|-----------|----------|--------|
| Adjust priority slider | PrioritySlider | `PATCH /campaigns/{id}` | NOT IMPLEMENTED |
| Confirm & activate | ConfirmButton | `POST /campaigns/activate` | NOT IMPLEMENTED |
| View campaign detail | - | `GET /campaigns/{id}` | IMPLEMENTED |
| Create new campaign | - | `POST /campaigns` | IMPLEMENTED |

### Settings Actions

| Action | Component | API Call | Status |
|--------|-----------|----------|--------|
| Update ICP | ICPForm | `PUT /clients/{id}/icp` | IMPLEMENTED |
| Connect LinkedIn | LinkedInConnect | `POST /linkedin/connect` | IMPLEMENTED |
| Manage webhooks | WebhookManager | `GET/POST /webhooks` | IMPLEMENTED |

---

## 5. Components (Existing)

### Dashboard Components

| Component | File | Props | Purpose |
|-----------|------|-------|---------|
| MeetingsWidget | `components/dashboard/meetings-widget.tsx` | None (uses hook) | Upcoming meetings list |
| ActivityTicker | `components/dashboard/ActivityTicker.tsx` | `activities?: Activity[]`, `speed?`, `direction?`, `showTimestamp?`, `maxVisible?` | Bloomberg-style scrolling activity |
| CapacityGauge | `components/dashboard/CapacityGauge.tsx` | `current`, `limit`, `label?`, `showPercentage?`, `variant?`, `warningThreshold?`, `criticalThreshold?` | Monthly usage gauge |
| CoPilotView | `components/dashboard/CoPilotView.tsx` | `lead`, `onSendEmail?`, `onRegenerateEmail?` | AI email co-pilot interface |

### Lead Components

| Component | File | Props | Purpose |
|-----------|------|-------|---------|
| ALSScorecard | `components/leads/ALSScorecard.tsx` | `score`, `breakdown?`, `showBadge?`, `size?` | ALS score with radar chart tooltip |

### Admin Components (Reusable)

| Component | File | Props | Purpose |
|-----------|------|-------|---------|
| KPICard | `components/admin/KPICard.tsx` | `title`, `value`, `change?`, `changeLabel?`, `icon?`, `loading?` | Metric display card |

### UI Components

| Component | File | Purpose |
|-----------|------|---------|
| Card, CardHeader, CardContent, CardTitle | `components/ui/card.tsx` | Base card layout |
| Badge | `components/ui/badge.tsx` | Status badges |
| Button | `components/ui/button.tsx` | Actions |
| Skeleton | `components/ui/loading-skeleton.tsx` | Loading states |
| ErrorState | `components/ui/error-state.tsx` | Error display |
| EmptyState | `components/ui/empty-state.tsx` | Empty state display |

---

## 6. Components to Create

### HeroMetricsCard

```typescript
// frontend/components/dashboard/HeroMetricsCard.tsx

interface HeroMetricsCardProps {
  metrics: HeroMetrics | null;
  isLoading: boolean;
  error?: Error;
}

/**
 * Displays T1 Hero metrics:
 * - Meetings booked this month (large number)
 * - Show rate percentage
 * - On track/Ahead/Behind indicator
 * - vs last month comparison
 */
```

**Design:**
```
+------------------------------------------+
|  12 Meetings Booked        85% Show Rate |
|  On track for 15-25            +3 vs last month |
+------------------------------------------+
```

### PrioritySlider

```typescript
// frontend/components/dashboard/PrioritySlider.tsx

interface PrioritySliderProps {
  campaignId: string;
  campaignName: string;
  priority: number;           // 0-100
  onPriorityChange: (value: number) => void;
  meetings: number;
  replyRate: number;
  isAISuggested?: boolean;
}

/**
 * Campaign priority slider that:
 * - Shows campaign name with AI badge if suggested
 * - Displays current priority as draggable slider
 * - Shows meetings and reply rate below
 * - Auto-balances with other sliders to 100%
 */
```

**Design:**
```
+------------------------------------------+
| Tech Decision Makers (AI)     ●━━━━━━○── 40% |
| 6 meetings booked | 3.8% reply rate         |
+------------------------------------------+
```

### CampaignPriorityPanel

```typescript
// frontend/components/dashboard/CampaignPriorityPanel.tsx

interface CampaignPriorityPanelProps {
  campaigns: CampaignWithPriority[];
  onPrioritiesChange: (priorities: Record<string, number>) => void;
  onActivate: () => void;
  isActivating: boolean;
}

/**
 * Container for all campaign priority sliders:
 * - Lists all campaigns with sliders
 * - Shows total (must equal 100%)
 * - "Confirm & Activate" button
 */
```

### LiveActivityFeed

```typescript
// frontend/components/dashboard/LiveActivityFeed.tsx

interface LiveActivityFeedProps {
  activities: Activity[];
  isLoading: boolean;
  onLoadMore?: () => void;
  maxHeight?: string;
}

/**
 * Real-time activity feed (proof of work):
 * - Shows recent outreach actions
 * - Channel icons (email, sms, linkedin, voice)
 * - Lead name and company
 * - Timestamp (relative: "2m ago")
 * - Expandable for full history
 */
```

### EmergencyPauseButton

```typescript
// frontend/components/dashboard/EmergencyPauseButton.tsx

interface EmergencyPauseButtonProps {
  isPaused: boolean;
  onToggle: () => void;
  isLoading: boolean;
}

/**
 * Big red button to pause all outreach:
 * - Prominent placement in header or dashboard
 * - Confirmation dialog before pausing
 * - Shows paused state clearly
 * - Logs pause event for audit
 */
```

### OnTrackIndicator

```typescript
// frontend/components/dashboard/OnTrackIndicator.tsx

interface OnTrackIndicatorProps {
  status: "ahead" | "on_track" | "behind";
  targetLow: number;
  targetHigh: number;
  current: number;
}

/**
 * Visual indicator for meeting pace:
 * - Green "Ahead" if > 110% expected
 * - Blue "On Track" if 90-110% expected
 * - Orange "Behind" if < 90% expected
 * - Progress bar showing month progress
 */
```

---

## 7. API Integration

### Current Hooks

| Hook | File | Query Key | Endpoint | Status |
|------|------|-----------|----------|--------|
| `useDashboardStats` | `hooks/use-reports.ts` | `["dashboard-stats", clientId]` | `GET /api/v1/reports/clients/{clientId}` | IMPLEMENTED |
| `useActivityFeed` | `hooks/use-reports.ts` | `["activity-feed", clientId, limit]` | `GET /api/v1/clients/{clientId}/activities` | STUB (returns []) |
| `useALSDistribution` | `hooks/use-reports.ts` | `["als-distribution", clientId]` | `GET /api/v1/reports/leads/distribution` | IMPLEMENTED |
| `useCampaignPerformance` | `hooks/use-reports.ts` | `["campaign-performance", clientId, params]` | N/A | STUB (returns []) |
| `useChannelMetrics` | `hooks/use-reports.ts` | `["channel-metrics", clientId, params]` | N/A | STUB (returns []) |
| `useDailyActivity` | `hooks/use-reports.ts` | `["daily-activity", clientId, params]` | `GET /api/v1/reports/activity/daily` | IMPLEMENTED |
| `useUpcomingMeetings` | `hooks/use-meetings.ts` | `["meetings", clientId, params]` | `GET /api/v1/clients/{clientId}/meetings` | IMPLEMENTED |

### Hooks to Create

| Hook | Query Key | Endpoint | Purpose |
|------|-----------|----------|---------|
| `useHeroMetrics` | `["hero-metrics", clientId]` | `GET /api/v1/clients/{id}/dashboard-metrics` | T1 Hero metrics |
| `useLiveActivity` | `["live-activity", clientId]` | WebSocket or polling | Real-time activity |
| `usePauseOutreach` | N/A (mutation) | `POST /api/v1/clients/{id}/pause` | Emergency pause |
| `useCampaignPriorities` | `["campaign-priorities", clientId]` | `GET /api/v1/clients/{id}/campaigns` | Campaign priorities |
| `useUpdatePriorities` | N/A (mutation) | `PATCH /api/v1/campaigns/priorities` | Update all priorities |

### React Query Configuration

```typescript
// Stale times by data type
const STALE_TIMES = {
  heroMetrics: 30 * 1000,      // 30 seconds
  activity: 10 * 1000,         // 10 seconds (frequent updates)
  campaigns: 60 * 1000,        // 1 minute
  meetings: 60 * 1000,         // 1 minute
  alsDistribution: 5 * 60 * 1000,  // 5 minutes (slow changing)
};

// Refetch intervals
const REFETCH_INTERVALS = {
  heroMetrics: 60 * 1000,      // Every minute
  activity: 30 * 1000,         // Every 30 seconds
  meetings: 5 * 60 * 1000,     // Every 5 minutes
};
```

---

## 8. API Gaps

### Missing Endpoints

| Endpoint | Purpose | Priority | Backend File |
|----------|---------|----------|--------------|
| `GET /api/v1/clients/{id}/dashboard-metrics` | Hero metrics (meetings, show rate, status) | P1 | `src/api/routes/reports.py` |
| `GET /api/v1/clients/{id}/activities` | Activity feed | P1 | `src/api/routes/activities.py` (new) |
| `POST /api/v1/clients/{id}/pause` | Emergency pause outreach | P1 | `src/api/routes/clients.py` |
| `PATCH /api/v1/campaigns/priorities` | Batch update priorities | P2 | `src/api/routes/campaigns.py` |
| `POST /api/v1/campaigns/activate` | Activate with new priorities | P2 | `src/api/routes/campaigns.py` |

### API Response Shapes Needed

```typescript
// GET /api/v1/clients/{id}/dashboard-metrics
interface DashboardMetricsResponse {
  period: string;
  outcomes: {
    meetings_booked: number;
    show_rate: number;
    meetings_showed: number;
    deals_created: number;
    status: "ahead" | "on_track" | "behind";
  };
  comparison: {
    meetings_vs_last_month: number;
    meetings_vs_last_month_pct: number;
    tier_target_low: number;
    tier_target_high: number;
  };
  activity: {
    prospects_in_pipeline: number;
    active_sequences: number;
    replies_this_month: number;
    reply_rate: number;
  };
  campaigns: Array<{
    id: string;
    name: string;
    priority_pct: number;
    meetings_booked: number;
    reply_rate: number;
    show_rate: number;
  }>;
}

// GET /api/v1/clients/{id}/activities
interface ActivitiesResponse {
  items: Activity[];
  total: number;
  has_more: boolean;
}

// POST /api/v1/clients/{id}/pause
interface PauseResponse {
  paused: boolean;
  paused_at: string;
  paused_by: string;
}
```

---

## 9. State Management

### React Query Strategy

```typescript
// Query keys namespace
const queryKeys = {
  dashboard: {
    all: (clientId: string) => ["dashboard", clientId],
    stats: (clientId: string) => ["dashboard", clientId, "stats"],
    heroMetrics: (clientId: string) => ["dashboard", clientId, "hero"],
    activity: (clientId: string, limit?: number) => ["dashboard", clientId, "activity", limit],
    meetings: (clientId: string, params?: object) => ["dashboard", clientId, "meetings", params],
  },
  campaigns: {
    all: (clientId: string) => ["campaigns", clientId],
    list: (clientId: string) => ["campaigns", clientId, "list"],
    detail: (campaignId: string) => ["campaigns", "detail", campaignId],
    priorities: (clientId: string) => ["campaigns", clientId, "priorities"],
  },
  reports: {
    als: (clientId: string) => ["reports", clientId, "als"],
    daily: (clientId: string, params?: object) => ["reports", clientId, "daily", params],
  },
};
```

### Optimistic Updates

```typescript
// Priority slider optimistic update
const updatePriorities = useMutation({
  mutationFn: (priorities: Record<string, number>) =>
    api.patch('/campaigns/priorities', priorities),
  onMutate: async (newPriorities) => {
    await queryClient.cancelQueries(queryKeys.campaigns.priorities(clientId));
    const previous = queryClient.getQueryData(queryKeys.campaigns.priorities(clientId));
    queryClient.setQueryData(queryKeys.campaigns.priorities(clientId), newPriorities);
    return { previous };
  },
  onError: (err, newPriorities, context) => {
    queryClient.setQueryData(queryKeys.campaigns.priorities(clientId), context?.previous);
  },
  onSettled: () => {
    queryClient.invalidateQueries(queryKeys.campaigns.priorities(clientId));
  },
});
```

### Client Context

```typescript
// frontend/hooks/use-client.ts
// Already implemented - provides clientId for all queries

const { clientId, client } = useClient();
// clientId: string - from user's active membership
// client: { name, tier, creditsRemaining } - basic client data
```

---

## 10. v0 Integration

### Ready for Visual Design

| Section | Component | Ready? | Notes |
|---------|-----------|--------|-------|
| Layout | DashboardLayout | YES | Sidebar + header structure exists |
| Meetings | MeetingsWidget | YES | Fully functional |
| Activity | ActivityTicker | PARTIAL | Component exists, needs real data |
| ALS Badge | ALSScorecard | YES | With radar chart tooltip |
| KPI Card | KPICard | YES | Reusable metric card |
| Hero Metrics | - | NO | Needs HeroMetricsCard component |
| Priority Sliders | - | NO | Needs PrioritySlider component |
| Pause Button | - | NO | Needs EmergencyPauseButton component |

### CSS Variables (Tailwind Config)

```typescript
// tailwind.config.ts theme colors already defined:
// - primary, secondary, muted, accent
// - destructive (for pause button)
// - card, popover, border

// Dark theme colors (for ActivityTicker, CoPilotView):
// - bg-[#0f0f13] - deep background
// - bg-[#1a1a1f] - card background
// - border-white/10 - subtle borders
// - text-gray-400, text-gray-500 - muted text
```

### Component States for Design

```typescript
// All dashboard components should handle:
// - Loading (skeleton state)
// - Error (error message + retry)
// - Empty (helpful empty state message)
// - Demo mode (yellow indicator when no real data)
```

---

## 11. Wireframe

### Dashboard Home Layout

```
+------------------------------------------------------------------+
| AGENCY OS                                    [Client] [Settings] |
+------------------------------------------------------------------+
|        |                                                          |
| SIDEBAR|  DASHBOARD                                               |
|        |                                                          |
| [Home] |  +------------------------+  +------------------------+ |
| [Camp] |  | 12 Meetings Booked     |  | 85% Show Rate          | |
| [Leads]|  | On track              |  | +5% vs last month       | |
| [Reply]|  +------------------------+  +------------------------+ |
| [Reprt]|                                                          |
| [Setng]|  +--------------------------------------------------+   |
|        |  | YOUR CAMPAIGNS                                    |   |
|        |  |                                                   |   |
|        |  | Tech Decision Makers (AI)   ●━━━━━━━━○──  40%    |   |
|        |  | 6 meetings | 3.8% reply                           |   |
|        |  |                                                   |   |
|        |  | Series A Startups (AI)      ○━━━━━●────  35%     |   |
|        |  | 4 meetings | 2.9% reply                           |   |
|        |  |                                                   |   |
|        |  | My Custom Campaign          ○━━━●──────  25%     |   |
|        |  | 2 meetings | 1.8% reply                           |   |
|        |  |                                                   |   |
|        |  | Total: 100%          [ Confirm & Activate ]       |   |
|        |  +--------------------------------------------------+   |
|        |                                                          |
|        |  +----------------------------+  +---------------------+ |
|        |  | RECENT ACTIVITY       Live |  | UPCOMING MEETINGS   | |
|        |  |                            |  |                     | |
|        |  | [Email] Sarah Chen opened  |  | Today 2:00 PM       | |
|        |  |         TechCorp      2m   |  | Sarah Chen          | |
|        |  |                            |  | TechCorp (Discovery)| |
|        |  | [Reply] Mike Johnson reply |  |                     | |
|        |  |         StartupXYZ   15m   |  | Tomorrow 10 AM      | |
|        |  |                            |  | Mike Johnson        | |
|        |  | [Meeting] Lisa Park booked |  | StartupXYZ (Demo)   | |
|        |  |           Acme       1h    |  |                     | |
|        |  +----------------------------+  +---------------------+ |
|        |                                                          |
+------------------------------------------------------------------+
```

### Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| `lg` (1024px+) | Sidebar visible, 3-column grid |
| `md` (768px) | Sidebar collapsible, 2-column grid |
| `sm` (< 768px) | Sidebar hidden (hamburger), single column |

### Component Grid

```
Desktop (lg):
+---------+---------------------------+
| Sidebar | Main Content              |
| 256px   | flex-1                    |
+---------+---------------------------+

Main Content Grid:
+------------------+------------------+
| Hero Metric 1    | Hero Metric 2    |  lg:grid-cols-2
+------------------+------------------+
| Campaign Priority Panel            |  lg:col-span-2
+------------------------------------+
| Activity Feed     | Meetings       |  lg:grid-cols-3
| (2 cols)          | (1 col)        |
+------------------------------------+
```

---

## Related Documentation

| Doc | Purpose |
|-----|---------|
| `frontend/design/dashboard/OVERVIEW.md` | Design philosophy and terminology |
| `frontend/design/dashboard/metrics.md` | Metric tiers and display rules |
| `frontend/design/dashboard/campaigns.md` | Campaign allocation UI spec |
| `docs/architecture/frontend/TECHNICAL.md` | Tech stack and patterns |
| `docs/architecture/frontend/ADMIN.md` | Admin panel (separate from client) |

---

For gaps and implementation status, see `../TODO.md`.
