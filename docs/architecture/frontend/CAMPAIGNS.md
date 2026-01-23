# Frontend Campaign Management Architecture

**Purpose:** Architecture spec for Agency OS campaign management UI.
**Last Updated:** 2026-01-22
**Status:** Specification Complete

---

## 1. Overview

### Purpose

The campaign management UI enables clients to view, create, and control their outreach campaigns. The key innovation is **priority-based allocation** where clients think in terms of effort distribution rather than lead counts.

### Design Philosophy

| Principle | Description |
|-----------|-------------|
| **Priority Sliders, Not Lead Counts** | Clients allocate effort as percentages, not raw numbers |
| **Auto-Balance to 100%** | Adjusting one campaign proportionally adjusts others |
| **Min 10%, Max 80%** | Constraints prevent campaigns from being starved or monopolized |
| **AI Suggested Badge** | Mark AI-generated campaigns distinctly from custom ones |
| **Outcome Focus** | Show meetings booked and reply rates, not lead counts |

### Mental Model

**What client thinks:**
> "I want to put more focus on my Tech Decision Makers campaign this month"

**What actually happens:**
> System calculates: 50% of 1,250 leads = 625 leads sourced and enriched immediately

**Client never sees:**
> "625 leads allocated"

---

## 2. Routes

### Campaign Route Structure

```
/dashboard/campaigns           -> Campaign list with priority sliders
/dashboard/campaigns/[id]      -> Campaign detail + sequences + leads
/dashboard/campaigns/new       -> New campaign creation wizard
```

### Route Files

| Route | File | Purpose |
|-------|------|---------|
| `/dashboard/campaigns` | `frontend/app/dashboard/campaigns/page.tsx` | Campaign list with priority sliders and quick actions |
| `/dashboard/campaigns/[id]` | `frontend/app/dashboard/campaigns/[id]/page.tsx` | Campaign detail with metrics, sequences, leads |
| `/dashboard/campaigns/new` | `frontend/app/dashboard/campaigns/new/page.tsx` | Simplified campaign creation (name, permission mode) |

---

## 3. Data Available

### Campaign Model

```typescript
// frontend/lib/api/types.ts

interface Campaign {
  id: string;
  client_id: string;
  name: string;
  description: string | null;
  status: "draft" | "active" | "paused" | "completed";
  permission_mode: "autopilot" | "co_pilot" | "manual" | null;

  // Channel Allocations (internal, system-managed)
  allocation_email: number;       // 0-100%
  allocation_sms: number;         // 0-100%
  allocation_linkedin: number;    // 0-100%
  allocation_voice: number;       // 0-100%
  allocation_mail: number;        // 0-100%

  // Scheduling
  daily_limit: number;
  start_date: string | null;
  end_date: string | null;

  // Metrics (client-visible)
  total_leads: number;            // Hidden from client
  leads_contacted: number;        // Hidden from client
  leads_replied: number;          // Show as reply count
  leads_converted: number;        // Show as meetings
  reply_rate: number;             // Key metric
  conversion_rate: number;        // Show rate

  created_at: string;
  updated_at: string;
}

interface CampaignCreate {
  name: string;
  description?: string;
  permission_mode?: "autopilot" | "co_pilot" | "manual";
}

interface CampaignUpdate {
  name?: string;
  description?: string;
  permission_mode?: "autopilot" | "co_pilot" | "manual";
  status?: "draft" | "active" | "paused" | "completed";
}
```

### Campaign with Priority (Extended)

```typescript
// For priority slider display
interface CampaignWithPriority extends Campaign {
  priority_pct: number;           // 0-100, all campaigns sum to 100
  is_ai_suggested: boolean;       // Show AI badge
  meetings_this_month: number;    // Key outcome metric
  show_rate: number;              // Meetings showed / meetings booked
}

// For allocation API
interface CampaignAllocation {
  campaign_id: string;
  priority_pct: number;           // Must sum to 100 across all
}

interface AllocateRequest {
  allocations: CampaignAllocation[];
}

interface AllocateResponse {
  status: "processing" | "complete" | "error";
  message: string;
  estimated_seconds?: number;
}
```

### Sequence Model

```typescript
interface CampaignSequence {
  id: string;
  campaign_id: string;
  name: string;
  channel: "email" | "sms" | "linkedin" | "voice";
  step_number: number;
  delay_days: number;
  template_id: string | null;
  subject?: string;              // For email
  content_preview?: string;
  is_active: boolean;
  created_at: string;
}
```

### Tier Limits

| Tier | Max Campaigns | Monthly Meeting Target |
|------|---------------|------------------------|
| Starter (Ignition) | 2 | 5-10 meetings |
| Growth (Velocity) | 3 | 15-25 meetings |
| Scale (Dominance) | 5 | 30-50 meetings |
| Enterprise | Unlimited | 50+ meetings |

---

## 4. User Actions

### Campaign List Page Actions

| Action | Component | API Call | Status |
|--------|-----------|----------|--------|
| Adjust priority slider | PrioritySlider | Optimistic + debounce | NOT IMPLEMENTED |
| Confirm priorities | ConfirmButton | `POST /campaigns/allocate` | NOT IMPLEMENTED |
| Cancel changes | CancelButton | Reset local state | NOT IMPLEMENTED |
| Activate campaign | DropdownMenu | `POST /campaigns/{id}/activate` | IMPLEMENTED |
| Pause campaign | DropdownMenu | `POST /campaigns/{id}/pause` | IMPLEMENTED |
| Navigate to detail | CampaignCard click | - | IMPLEMENTED |
| Create new campaign | Button | Navigate to /new | IMPLEMENTED |
| Search campaigns | Input | Client-side filter | IMPLEMENTED |
| Filter by status | ButtonGroup | Client-side filter | IMPLEMENTED |

### Campaign Detail Page Actions

| Action | Component | API Call | Status |
|--------|-----------|----------|--------|
| Edit campaign name | Inline edit | `PATCH /campaigns/{id}` | NOT IMPLEMENTED |
| Change permission mode | PermissionModeSelector | `PATCH /campaigns/{id}` | IMPLEMENTED |
| Activate/Pause | Button | `POST /campaigns/{id}/activate` | IMPLEMENTED |
| View sequences | Tabs | `GET /campaigns/{id}/sequences` | IMPLEMENTED |
| View leads | Tabs | `GET /campaigns/{id}/leads` | IMPLEMENTED |
| View activity | Tabs | `GET /campaigns/{id}/activities` | NOT IMPLEMENTED |
| Delete campaign | Settings | `DELETE /campaigns/{id}` | NOT IMPLEMENTED |

### New Campaign Page Actions

| Action | Component | API Call | Status |
|--------|-----------|----------|--------|
| Enter name | Input | - | IMPLEMENTED |
| Enter description | Input | - | IMPLEMENTED |
| Select permission mode | PermissionModeSelector | - | IMPLEMENTED |
| View inherited ICP | ReadOnly display | `GET /clients/{id}/icp` | IMPLEMENTED |
| Edit ICP | Link | Navigate to /settings/icp | IMPLEMENTED |
| Create campaign | Button | `POST /campaigns` | IMPLEMENTED |

---

## 5. Components (Existing)

### Campaign Components

| Component | File | Props | Purpose |
|-----------|------|-------|---------|
| PermissionModeSelector | `components/campaigns/permission-mode-selector.tsx` | `value`, `onChange` | Autopilot/Co-pilot/Manual selection |

### Page Components

| Component | File | Purpose |
|-----------|------|---------|
| CampaignsPage | `app/dashboard/campaigns/page.tsx` | Campaign list with search, filters, grid |
| CampaignDetailPage | `app/dashboard/campaigns/[id]/page.tsx` | Campaign detail with stats, channels, target settings |
| NewCampaignPage | `app/dashboard/campaigns/new/page.tsx` | Simplified campaign creation form |

### Shared UI Components

| Component | File | Purpose |
|-----------|------|---------|
| Card, CardHeader, CardContent | `components/ui/card.tsx` | Campaign card layout |
| Badge | `components/ui/badge.tsx` | Status badges (active, paused, draft, AI) |
| Button | `components/ui/button.tsx` | Actions |
| Input | `components/ui/input.tsx` | Search, name input |
| DropdownMenu | `components/ui/dropdown-menu.tsx` | Campaign actions menu |
| CardListSkeleton | `components/ui/loading-skeleton.tsx` | Loading state |
| ErrorState | `components/ui/error-state.tsx` | Error display |
| NoItemsState, NoSearchResults | `components/ui/empty-state.tsx` | Empty states |

---

## 6. Components to Create

### PrioritySlider

```typescript
// frontend/components/campaigns/PrioritySlider.tsx

interface PrioritySliderProps {
  campaignId: string;
  campaignName: string;
  priority: number;                    // 0-100
  onPriorityChange: (value: number) => void;
  meetingsBooked: number;
  replyRate: number;
  showRate: number;
  isAISuggested: boolean;
  isDisabled?: boolean;
  min?: number;                        // Default 10
  max?: number;                        // Default 80
}

/**
 * Individual campaign priority slider:
 * - Campaign name with AI badge if suggested
 * - Draggable slider with percentage display
 * - Min 10%, Max 80% constraints
 * - Meetings, reply rate, show rate below
 * - Yellow border when pending changes
 */
```

**Design:**
```
+-----------------------------------------------------------+
| [AI] Tech Decision Makers                                  |
|                                                            |
| Priority                                                   |
| Low o=========[*]============o High                        |
|                40%                                         |
|                                                            |
| +--------------------------------------------------------+ |
| | This Month                                              | |
| | 6 meetings booked  |  3.8% reply rate  |  85% show rate | |
| +--------------------------------------------------------+ |
+-----------------------------------------------------------+
```

### CampaignPriorityCard

```typescript
// frontend/components/campaigns/CampaignPriorityCard.tsx

interface CampaignPriorityCardProps {
  campaign: CampaignWithPriority;
  priority: number;
  onPriorityChange: (value: number) => void;
  isPending: boolean;                  // Shows yellow border
  onActivate?: () => void;
  onPause?: () => void;
  onNavigate?: () => void;
}

/**
 * Full campaign card with:
 * - Header: Campaign name, AI badge, status badge, menu
 * - Priority slider
 * - Metrics row: meetings, reply rate, show rate
 * - Active channels indicator
 */
```

### CampaignAllocationManager

```typescript
// frontend/components/campaigns/CampaignAllocationManager.tsx

interface CampaignAllocationManagerProps {
  campaigns: CampaignWithPriority[];
  maxCampaigns: number;                // From tier
  onConfirm: (allocations: CampaignAllocation[]) => void;
  isConfirming: boolean;
}

/**
 * Container managing all priority sliders:
 * - Header: "YOUR CAMPAIGNS" + "X of Y slots used" + Add button
 * - List of CampaignPriorityCard components
 * - Empty slot placeholder if under limit
 * - Footer: Total percentage (must be 100%)
 * - Action bar: Cancel + Confirm when pending
 * - Auto-balance logic when any slider changes
 */
```

**States:**
1. **Initial** - Sliders at current allocation, no action buttons
2. **Pending** - Yellow borders, "Changes pending" message, Cancel + Confirm buttons
3. **Processing** - Spinner, "Preparing your campaigns..."
4. **Success** - Checkmark, "Campaigns ready!"
5. **Error** - Error message, Try Again + Contact Support buttons

### SequenceBuilder

```typescript
// frontend/components/campaigns/SequenceBuilder.tsx

interface SequenceBuilderProps {
  campaignId: string;
  sequences: CampaignSequence[];
  onSave: (sequences: CampaignSequence[]) => void;
  isReadOnly?: boolean;
}

/**
 * Visual sequence editor:
 * - Timeline view of sequence steps
 * - Add/remove/reorder steps
 * - Configure delay between steps
 * - Preview content at each step
 * - Channel selection per step
 */
```

### CampaignMetricsPanel

```typescript
// frontend/components/campaigns/CampaignMetricsPanel.tsx

interface CampaignMetricsPanelProps {
  campaign: Campaign;
}

/**
 * Metrics display for campaign detail:
 * - Meetings booked (large number)
 * - Show rate percentage
 * - Reply rate percentage
 * - Active sequences count
 * - Channel allocation breakdown
 */
```

### CampaignTabs

```typescript
// frontend/components/campaigns/CampaignTabs.tsx

interface CampaignTabsProps {
  campaignId: string;
  activeTab: "overview" | "sequences" | "leads" | "activity";
  onTabChange: (tab: string) => void;
}

/**
 * Tab navigation for campaign detail:
 * - Overview: Metrics, settings
 * - Sequences: Email sequence builder
 * - Leads: Leads in this campaign
 * - Activity: Recent actions
 */
```

---

## 7. API Integration

### Current Hooks

| Hook | File | Query Key | Endpoint | Status |
|------|------|-----------|----------|--------|
| `useCampaigns` | `hooks/use-campaigns.ts` | `["campaigns", clientId, params]` | `GET /api/v1/clients/{id}/campaigns` | IMPLEMENTED |
| `useCampaign` | `hooks/use-campaigns.ts` | `["campaign", clientId, campaignId]` | `GET /api/v1/clients/{id}/campaigns/{id}` | IMPLEMENTED |
| `useCampaignLeads` | `hooks/use-campaigns.ts` | `["campaign-leads", clientId, campaignId, params]` | `GET /api/v1/clients/{id}/campaigns/{id}/leads` | IMPLEMENTED |
| `useCampaignSequences` | `hooks/use-campaigns.ts` | `["campaign-sequences", clientId, campaignId]` | `GET /api/v1/clients/{id}/campaigns/{id}/sequences` | IMPLEMENTED |
| `useCreateCampaign` | `hooks/use-campaigns.ts` | N/A (mutation) | `POST /api/v1/clients/{id}/campaigns` | IMPLEMENTED |
| `useUpdateCampaign` | `hooks/use-campaigns.ts` | N/A (mutation) | `PUT /api/v1/clients/{id}/campaigns/{id}` | IMPLEMENTED |
| `useUpdateCampaignStatus` | `hooks/use-campaigns.ts` | N/A (mutation) | `PATCH /api/v1/clients/{id}/campaigns/{id}/status` | IMPLEMENTED |
| `useActivateCampaign` | `hooks/use-campaigns.ts` | N/A (mutation) | `POST /api/v1/clients/{id}/campaigns/{id}/activate` | IMPLEMENTED |
| `usePauseCampaign` | `hooks/use-campaigns.ts` | N/A (mutation) | `POST /api/v1/clients/{id}/campaigns/{id}/pause` | IMPLEMENTED |
| `useDeleteCampaign` | `hooks/use-campaigns.ts` | N/A (mutation) | `DELETE /api/v1/clients/{id}/campaigns/{id}` | IMPLEMENTED |

### Mutations

```typescript
// frontend/hooks/use-campaigns.ts

export function useCreateCampaign() {
  const { clientId } = useClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CampaignCreate) => createCampaign(clientId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campaigns", clientId] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats", clientId] });
    },
  });
}

export function useActivateCampaign() {
  const { clientId } = useClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (campaignId: string) => activateCampaign(clientId!, campaignId),
    onSuccess: (data, campaignId) => {
      queryClient.setQueryData(["campaign", clientId, campaignId], data);
      queryClient.invalidateQueries({ queryKey: ["campaigns", clientId] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats", clientId] });
    },
  });
}
```

### Hooks to Create

| Hook | Query Key | Endpoint | Purpose |
|------|-----------|----------|---------|
| `useCampaignPriorities` | `["campaign-priorities", clientId]` | `GET /api/v1/clients/{id}/campaigns` | Get campaigns with priority_pct |
| `useAllocateCampaigns` | N/A (mutation) | `POST /api/v1/clients/{id}/campaigns/allocate` | Batch update priorities |
| `useCampaignActivities` | `["campaign-activities", clientId, campaignId]` | `GET /api/v1/campaigns/{id}/activities` | Activity feed for campaign |

---

## 8. API Gaps

### Missing Endpoints

| Endpoint | Purpose | Priority | Backend File |
|----------|---------|----------|--------------|
| `POST /api/v1/clients/{id}/campaigns/allocate` | Batch update campaign priorities | P1 | `src/api/routes/campaigns.py` |
| `GET /api/v1/campaigns/{id}/activities` | Campaign-specific activity feed | P2 | `src/api/routes/campaigns.py` |
| `PATCH /api/v1/campaigns/{id}/sequences` | Update sequence configuration | P3 | `src/api/routes/campaigns.py` |

### Missing Fields

| Field | Model | Purpose | Priority |
|-------|-------|---------|----------|
| `priority_pct` | Campaign | Lead allocation percentage | P1 |
| `is_ai_suggested` | Campaign | Show AI badge | P2 |
| `meetings_this_month` | Campaign metrics | Current month meetings | P1 |
| `show_rate` | Campaign metrics | Meetings showed / booked | P1 |

### API Response Shapes Needed

```typescript
// POST /api/v1/clients/{id}/campaigns/allocate
interface AllocateRequest {
  allocations: Array<{
    campaign_id: string;
    priority_pct: number;
  }>;
}

interface AllocateResponse {
  status: "processing" | "complete" | "error";
  message: string;
  estimated_seconds?: number;
}

// GET /api/v1/campaigns/{id}/activities
interface CampaignActivitiesResponse {
  items: Activity[];
  total: number;
  has_more: boolean;
}

// Extended campaign response with metrics
interface CampaignDetailResponse extends Campaign {
  priority_pct: number;
  is_ai_suggested: boolean;
  metrics: {
    meetings_this_month: number;
    meetings_showed: number;
    show_rate: number;
    active_sequences: number;
    leads_in_sequence: number;
  };
}
```

---

## 9. State Management

### Priority Slider State

```typescript
// Local state for priority management
interface PriorityState {
  original: Record<string, number>;    // campaignId -> original priority
  current: Record<string, number>;     // campaignId -> current priority
  isPending: boolean;                  // Any changes from original?
  isProcessing: boolean;               // API call in progress?
}

// Auto-balance algorithm
function autoBalance(
  priorities: Record<string, number>,
  changedId: string,
  newValue: number,
  min: number = 10,
  max: number = 80
): Record<string, number> {
  const result = { ...priorities };
  const oldValue = result[changedId];
  const delta = newValue - oldValue;

  // Clamp the changed value
  result[changedId] = Math.max(min, Math.min(max, newValue));

  // Distribute delta proportionally to other campaigns
  const otherIds = Object.keys(result).filter(id => id !== changedId);
  const otherTotal = otherIds.reduce((sum, id) => sum + result[id], 0);

  for (const id of otherIds) {
    const proportion = result[id] / otherTotal;
    const adjustment = delta * proportion;
    result[id] = Math.max(min, Math.min(max, result[id] - adjustment));
  }

  // Normalize to exactly 100%
  const total = Object.values(result).reduce((sum, v) => sum + v, 0);
  const factor = 100 / total;
  for (const id of Object.keys(result)) {
    result[id] = Math.round(result[id] * factor);
  }

  return result;
}
```

### Optimistic Updates for Allocation

```typescript
// useMutation with optimistic update
const allocateMutation = useMutation({
  mutationFn: (allocations: CampaignAllocation[]) =>
    api.post(`/clients/${clientId}/campaigns/allocate`, { allocations }),

  onMutate: async (newAllocations) => {
    await queryClient.cancelQueries({ queryKey: ["campaigns", clientId] });

    const previous = queryClient.getQueryData(["campaigns", clientId]);

    // Optimistically update campaign priorities
    queryClient.setQueryData(["campaigns", clientId], (old: any) => ({
      ...old,
      items: old.items.map((c: Campaign) => {
        const allocation = newAllocations.find(a => a.campaign_id === c.id);
        return allocation ? { ...c, priority_pct: allocation.priority_pct } : c;
      }),
    }));

    return { previous };
  },

  onError: (err, variables, context) => {
    // Rollback on error
    if (context?.previous) {
      queryClient.setQueryData(["campaigns", clientId], context.previous);
    }
  },

  onSettled: () => {
    queryClient.invalidateQueries({ queryKey: ["campaigns", clientId] });
  },
});
```

### React Query Configuration

```typescript
const CAMPAIGN_STALE_TIMES = {
  list: 30 * 1000,           // 30 seconds
  detail: 60 * 1000,         // 1 minute
  sequences: 5 * 60 * 1000,  // 5 minutes
  leads: 30 * 1000,          // 30 seconds
  activities: 10 * 1000,     // 10 seconds
};
```

---

## 10. v0 Integration

### Ready for Visual Design

| Section | Component | Ready? | Notes |
|---------|-----------|--------|-------|
| Campaign List | CampaignsPage | PARTIAL | Layout exists, needs priority sliders |
| Campaign Card | Card component | YES | Using shadcn/ui Card |
| Status Badge | Badge | YES | Variants for active/paused/draft |
| Permission Mode | PermissionModeSelector | YES | Fully functional |
| Campaign Detail | CampaignDetailPage | PARTIAL | Placeholder data, needs real API |
| New Campaign | NewCampaignPage | YES | Fully functional |
| Priority Slider | - | NO | Needs PrioritySlider component |
| Sequence Builder | - | NO | Needs SequenceBuilder component |
| Activity Tab | - | NO | Needs CampaignActivityFeed component |

### CSS Variables (Tailwind Config)

```css
/* Campaign card states */
.campaign-card-initial {
  @apply border-border;
}

.campaign-card-pending {
  @apply border-yellow-500 ring-1 ring-yellow-500/20;
}

.campaign-card-processing {
  @apply opacity-70 pointer-events-none;
}

/* Priority slider */
.priority-slider-track {
  @apply h-2 bg-muted rounded-full;
}

.priority-slider-thumb {
  @apply h-4 w-4 bg-primary rounded-full shadow-md;
  @apply focus:ring-2 focus:ring-primary/50;
}

/* AI badge */
.badge-ai-suggested {
  @apply bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400;
}
```

### Component States for Design

All campaign components should handle:
- **Loading** - CardListSkeleton, Skeleton
- **Error** - ErrorState with retry
- **Empty** - NoItemsState with create button
- **Pending** - Yellow border, action buttons
- **Processing** - Spinner, disabled state
- **Success** - Checkmark, success message

---

## 11. Wireframes

### Campaign List Page

```
+------------------------------------------------------------------+
| AGENCY OS                                    [Client] [Settings] |
+------------------------------------------------------------------+
|        |                                                          |
| SIDEBAR|  CAMPAIGNS                              [ + New Campaign ]|
|        |                                                          |
| [Home] |  [ Search campaigns...        ] [Active] [Paused] [Draft]|
| [Camp] |                                                          |
| [Leads]|  YOUR CAMPAIGNS                                          |
| [Reply]|  3 of 3 slots used                                       |
| [Reprt]|                                                          |
| [Setng]|  +-------------------------------------------------+     |
|        |  | [AI] Tech Decision Makers            Active [v] |     |
|        |  |                                                 |     |
|        |  | Priority                                        |     |
|        |  | Low o=======[*]==========o High         40%     |     |
|        |  |                                                 |     |
|        |  | 6 meetings  |  3.8% reply  |  85% show          |     |
|        |  +-------------------------------------------------+     |
|        |                                                          |
|        |  +-------------------------------------------------+     |
|        |  | [AI] Series A Startups              Active [v]  |     |
|        |  |                                                 |     |
|        |  | Priority                                        |     |
|        |  | Low o====[*]============o High          35%     |     |
|        |  |                                                 |     |
|        |  | 4 meetings  |  2.9% reply  |  80% show          |     |
|        |  +-------------------------------------------------+     |
|        |                                                          |
|        |  +-------------------------------------------------+     |
|        |  | My Custom Campaign                  Paused [v]  |     |
|        |  |                                                 |     |
|        |  | Priority                                        |     |
|        |  | Low o==[*]==============o High          25%     |     |
|        |  |                                                 |     |
|        |  | 2 meetings  |  1.8% reply  |  75% show          |     |
|        |  +-------------------------------------------------+     |
|        |                                                          |
|        |  +---------------------------------------------------+   |
|        |  |  ! Changes pending                                |   |
|        |  |                                                   |   |
|        |  |  [ Cancel ]                 [ Confirm & Activate ]|   |
|        |  +---------------------------------------------------+   |
|        |                                                          |
+------------------------------------------------------------------+
```

### Campaign Detail Page

```
+------------------------------------------------------------------+
| AGENCY OS                                    [Client] [Settings] |
+------------------------------------------------------------------+
|        |                                                          |
| SIDEBAR|  < Back to Campaigns                                     |
|        |                                                          |
| [Home] |  Tech Decision Makers                    [Active] [Pause]|
| [Camp] |  Targeting Series A-B tech startups                      |
| [Leads]|                                                          |
| [Reply]|  +-----------+ +-----------+ +-----------+ +-----------+ |
| [Reprt]|  | Meetings  | | Show Rate | | Reply Rate| | Sequences | |
| [Setng]|  |    12     | |   85%     | |   3.8%    | |     5     | |
|        |  +-----------+ +-----------+ +-----------+ +-----------+ |
|        |                                                          |
|        |  [ Overview ] [ Sequences ] [ Leads ] [ Activity ]       |
|        |  ---------------------------------------------------------
|        |                                                          |
|        |  +-------------------------+ +-------------------------+ |
|        |  | Channel Allocation      | | Target Settings         | |
|        |  |                         | |                         | |
|        |  | Email     [====]  60%   | | Industries              | |
|        |  | SMS       [==]    20%   | | [Technology] [SaaS]     | |
|        |  | LinkedIn  [==]    20%   | | [Fintech]               | |
|        |  |                         | |                         | |
|        |  |                         | | Titles                  | |
|        |  |                         | | [CEO] [CTO] [Founder]   | |
|        |  |                         | |                         | |
|        |  |                         | | Company Size            | |
|        |  |                         | | [10-50] [51-200]        | |
|        |  +-------------------------+ +-------------------------+ |
|        |                                                          |
|        |  +-----------------------------------------------------+ |
|        |  | Campaign Leads                     [ View All Leads ]| |
|        |  |                                                     | |
|        |  | Lead list would be displayed here                   | |
|        |  +-----------------------------------------------------+ |
|        |                                                          |
+------------------------------------------------------------------+
```

### Processing State (Overlay)

```
+------------------------------------------------------------------+
|                                                                    |
|          +------------------------------------------+              |
|          |                                          |              |
|          |     (O)  Preparing your campaigns...     |              |
|          |                                          |              |
|          |          Finding ideal prospects         |              |
|          |          Researching & qualifying        |              |
|          |          Setting up outreach sequences   |              |
|          |                                          |              |
|          |     This usually takes 30-60 seconds     |              |
|          |                                          |              |
|          +------------------------------------------+              |
|                                                                    |
+------------------------------------------------------------------+
```

### Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| `lg` (1024px+) | Sidebar visible, campaign cards in grid |
| `md` (768px) | Sidebar collapsible, single column cards |
| `sm` (< 768px) | Sidebar hidden, full-width cards |

---

## Related Documentation

| Doc | Purpose |
|-----|---------|
| `frontend/design/dashboard/campaigns.md` | Campaign allocation UI design spec |
| `docs/architecture/business/CAMPAIGNS.md` | Backend campaign lifecycle |
| `docs/architecture/frontend/DASHBOARD.md` | Dashboard architecture |
| `docs/architecture/frontend/TECHNICAL.md` | Tech stack and patterns |

---

For gaps and implementation status, see `../TODO.md`.
