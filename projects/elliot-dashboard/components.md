# Frontend Component Structure

Next.js App Router structure for the Elliot Dashboard.

## Directory Structure

```
apps/dashboard/
├── app/
│   ├── layout.tsx                    # Root layout with providers
│   ├── page.tsx                      # Redirect to /dashboard
│   │
│   ├── dashboard/
│   │   ├── layout.tsx                # Dashboard shell (sidebar, header)
│   │   ├── page.tsx                  # Dashboard home/overview
│   │   │
│   │   ├── elliot/
│   │   │   ├── layout.tsx            # Elliot section layout
│   │   │   ├── page.tsx              # Elliot overview
│   │   │   │
│   │   │   ├── memory/
│   │   │   │   ├── page.tsx          # Memory overview (timeline)
│   │   │   │   ├── daily/
│   │   │   │   │   ├── page.tsx      # Daily logs calendar
│   │   │   │   │   └── [date]/page.tsx  # Single day view
│   │   │   │   ├── weekly/
│   │   │   │   │   ├── page.tsx      # Weekly rollups list
│   │   │   │   │   └── [week]/page.tsx  # Single week view
│   │   │   │   └── patterns/
│   │   │   │       └── page.tsx      # Pattern visualization
│   │   │   │
│   │   │   ├── knowledge/
│   │   │   │   ├── page.tsx          # Knowledge overview
│   │   │   │   ├── rules/page.tsx    # Operating rules
│   │   │   │   ├── learnings/page.tsx # Lessons learned
│   │   │   │   └── decisions/
│   │   │   │       ├── page.tsx      # Decision log
│   │   │   │       └── [id]/page.tsx # Decision detail
│   │   │   │
│   │   │   ├── activity/
│   │   │   │   └── page.tsx          # Real-time activity feed
│   │   │   │
│   │   │   └── settings/
│   │   │       └── page.tsx          # Elliot configuration
│   │   │
│   │   └── health/
│   │       └── page.tsx              # Agency OS health grid
│   │
│   └── api/                          # API routes (proxy to FastAPI)
│       └── elliot/[...path]/route.ts
│
├── components/
│   ├── ui/                           # shadcn/ui components
│   │
│   ├── layout/
│   │   ├── DashboardShell.tsx        # Main dashboard wrapper
│   │   ├── Sidebar.tsx               # Navigation sidebar
│   │   ├── Header.tsx                # Top header with user menu
│   │   └── Breadcrumbs.tsx           # Breadcrumb navigation
│   │
│   ├── elliot/
│   │   ├── ElliotOverview.tsx        # Summary cards + recent activity
│   │   ├── ElliotStatus.tsx          # Online/offline indicator
│   │   │
│   │   ├── memory/
│   │   │   ├── MemoryTimeline.tsx    # Zoomable timeline component
│   │   │   ├── DailyLogCard.tsx      # Single day card
│   │   │   ├── DailyLogEditor.tsx    # Edit daily log
│   │   │   ├── DailyCalendar.tsx     # Calendar heatmap view
│   │   │   ├── WeeklyRollupCard.tsx  # Weekly summary card
│   │   │   └── PatternGraph.tsx      # Pattern network visualization
│   │   │
│   │   ├── knowledge/
│   │   │   ├── RulesTable.tsx        # Editable rules table
│   │   │   ├── RuleCard.tsx          # Single rule display
│   │   │   ├── LearningsList.tsx     # Searchable learnings list
│   │   │   ├── LearningCard.tsx      # Single learning card
│   │   │   ├── DecisionKanban.tsx    # Kanban by outcome status
│   │   │   ├── DecisionCard.tsx      # Single decision card
│   │   │   ├── DecisionDetail.tsx    # Full decision view
│   │   │   └── OutcomeForm.tsx       # Form to record outcome
│   │   │
│   │   ├── activity/
│   │   │   ├── ActivityFeed.tsx      # Real-time activity stream
│   │   │   ├── ActivityItem.tsx      # Single activity entry
│   │   │   ├── ActivityFilters.tsx   # Filter controls
│   │   │   ├── ActivityStats.tsx     # Stats/charts
│   │   │   └── TokenUsageChart.tsx   # Token usage over time
│   │   │
│   │   └── sync/
│   │       ├── SyncStatus.tsx        # Sync status indicator
│   │       ├── SyncPanel.tsx         # Full sync management
│   │       └── ConflictResolver.tsx  # Conflict resolution UI
│   │
│   └── health/
│       ├── HealthGrid.tsx            # Service status grid
│       ├── ServiceCard.tsx           # Single service status
│       ├── HealthHistory.tsx         # Status history chart
│       └── UptimeIndicator.tsx       # Uptime percentage
│
├── lib/
│   ├── api/
│   │   ├── client.ts                 # API client setup
│   │   ├── elliot.ts                 # Elliot API functions
│   │   └── health.ts                 # Health API functions
│   │
│   ├── supabase/
│   │   ├── client.ts                 # Supabase client
│   │   ├── realtime.ts               # Realtime subscriptions
│   │   └── types.ts                  # Generated DB types
│   │
│   ├── hooks/
│   │   ├── useElliotActivity.ts      # Activity feed hook
│   │   ├── useElliotMemory.ts        # Memory data hook
│   │   ├── useElliotDecisions.ts     # Decisions hook
│   │   ├── useRealtimeActivity.ts    # Realtime subscription
│   │   ├── useServiceHealth.ts       # Health status hook
│   │   └── useSyncStatus.ts          # Sync status hook
│   │
│   └── utils/
│       ├── markdown.ts               # Markdown parsing
│       ├── dates.ts                  # Date utilities
│       └── formatters.ts             # Display formatters
│
└── types/
    ├── elliot.ts                     # Elliot-specific types
    └── api.ts                        # API response types
```

---

## Key Component Specifications

### ElliotOverview.tsx

Main dashboard overview for Elliot section.

```tsx
interface ElliotOverviewProps {
  // Data fetched server-side
  recentActivity: Activity[];
  pendingDecisions: Decision[];
  todayLog: DailyLog | null;
  syncStatus: SyncStatus;
}

// Features:
// - Status indicator (last active, current session)
// - Today's memory summary (if exists)
// - Pending decisions count + list
// - Recent activity preview (last 5)
// - Quick stats: decisions this week, learnings this month
// - Sync status indicator
```

### MemoryTimeline.tsx

Zoomable timeline showing memory across time scales.

```tsx
interface MemoryTimelineProps {
  initialScale: 'day' | 'week' | 'month' | 'year';
  onDateSelect: (date: Date) => void;
}

// Features:
// - Zoom levels: day (hourly) → week → month → year
// - Click to drill down
// - Visual density indicators (activity level)
// - Patterns highlighted as overlays
// - Weekly rollup markers
```

### DailyCalendar.tsx

GitHub-style contribution calendar for daily logs.

```tsx
interface DailyCalendarProps {
  year: number;
  dailyLogs: Map<string, DailyLogSummary>;
  onDayClick: (date: string) => void;
}

// Features:
// - 12-month calendar grid
// - Color intensity = activity level
// - Hover tooltip with day summary
// - Click to view full day
// - Legend showing activity levels
```

### DecisionKanban.tsx

Kanban board for tracking decision outcomes.

```tsx
interface DecisionKanbanProps {
  decisions: Decision[];
  onDecisionClick: (id: string) => void;
  onStatusChange: (id: string, status: OutcomeStatus) => void;
}

// Columns:
// - Pending (awaiting outcome)
// - Success (outcome achieved)
// - Partial (partial success)
// - Failure (didn't work)
//
// Features:
// - Drag-drop between columns
// - Quick outcome entry
// - Days-since-decision indicator
// - Filter by category/importance
```

### ActivityFeed.tsx

Real-time activity stream with live updates.

```tsx
interface ActivityFeedProps {
  initialActivities: Activity[];
  filters?: ActivityFilters;
}

// Features:
// - Real-time updates via Supabase subscription
// - Activity type icons
// - Relative timestamps ("2 min ago")
// - Expandable details
// - Filter by type, channel, session
// - Pause/resume live updates
// - Virtual scrolling for performance
```

### PatternGraph.tsx

Network visualization of patterns and their connections.

```tsx
interface PatternGraphProps {
  patterns: Pattern[];
  learnings: Learning[];
  decisions: Decision[];
}

// Features:
// - Force-directed graph layout
// - Nodes: patterns (large), learnings (medium), decisions (small)
// - Edges: pattern → learning, decision → learning
// - Click node for details panel
// - Filter by category
// - Zoom/pan controls
// - Uses D3.js or react-force-graph
```

### HealthGrid.tsx

Grid display of all Agency OS service health.

```tsx
interface HealthGridProps {
  services: ServiceHealth[];
  onServiceClick: (name: string) => void;
}

// Layout:
// ┌─────────┐ ┌─────────┐ ┌─────────┐
// │ Supabase│ │ Railway │ │ Vercel  │
// │ ✓ 45ms  │ │ ✓ 120ms │ │ ✓ 80ms  │
// └─────────┘ └─────────┘ └─────────┘
// ┌─────────┐ ┌─────────┐ ┌─────────┐
// │ Prefect │ │ Redis   │ │ Clawdbot│
// │ ✓ 200ms │ │ ✓ 15ms  │ │ ✓ Online│
// └─────────┘ └─────────┘ └─────────┘
//
// Features:
// - Color-coded status (green/yellow/red)
// - Response time display
// - Click for history chart
// - Auto-refresh every 60s
// - Overall status banner at top
```

### SyncPanel.tsx

Full sync management interface.

```tsx
interface SyncPanelProps {
  syncState: SyncState[];
  onTriggerSync: (direction: SyncDirection) => void;
  onResolveConflict: (id: string, resolution: Resolution) => void;
}

// Features:
// - File list with sync status
// - Last sync timestamp per file
// - Manual sync trigger buttons
// - Conflict list with resolution UI
// - Diff view for conflicts
// - Sync history/log
```

---

## Realtime Subscription Hook

```typescript
// lib/hooks/useRealtimeActivity.ts

import { useEffect, useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import type { Activity } from '@/types/elliot';

export function useRealtimeActivity(limit = 50) {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const supabase = createClient();

  useEffect(() => {
    // Initial fetch
    const fetchInitial = async () => {
      const { data } = await supabase
        .from('elliot_activity')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(limit);
      
      if (data) setActivities(data);
    };
    
    fetchInitial();

    // Subscribe to new activities
    const channel = supabase
      .channel('elliot-activity-realtime')
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'elliot_activity',
        },
        (payload) => {
          setActivities((prev) => [payload.new as Activity, ...prev.slice(0, limit - 1)]);
        }
      )
      .subscribe((status) => {
        setIsConnected(status === 'SUBSCRIBED');
      });

    return () => {
      supabase.removeChannel(channel);
    };
  }, [limit]);

  return { activities, isConnected };
}
```

---

## API Client

```typescript
// lib/api/elliot.ts

import { createClient } from '@/lib/supabase/client';
import type { 
  DailyLog, 
  Decision, 
  Learning, 
  Pattern,
  Activity 
} from '@/types/elliot';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://api.agency-os.com';

async function fetchWithAuth(path: string, options: RequestInit = {}) {
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  
  return fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${session?.access_token}`,
      ...options.headers,
    },
  });
}

export const elliotApi = {
  // Memory
  async getDailyLogs(params?: { startDate?: string; endDate?: string; limit?: number }) {
    const query = new URLSearchParams(params as Record<string, string>);
    const res = await fetchWithAuth(`/api/elliot/memory/daily?${query}`);
    return res.json();
  },
  
  async getDailyLog(date: string): Promise<DailyLog | null> {
    const res = await fetchWithAuth(`/api/elliot/memory/daily/${date}`);
    if (res.status === 404) return null;
    return res.json();
  },
  
  async updateDailyLog(date: string, data: Partial<DailyLog>) {
    const res = await fetchWithAuth('/api/elliot/memory/daily', {
      method: 'POST',
      body: JSON.stringify({ log_date: date, ...data }),
    });
    return res.json();
  },

  // Decisions
  async getDecisions(params?: { status?: string; limit?: number }) {
    const query = new URLSearchParams(params as Record<string, string>);
    const res = await fetchWithAuth(`/api/elliot/knowledge/decisions?${query}`);
    return res.json();
  },
  
  async updateDecisionOutcome(id: string, outcome: {
    actual_outcome: string;
    outcome_status: 'success' | 'partial' | 'failure';
    learning_extracted?: string;
  }) {
    const res = await fetchWithAuth(`/api/elliot/knowledge/decisions/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(outcome),
    });
    return res.json();
  },

  // Activity
  async getActivity(params?: { since?: string; type?: string; limit?: number }) {
    const query = new URLSearchParams(params as Record<string, string>);
    const res = await fetchWithAuth(`/api/elliot/activity?${query}`);
    return res.json();
  },

  // Sync
  async triggerSync(direction: 'file_to_db' | 'db_to_file' | 'bidirectional') {
    const res = await fetchWithAuth('/api/elliot/sync/trigger', {
      method: 'POST',
      body: JSON.stringify({ direction }),
    });
    return res.json();
  },
  
  async getSyncStatus() {
    const res = await fetchWithAuth('/api/elliot/sync/status');
    return res.json();
  },
};
```

---

## Styling Notes

- Use **shadcn/ui** for base components (consistent with Agency OS)
- **Tailwind CSS** for styling
- **Dark mode first** (matches developer preference)
- Charts: **Recharts** or **Tremor**
- Graph visualization: **react-force-graph** or **D3.js**
- Date handling: **date-fns**
- Markdown rendering: **react-markdown** with syntax highlighting

---

## Key Pages Implementation

### `/dashboard/elliot/page.tsx`

```tsx
import { Suspense } from 'react';
import { ElliotOverview } from '@/components/elliot/ElliotOverview';
import { ActivityFeed } from '@/components/elliot/activity/ActivityFeed';
import { PendingDecisions } from '@/components/elliot/knowledge/PendingDecisions';
import { SyncStatus } from '@/components/elliot/sync/SyncStatus';
import { getElliotOverview } from '@/lib/api/elliot.server';

export default async function ElliotDashboardPage() {
  const overview = await getElliotOverview();
  
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Elliot Dashboard</h1>
        <SyncStatus status={overview.syncStatus} />
      </div>
      
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <StatCard 
          title="Decisions This Week" 
          value={overview.stats.decisionsThisWeek} 
        />
        <StatCard 
          title="Pending Outcomes" 
          value={overview.stats.pendingDecisions} 
          variant="warning"
        />
        <StatCard 
          title="Learnings This Month" 
          value={overview.stats.learningsThisMonth} 
        />
      </div>
      
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <Suspense fallback={<ActivitySkeleton />}>
              <ActivityFeed initialActivities={overview.recentActivity} />
            </Suspense>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>Pending Decisions</CardTitle>
          </CardHeader>
          <CardContent>
            <PendingDecisions decisions={overview.pendingDecisions} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
```

### `/dashboard/elliot/memory/daily/page.tsx`

```tsx
import { DailyCalendar } from '@/components/elliot/memory/DailyCalendar';
import { getDailyLogSummaries } from '@/lib/api/elliot.server';

export default async function DailyMemoryPage() {
  const currentYear = new Date().getFullYear();
  const summaries = await getDailyLogSummaries(currentYear);
  
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Daily Memory</h1>
      
      <DailyCalendar 
        year={currentYear}
        dailyLogs={summaries}
      />
      
      <RecentDailyLogs limit={10} />
    </div>
  );
}
```

---

## Mobile Responsiveness

All components should be mobile-responsive:

- **Sidebar**: Collapsible drawer on mobile
- **Cards**: Stack vertically on small screens
- **Tables**: Horizontal scroll or card-based view
- **Charts**: Simplified on mobile
- **Kanban**: Single column with horizontal scroll for columns
