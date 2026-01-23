# Frontend Lead Management Architecture

**Purpose:** Architecture spec for Agency OS lead list and detail pages.
**Last Updated:** 2026-01-22
**Status:** Specification Complete

---

## 1. Overview

### Purpose

The lead management UI displays leads with their ALS (Agency Lead Score) tiers, enrichment status, and activity history. Clients see a curated view focused on outcomes and engagement status, while internal scoring details remain hidden.

### Design Philosophy

| Principle | Description |
|-----------|-------------|
| **ALS Tiers, Not Raw Scores** | Show "Hot", "Warm", "Cool" labels instead of numeric scores to clients |
| **Activity as Proof of Work** | Timeline shows what the system is doing for each lead |
| **Curated Client View** | Hide internal enrichment costs, source waterfall details |
| **Outcome Focus** | Emphasize meetings booked, replies received, not contact counts |

### ALS Tier Display Rules

| Tier | Score Range | Color | Client Label | Internal Label |
|------|-------------|-------|--------------|----------------|
| Hot | 85-100 | Red/Orange (`bg-orange-500`) | "High Priority" | "Hot" |
| Warm | 60-84 | Yellow (`bg-yellow-500`) | "Engaged" | "Warm" |
| Cool | 35-59 | Blue (`bg-blue-500`) | "Nurturing" | "Cool" |
| Cold | 20-34 | Gray (`bg-gray-500`) | "Low Activity" | "Cold" |
| Dead | <20 | Dark Gray (`bg-gray-600`) | "Inactive" | "Dead" |

### Data Visibility Rules

| Data Type | Client Sees | Admin Sees |
|-----------|-------------|------------|
| Name, company, title | YES | YES |
| ALS tier (Hot/Warm/etc) | YES | YES |
| Raw ALS score (0-100) | NO | YES |
| Activity timeline | YES | YES |
| Enrichment source (Apollo/Clay) | NO | YES |
| SDK cost per lead | NO | YES |
| Source waterfall details | NO | YES |
| Email status (verified/guessed) | NO | YES |

---

## 2. Routes

### Lead Route Structure

```
/dashboard/leads              -> Lead list with ALS tier filters
/dashboard/leads/[id]         -> Lead detail with enrichment and timeline
```

### Route Files

| Route | File | Purpose |
|-------|------|---------|
| `/dashboard/leads` | `frontend/app/dashboard/leads/page.tsx` | Lead list with search, tier filtering, pagination |
| `/dashboard/leads/[id]` | `frontend/app/dashboard/leads/[id]/page.tsx` | Lead detail with ALS breakdown, activities, contact info |

---

## 3. Data Available

### Lead Model

```typescript
// frontend/lib/api/types.ts

interface Lead {
  id: UUID;
  client_id: UUID;
  campaign_id: UUID;

  // Contact Info (Client Visible)
  email: string;
  phone: string | null;
  first_name: string | null;
  last_name: string | null;
  title: string | null;
  company: string | null;
  linkedin_url: string | null;
  domain: string | null;

  // ALS Score (Tier visible, raw score hidden from client)
  als_score: number | null;           // Hidden from client
  als_tier: ALSTier | null;           // Visible to client as label
  als_data_quality: number | null;    // Hidden from client
  als_authority: number | null;       // Hidden from client
  als_company_fit: number | null;     // Hidden from client
  als_timing: number | null;          // Hidden from client
  als_risk: number | null;            // Hidden from client

  // Organization (Client Visible)
  organization_industry: string | null;
  organization_employee_count: number | null;
  organization_country: string | null;

  // Status
  status: LeadStatus;
  created_at: string;
  updated_at: string;
}

type LeadStatus =
  | "new"           // Just added, not enriched
  | "enriched"      // Enriched, not scored
  | "scored"        // ALS calculated
  | "in_sequence"   // Active outreach
  | "converted"     // Meeting booked
  | "unsubscribed"  // Opted out
  | "bounced";      // Email bounced

type ALSTier = "hot" | "warm" | "cool" | "cold" | "dead";
```

### Lead Filters

```typescript
interface LeadFilters {
  campaign_id?: UUID;
  status?: LeadStatus;
  tier?: ALSTier;
  search?: string;
}
```

### Activity Model

```typescript
interface Activity {
  id: UUID;
  client_id: UUID;
  campaign_id: UUID;
  lead_id: UUID;
  channel: "email" | "sms" | "linkedin" | "voice" | "mail";
  action: string;
  provider_message_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;

  // Activity details
  sequence_step?: number | null;
  subject?: string | null;
  content_preview?: string | null;
  intent?: string | null;            // Reply intent classification

  // Joined data
  lead?: Lead;
  campaign?: Campaign;
}
```

### Deep Research Data (Hot Leads)

```typescript
// frontend/lib/api/leads.ts

interface DeepResearchData {
  lead_id: string;
  status: "not_started" | "in_progress" | "complete" | "failed";
  icebreaker_hook: string | null;
  profile_summary: string | null;
  recent_activity: string | null;
  posts_found: number;
  confidence: number | null;
  run_at: string | null;
  social_posts: {
    id: string;
    source: string;
    content: string;
    date: string | null;
    hook: string | null;
  }[];
  error: string | null;
}
```

---

## 4. User Actions

### Lead List Page Actions

| Action | Component | API Call | Status |
|--------|-----------|----------|--------|
| Search leads | Input | Client-side filter | IMPLEMENTED |
| Filter by tier | TierCards | Client-side filter | IMPLEMENTED |
| Filter by status | FilterDropdown | Client-side filter | NOT IMPLEMENTED |
| Paginate | PaginationButtons | `GET /leads?page=X` | IMPLEMENTED |
| Navigate to detail | TableRow click | - | IMPLEMENTED |
| Export leads | Button | `GET /leads/export` | NOT IMPLEMENTED |
| Import leads | Button | `POST /leads/bulk` | NOT IMPLEMENTED |
| Bulk select | Checkbox | - | NOT IMPLEMENTED |
| Bulk enrich | Button | `POST /leads/bulk-enrich` | NOT IMPLEMENTED |

### Lead Detail Page Actions

| Action | Component | API Call | Status |
|--------|-----------|----------|--------|
| View contact info | ContactCard | - | IMPLEMENTED |
| View company info | CompanyCard | - | IMPLEMENTED |
| View ALS breakdown | ALSCard | - | IMPLEMENTED |
| View activity timeline | ActivityTimeline | `GET /leads/{id}/activities` | IMPLEMENTED |
| Expand activity content | Collapsible | - | IMPLEMENTED |
| Copy activity content | Button | - | IMPLEMENTED |
| Send manual email | Button | Navigate to compose | NOT IMPLEMENTED |
| Re-score lead | Button | `POST /leads/{id}/score` | NOT IMPLEMENTED |
| Trigger deep research | Button | `POST /leads/{id}/research` | NOT IMPLEMENTED |
| Pause lead | Button | `PATCH /leads/{id}` | NOT IMPLEMENTED |
| Archive lead | Button | `DELETE /leads/{id}` | NOT IMPLEMENTED |

---

## 5. Components (Existing)

### Lead Components

| Component | File | Props | Purpose |
|-----------|------|-------|---------|
| ALSScorecard | `components/leads/ALSScorecard.tsx` | `score`, `breakdown?`, `showBadge?`, `size?` | ALS score with radar chart tooltip |

### Page Components

| Component | File | Purpose |
|-----------|------|---------|
| LeadsPage | `app/dashboard/leads/page.tsx` | Lead list with tier filters, search, pagination |
| LeadDetailPage | `app/dashboard/leads/[id]/page.tsx` | Lead detail with ALS breakdown, timeline |
| ActivityTimelineItem | Inline in detail page | Single activity with expandable content |

### Shared UI Components

| Component | File | Purpose |
|-----------|------|---------|
| Card, CardHeader, CardContent | `components/ui/card.tsx` | Section layout |
| Badge | `components/ui/badge.tsx` | Tier and status badges |
| Button | `components/ui/button.tsx` | Actions |
| Input | `components/ui/input.tsx` | Search |
| Collapsible | `components/ui/collapsible.tsx` | Activity content expand |
| TableSkeleton | `components/ui/loading-skeleton.tsx` | Loading state |
| ErrorState | `components/ui/error-state.tsx` | Error display |
| EmptyState, NoSearchResults | `components/ui/empty-state.tsx` | Empty states |

---

## 6. Components to Create

### ALSTierBadge (Simplified)

```typescript
// frontend/components/leads/ALSTierBadge.tsx

interface ALSTierBadgeProps {
  tier: ALSTier;
  showLabel?: boolean;      // Show "High Priority" instead of "Hot"
  size?: "sm" | "md" | "lg";
}

/**
 * Color-coded tier badge without score number:
 * - Hot: Orange with "High Priority" label
 * - Warm: Yellow with "Engaged" label
 * - Cool: Blue with "Nurturing" label
 * - Cold: Gray with "Low Activity" label
 * - Dead: Dark gray with "Inactive" label
 */
```

**Design:**
```
+---------------+  +----------+  +------------+
| High Priority |  | Engaged  |  | Nurturing  |
| (orange)      |  | (yellow) |  | (blue)     |
+---------------+  +----------+  +------------+
```

### LeadEnrichmentCard

```typescript
// frontend/components/leads/LeadEnrichmentCard.tsx

interface LeadEnrichmentCardProps {
  lead: Lead;
  research?: DeepResearchData | null;
  showInternalDetails?: boolean;   // Admin only
}

/**
 * Company and enrichment information:
 * - Company name, industry, size
 * - Location
 * - Recent signals (hiring, funding) if available
 * - Deep research summary for Hot leads
 * - Icebreaker hooks (if SDK enriched)
 */
```

**Design:**
```
+------------------------------------------+
| ENRICHMENT DATA                          |
+------------------------------------------+
| Company: TechCorp                        |
| Industry: Technology                     |
| Size: 50-200 employees                   |
| Location: Sydney, Australia              |
+------------------------------------------+
| SIGNALS                                  |
| [Hiring] 5 open roles                    |
| [Funding] Series B - Q4 2025             |
+------------------------------------------+
| ICEBREAKER (Hot leads only)              |
| "Noticed your recent product launch..."  |
+------------------------------------------+
```

### LeadActivityTimeline

```typescript
// frontend/components/leads/LeadActivityTimeline.tsx

interface LeadActivityTimelineProps {
  activities: Activity[];
  isLoading: boolean;
  onLoadMore?: () => void;
  maxInitial?: number;
}

/**
 * Vertical timeline of lead interactions:
 * - Channel icon with color coding
 * - Action description
 * - Timestamp (relative)
 * - Expandable content preview
 * - Reply intent badges
 * - Load more pagination
 */
```

**Design:**
```
+------------------------------------------+
| ACTIVITY TIMELINE                        |
+------------------------------------------+
| O Email sent - "Quick question about..." |
| |     2 hours ago                        |
| |     [Show content v]                   |
| |                                        |
| O Reply received - Positive Intent       |
| |     1 hour ago                         |
| |     "Hi, yes we'd be interested..."    |
| |     [Expand v] [Copy]                  |
| |                                        |
| O Meeting booked - Discovery Call        |
|       30 minutes ago                     |
|       Tomorrow 2:00 PM                   |
+------------------------------------------+
```

### LeadQuickActions

```typescript
// frontend/components/leads/LeadQuickActions.tsx

interface LeadQuickActionsProps {
  lead: Lead;
  onPause: () => void;
  onArchive: () => void;
  onPrioritize: () => void;
  isLoading: boolean;
}

/**
 * Quick action buttons for lead management:
 * - Pause outreach (temporary hold)
 * - Archive (soft delete)
 * - Prioritize (bump to top of queue)
 * - Re-score
 */
```

**Design:**
```
+------------------------------------------+
| [Pause] [Archive] [Prioritize] [Re-score]|
+------------------------------------------+
```

### LeadStatusProgress

```typescript
// frontend/components/leads/LeadStatusProgress.tsx

interface LeadStatusProgressProps {
  status: LeadStatus;
  showLabels?: boolean;
}

/**
 * Visual progress indicator for lead status:
 * new -> enriched -> scored -> in_sequence -> converted
 */
```

**Design:**
```
[New]-->[Enriched]-->[Scored]-->[In Sequence]-->[Converted]
  O        O           *            O              O
                    (current)
```

### LeadBulkActions

```typescript
// frontend/components/leads/LeadBulkActions.tsx

interface LeadBulkActionsProps {
  selectedIds: string[];
  onEnrich: () => void;
  onPause: () => void;
  onArchive: () => void;
  onClearSelection: () => void;
  isProcessing: boolean;
}

/**
 * Floating action bar for bulk operations:
 * - Shows when leads are selected
 * - Enrich, pause, archive actions
 * - Selection count
 */
```

**Design:**
```
+--------------------------------------------------+
| 5 leads selected  [Enrich All] [Pause] [Archive] |
+--------------------------------------------------+
```

---

## 7. API Integration

### Current Hooks

| Hook | File | Query Key | Endpoint | Status |
|------|------|-----------|----------|--------|
| `useLeads` | `hooks/use-leads.ts` | `["leads", clientId, params]` | `GET /api/v1/clients/{id}/leads` | IMPLEMENTED |
| `useLead` | `hooks/use-leads.ts` | `["lead", clientId, leadId]` | `GET /api/v1/clients/{id}/leads/{id}` | IMPLEMENTED |
| `useLeadActivities` | `hooks/use-leads.ts` | `["lead-activities", clientId, leadId]` | `GET /api/v1/clients/{id}/leads/{id}/activities` | IMPLEMENTED |
| `useCreateLead` | `hooks/use-leads.ts` | N/A (mutation) | `POST /api/v1/clients/{id}/leads` | IMPLEMENTED |
| `useCreateLeadsBulk` | `hooks/use-leads.ts` | N/A (mutation) | `POST /api/v1/clients/{id}/leads/bulk` | IMPLEMENTED |
| `useUpdateLead` | `hooks/use-leads.ts` | N/A (mutation) | `PUT /api/v1/clients/{id}/leads/{id}` | IMPLEMENTED |
| `useDeleteLead` | `hooks/use-leads.ts` | N/A (mutation) | `DELETE /api/v1/clients/{id}/leads/{id}` | IMPLEMENTED |
| `useEnrichLead` | `hooks/use-leads.ts` | N/A (mutation) | `POST /api/v1/clients/{id}/leads/{id}/enrich` | IMPLEMENTED |
| `useEnrichLeadsBulk` | `hooks/use-leads.ts` | N/A (mutation) | `POST /api/v1/clients/{id}/leads/bulk-enrich` | IMPLEMENTED |
| `useALSDistribution` | `hooks/use-reports.ts` | `["als-distribution", clientId]` | `GET /api/v1/reports/leads/distribution` | IMPLEMENTED |

### Deep Research Hooks (Existing in API)

| Hook | Query Key | Endpoint | Status |
|------|-----------|----------|--------|
| `useLeadResearch` | `["lead-research", clientId, leadId]` | `GET /api/v1/clients/{id}/leads/{id}/research` | API EXISTS, Hook NOT IMPLEMENTED |
| `useTriggerResearch` | N/A (mutation) | `POST /api/v1/clients/{id}/leads/{id}/research` | API EXISTS, Hook NOT IMPLEMENTED |
| `useScoreLead` | N/A (mutation) | `POST /api/v1/clients/{id}/leads/{id}/score` | API EXISTS, Hook NOT IMPLEMENTED |

### React Query Configuration

```typescript
const LEAD_STALE_TIMES = {
  list: 30 * 1000,           // 30 seconds
  detail: 30 * 1000,         // 30 seconds
  activities: 10 * 1000,     // 10 seconds (updates frequently)
  research: 5 * 60 * 1000,   // 5 minutes (expensive to fetch)
  distribution: 60 * 1000,   // 1 minute
};
```

---

## 8. API Gaps

### Missing Hooks (API Exists)

| Hook | Endpoint | Purpose | Priority |
|------|----------|---------|----------|
| `useLeadResearch` | `GET /api/v1/clients/{id}/leads/{id}/research` | Fetch deep research data | P2 |
| `useTriggerResearch` | `POST /api/v1/clients/{id}/leads/{id}/research` | Trigger SDK research | P2 |
| `useScoreLead` | `POST /api/v1/clients/{id}/leads/{id}/score` | Re-score a lead | P2 |

### Missing Endpoints

| Endpoint | Purpose | Priority | Backend File |
|----------|---------|----------|--------------|
| `GET /api/v1/clients/{id}/leads/export` | Export leads as CSV | P3 | `src/api/routes/leads.py` |
| `PATCH /api/v1/clients/{id}/leads/{id}/pause` | Pause lead outreach | P2 | `src/api/routes/leads.py` |
| `POST /api/v1/clients/{id}/leads/bulk-pause` | Bulk pause leads | P3 | `src/api/routes/leads.py` |
| `POST /api/v1/clients/{id}/leads/bulk-archive` | Bulk archive leads | P3 | `src/api/routes/leads.py` |

### Missing Fields

| Field | Purpose | Priority |
|-------|---------|----------|
| `last_touched_at` | When lead was last contacted | P2 |
| `next_action_at` | When next outreach is scheduled | P2 |
| `meetings_count` | Total meetings booked | P1 |
| `is_paused` | Lead outreach paused | P2 |

---

## 9. State Management

### Lead List State

```typescript
// Local state in LeadsPage
interface LeadListState {
  search: string;
  tierFilter: ALSTier | undefined;
  statusFilter: LeadStatus | undefined;
  page: number;
  pageSize: number;
  selectedIds: string[];        // For bulk actions
}
```

### Lead Detail State

```typescript
// Local state in LeadDetailPage
interface LeadDetailState {
  activeTab: "overview" | "activity" | "enrichment";
  expandedActivities: Set<string>;   // Which activities are expanded
}
```

### React Query Keys

```typescript
const queryKeys = {
  leads: {
    all: (clientId: string) => ["leads", clientId],
    list: (clientId: string, params?: object) => ["leads", clientId, params],
    detail: (clientId: string, leadId: string) => ["lead", clientId, leadId],
    activities: (clientId: string, leadId: string) => ["lead-activities", clientId, leadId],
    research: (clientId: string, leadId: string) => ["lead-research", clientId, leadId],
  },
  reports: {
    alsDistribution: (clientId: string) => ["als-distribution", clientId],
  },
};
```

### Optimistic Updates

```typescript
// Delete lead optimistically
const deleteMutation = useMutation({
  mutationFn: (leadId: string) => deleteLead(clientId!, leadId),
  onMutate: async (leadId) => {
    await queryClient.cancelQueries({ queryKey: ["leads", clientId] });
    const previous = queryClient.getQueryData(["leads", clientId]);

    queryClient.setQueryData(["leads", clientId], (old: any) => ({
      ...old,
      items: old.items.filter((l: Lead) => l.id !== leadId),
      total: old.total - 1,
    }));

    return { previous };
  },
  onError: (err, leadId, context) => {
    queryClient.setQueryData(["leads", clientId], context?.previous);
  },
  onSettled: () => {
    queryClient.invalidateQueries({ queryKey: ["leads", clientId] });
  },
});
```

---

## 10. v0 Integration

### Ready for Visual Design

| Section | Component | Ready? | Notes |
|---------|-----------|--------|-------|
| Lead List | LeadsPage | YES | Layout, table, pagination exist |
| Tier Cards | Inline | YES | 5 clickable tier filter cards |
| Lead Table | Inline | YES | Click to navigate |
| Lead Detail | LeadDetailPage | YES | Contact, company, ALS cards |
| ALS Breakdown | Inline | YES | 5-component progress bars |
| Activity Timeline | ActivityTimelineItem | YES | Expandable content |
| ALSScorecard | ALSScorecard.tsx | YES | Radar chart tooltip |
| Bulk Actions | - | NO | Needs LeadBulkActions component |
| Status Filter | - | NO | Needs dropdown implementation |
| Deep Research | - | NO | Needs research card component |

### CSS Variables (Tailwind)

```css
/* Tier colors */
.badge-hot { @apply bg-orange-500 text-white; }
.badge-warm { @apply bg-yellow-500 text-black; }
.badge-cool { @apply bg-blue-500 text-white; }
.badge-cold { @apply bg-gray-500 text-white; }
.badge-dead { @apply bg-gray-600 text-white; }

/* Activity timeline */
.timeline-email { @apply bg-blue-500; }
.timeline-sms { @apply bg-green-500; }
.timeline-linkedin { @apply bg-sky-500; }
.timeline-voice { @apply bg-purple-500; }
.timeline-mail { @apply bg-amber-500; }

/* Reply highlighting */
.reply-received {
  @apply bg-blue-50 dark:bg-blue-950 border-l-4 border-blue-500;
}
```

### Component States

All lead components should handle:
- **Loading** - Skeleton states
- **Error** - Error message + retry
- **Empty** - Helpful empty state
- **No Results** - Search/filter returned nothing

---

## 11. Wireframes

### Lead List Page

```
+------------------------------------------------------------------+
| AGENCY OS                                    [Client] [Settings] |
+------------------------------------------------------------------+
|        |                                                          |
| SIDEBAR|  LEADS                               [Export] [Import]   |
|        |                                                          |
| [Home] |  [ Search by name, email, company...           ] [Filter]|
| [Camp] |                                                          |
| [Leads]|  +----------+ +----------+ +----------+ +----------+ +--+|
| [Reply]|  |   HOT    | |   WARM   | |   COOL   | |   COLD   | |DE||
| [Reprt]|  |    23    | |    45    | |    78    | |    34    | |12||
| [Setng]|  +----------+ +----------+ +----------+ +----------+ +--+|
|        |      ^selected                                           |
|        |                                                          |
|        |  +------------------------------------------------------+|
|        |  | ALL LEADS                           567 total leads  ||
|        |  +------------------------------------------------------+|
|        |  | Lead            | Company       | Tier    | Status   ||
|        |  +------------------------------------------------------+|
|        |  | Sarah Chen      | TechCorp      | [Hot]   | In Seq   ||
|        |  | sarah@tech.com  | Technology    |         |          ||
|        |  +------------------------------------------------------+|
|        |  | Mike Johnson    | StartupXYZ    | [Warm]  | Scored   ||
|        |  | mike@startup.co | SaaS          |         |          ||
|        |  +------------------------------------------------------+|
|        |  | Lisa Park       | Acme Inc      | [Cool]  | Enriched ||
|        |  | lisa@acme.com   | Finance       |         |          ||
|        |  +------------------------------------------------------+|
|        |                                                          |
|        |  Page 1 of 29              [< Previous] [Next >]        |
|        |                                                          |
+------------------------------------------------------------------+
```

### Lead Detail Page

```
+------------------------------------------------------------------+
| AGENCY OS                                    [Client] [Settings] |
+------------------------------------------------------------------+
|        |                                                          |
| SIDEBAR|  < Back to Leads                                         |
|        |                                                          |
| [Home] |  Sarah Chen                    [Hot]  [In Sequence]      |
| [Camp] |  VP of Engineering at TechCorp                           |
| [Leads]|                                                          |
| [Reply]|                          [Send Email] [Re-score] [Pause] |
| [Reprt]|                                                          |
| [Setng]|  +----------------+ +----------------+ +----------------+|
|        |  | CONTACT        | | COMPANY        | | CAMPAIGN       ||
|        |  |                | |                | |                ||
|        |  | [E] sarah@...  | | [B] TechCorp   | | Tech Decision  ||
|        |  | [P] +1 555-123 | | [G] techcorp.io| | Makers         ||
|        |  | [L] /in/sarah  | | [M] Sydney, AU | | View Campaign >||
|        |  |                | | 150 employees  | |                ||
|        |  +----------------+ +----------------+ +----------------+|
|        |                                                          |
|        |  +------------------------------------------------------+|
|        |  | ALS SCORE BREAKDOWN                                  ||
|        |  |                                                      ||
|        |  |  [87]  Hot Lead                                      ||
|        |  |                                                      ||
|        |  | Data Quality  [========--] 18/20                     ||
|        |  | Authority     [==========-] 22/25                    ||
|        |  | Company Fit   [==========] 25/25                     ||
|        |  | Timing        [======----] 10/15                     ||
|        |  | Risk          [=========-] 12/15                     ||
|        |  +------------------------------------------------------+|
|        |                                                          |
|        |  +------------------------------------------------------+|
|        |  | ACTIVITY TIMELINE              Click to expand       ||
|        |  |                                                      ||
|        |  | O Email sent - "Quick question about scaling..."     ||
|        |  | |     2 hours ago                                    ||
|        |  | |     [Show content v]                               ||
|        |  | |                                                    ||
|        |  | O Reply received - Positive Intent                   ||
|        |  | |     1 hour ago                                     ||
|        |  | |     +----------------------------------------+     ||
|        |  | |     | "Hi, yes we'd be interested in        |     ||
|        |  | |     | learning more about your solution..." |     ||
|        |  | |     | [Show less ^] [Copy]                  |     ||
|        |  | |     +----------------------------------------+     ||
|        |  | |                                                    ||
|        |  | O Meeting booked - Discovery Call                    ||
|        |  |       30 minutes ago                                 ||
|        |  |       Tomorrow 2:00 PM                               ||
|        |  +------------------------------------------------------+|
|        |                                                          |
+------------------------------------------------------------------+
```

### Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| `lg` (1024px+) | Sidebar visible, 3-column detail grid |
| `md` (768px) | Sidebar collapsible, 2-column detail grid |
| `sm` (< 768px) | Sidebar hidden, single column, stacked cards |

---

## Related Documentation

| Doc | Purpose |
|-----|---------|
| `docs/architecture/flows/ENRICHMENT.md` | Lead enrichment pipeline |
| `docs/architecture/business/SCORING.md` | ALS calculation formula |
| `docs/architecture/frontend/DASHBOARD.md` | Dashboard architecture |
| `docs/architecture/frontend/CAMPAIGNS.md` | Campaign management |

---

For gaps and implementation status, see `../TODO.md`.
