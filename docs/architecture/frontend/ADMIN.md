# Admin Panel — Agency OS

**Purpose:** Platform administration dashboard for system monitoring, client management, and operations.
**Status:** IMPLEMENTED
**Last Updated:** 2026-01-22

---

## Overview

The Admin Panel provides platform administrators with tools to monitor system health, manage clients, track costs, and handle compliance. It consists of a FastAPI backend (`admin.py`) with 23+ endpoints and a Next.js frontend with 21 pages.

**Key Capabilities:**
- Real-time system health monitoring
- Client management with health scoring
- AI spend tracking (live from Redis)
- Global activity feed
- Suppression list management
- Lead pool administration
- Revenue metrics

**Access Control:** Requires `is_platform_admin = true` on the user record.

---

## Code Locations

### Backend

| Component | File | Purpose |
|-----------|------|---------|
| Admin Routes | `src/api/routes/admin.py` | 23+ endpoints for admin operations |
| Auth Dependency | `src/api/dependencies.py` | `get_admin_context`, `require_platform_admin` |
| Current User Model | `src/api/dependencies.py` | `CurrentUser`, `AdminContext` classes |

### Frontend

| Component | File | Purpose |
|-----------|------|---------|
| Layout | `frontend/app/admin/layout.tsx` | Server-side auth check, sidebar + header |
| Command Center | `frontend/app/admin/page.tsx` | Main dashboard with KPIs |
| Sidebar | `frontend/components/admin/AdminSidebar.tsx` | Navigation (14 items) |
| Header | `frontend/components/admin/AdminHeader.tsx` | Top bar with alerts |
| Admin Hooks | `frontend/hooks/use-admin.ts` | React Query hooks for API |
| Admin API | `frontend/lib/api/admin.ts` | API client functions |

### Frontend Pages (21 total)

| Page | File | Purpose |
|------|------|---------|
| Command Center | `app/admin/page.tsx` | KPIs, system status, alerts, activity |
| Revenue | `app/admin/revenue/page.tsx` | MRR, ARR, tier distribution |
| Clients | `app/admin/clients/page.tsx` | Client directory with health scores |
| Client Detail | `app/admin/clients/[id]/page.tsx` | Single client deep dive |
| Campaigns | `app/admin/campaigns/page.tsx` | All campaigns across clients |
| Leads | `app/admin/leads/page.tsx` | All leads across clients |
| Activity | `app/admin/activity/page.tsx` | Global activity feed |
| Replies | `app/admin/replies/page.tsx` | Reply inbox (admin view) |
| AI Spend | `app/admin/costs/ai/page.tsx` | AI cost breakdown by agent/client |
| Channel Costs | `app/admin/costs/channels/page.tsx` | SMS, Voice, Email costs |
| System Status | `app/admin/system/page.tsx` | Service health dashboard |
| Errors | `app/admin/system/errors/page.tsx` | Error tracking (Sentry) |
| Queues | `app/admin/system/queues/page.tsx` | Prefect queue status |
| Rate Limits | `app/admin/system/rate-limits/page.tsx` | API rate limit status |
| Compliance | `app/admin/compliance/page.tsx` | Compliance overview |
| Suppression | `app/admin/compliance/suppression/page.tsx` | Global suppression list |
| Bounces | `app/admin/compliance/bounces/page.tsx` | Bounce management |
| Settings | `app/admin/settings/page.tsx` | Platform settings |
| Users | `app/admin/settings/users/page.tsx` | Platform admin users |

---

## Data Flow

### Authentication Flow

```
User Request
    ↓
[AdminLayout] Server Component
    ↓
isPlatformAdmin() check
    ↓
  No → Redirect to /dashboard
    ↓
  Yes → Render admin UI
    ↓
[API Request with JWT]
    ↓
get_admin_context() dependency
    ↓
Verify is_platform_admin = true
    ↓
Return AdminContext
```

### Command Center Data Flow

```
AdminCommandCenter
    ↓
useAdminStats() → GET /api/v1/admin/stats
useSystemHealth() → GET /api/v1/admin/system/status
useAlerts() → GET /api/v1/admin/alerts
useGlobalActivity() → GET /api/v1/admin/activity
    ↓
[React Query Cache]
    ↓
Render KPIs, Status, Alerts, Activity
```

### AI Spend Data Flow

```
GET /api/v1/admin/costs/ai
    ↓
[ai_spend_tracker.get_spend()] ← Redis
    ↓
Calculate: today_spend, limit, percentage
    ↓
Estimate breakdown by agent (content 42%, reply 33%, cmo 25%)
    ↓
Query top clients for distribution
    ↓
Return AISpendResponse
```

---

## API Endpoints

### Command Center

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/admin/stats` | KPI statistics (MRR, clients, leads, AI spend) |
| GET | `/admin/activity` | Global activity feed |
| GET | `/admin/alerts` | System alerts (inactive clients, past due) |

### System Status

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/admin/system/status` | Service health (DB, Redis, Prefect, API) |

### Client Management

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/admin/clients` | Paginated client list with health scores |
| GET | `/admin/clients/{id}` | Client detail with campaigns, team, activity |

### AI Spend

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/admin/costs/ai` | AI spend breakdown (real-time from Redis) |

### Suppression List

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/admin/suppression` | Paginated suppression list |
| POST | `/admin/suppression` | Add email to suppression |
| DELETE | `/admin/suppression/{id}` | Remove from suppression |

### Revenue

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/admin/revenue` | Revenue metrics (MRR, ARR, by tier) |

### Global Data

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/admin/campaigns` | All campaigns across clients |
| GET | `/admin/leads` | All leads across clients |

### Lead Pool Management (Phase 24A)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/admin/pool/stats` | Pool statistics |
| GET | `/admin/pool/leads` | Paginated pool leads |
| GET | `/admin/pool/leads/{id}` | Pool lead detail with assignments |
| GET | `/admin/pool/assignments` | Paginated assignments |
| POST | `/admin/pool/assign` | Manual lead assignment |
| POST | `/admin/pool/release` | Release leads back to pool |
| GET | `/admin/pool/utilization` | Utilization by client |

---

## Key Rules

1. **Platform Admin Only** — All admin endpoints require `is_platform_admin = true`. No client-level access.

2. **Soft Delete Compliance** — All queries include `deleted_at IS NULL` checks (Rule 14).

3. **Session as Argument** — Database session passed via FastAPI dependency (Rule 11).

4. **Real-Time AI Spend** — AI spend comes from Redis (`ai_spend_tracker`), not database.

5. **Health Score Calculation** — Client health = base(50) + campaigns(+20) + recent_activity(+30) + subscription_status(+15/-30).

6. **Pagination Standard** — All list endpoints support `page`, `page_size`, filters, and search.

7. **Server-Side Auth Check** — Frontend uses `isPlatformAdmin()` in layout before rendering.

---

## Configuration

| Setting | Location | Default | Notes |
|---------|----------|---------|-------|
| AI Spend Limit | `settings.anthropic_daily_spend_limit` | $100 | Daily limit in AUD |
| Tier Pricing | `admin.py` tier_pricing dict | 199/499/999 | MRR by tier |
| Activity Limit | Query param | 20 | Max items in feed |
| Page Size | Query param | 20-50 | Varies by endpoint |
| Refresh Intervals | `use-admin.ts` | 30-60s | React Query stale time |

---

## Frontend Patterns

### React Query Hooks

```typescript
// hooks/use-admin.ts
export function useAdminStats() {
  return useQuery({
    queryKey: ["admin-stats"],
    queryFn: getAdminStats,
    staleTime: 30 * 1000,      // 30 seconds
    refetchInterval: 60 * 1000, // Auto-refresh 1 minute
  });
}
```

### Server-Side Auth Guard

```typescript
// app/admin/layout.tsx
export default async function AdminLayout({ children }) {
  const isAdmin = await isPlatformAdmin();
  if (!isAdmin) {
    redirect("/dashboard");
  }
  return <AdminUI>{children}</AdminUI>;
}
```

### Navigation Items

14 items in `AdminSidebar.tsx`:
1. Command Center
2. Revenue
3. Clients
4. Campaigns
5. Leads
6. Activity
7. Replies
8. AI Spend
9. Channel Costs
10. System Status
11. Suppression List
12. Bounces
13. Settings
14. Users

---

## Response Models

### KPIStats

```python
class KPIStats(BaseModel):
    mrr: Decimal                    # Monthly Recurring Revenue
    mrr_change: float               # MoM change %
    active_clients: int             # Count of active clients
    new_clients_this_month: int     # New this month
    leads_today: int                # Leads created today
    leads_change: float             # vs yesterday %
    ai_spend_today: Decimal         # Today's AI spend
    ai_spend_limit: Decimal         # Daily limit
```

### SystemStatusResponse

```python
class SystemStatusResponse(BaseModel):
    overall_status: str             # healthy | degraded | down
    services: list[ServiceStatus]   # Individual service status
    timestamp: datetime
```

### ClientListItem

```python
class ClientListItem(BaseModel):
    id: UUID
    name: str
    tier: str
    subscription_status: str
    mrr: Decimal
    campaigns_count: int
    leads_count: int
    last_activity: Optional[datetime]
    health_score: int               # 0-100 calculated
```

---

## Cross-References

- [`../foundation/API_LAYER.md`](../foundation/API_LAYER.md) — API structure, auth dependencies
- [`../foundation/DATABASE.md`](../foundation/DATABASE.md) — User, Client, Membership models
- [`../business/TIERS_AND_BILLING.md`](../business/TIERS_AND_BILLING.md) — Tier pricing, credits
- [`../flows/ENRICHMENT.md`](../flows/ENRICHMENT.md) — Lead pool architecture
- [`TECHNICAL.md`](TECHNICAL.md) — Frontend tech stack and patterns

---

For gaps and implementation status, see [`../TODO.md`](../TODO.md).
