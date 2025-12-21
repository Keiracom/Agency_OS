# SKILL.md — Admin Dashboard

**Skill:** Admin Dashboard for Agency OS  
**Author:** CTO (Claude)  
**Version:** 1.0  
**Created:** December 21, 2025

---

## Purpose

Build a comprehensive admin dashboard for the platform owner (CEO) to monitor all aspects of Agency OS: revenue, clients, operations, costs, system health, and compliance.

This dashboard is **separate from the User Dashboard** (built in Phase 8) and provides platform-wide visibility that individual clients should never see.

---

## Architecture Decision

**Location:** `frontend/app/admin/`  
**Access:** Protected route, requires `is_platform_admin: true` on user record  
**URL Pattern:** `https://app.agency-os.com/admin/*`

The admin dashboard lives in the same Next.js app but under a protected `/admin` route prefix.

---

## Database Requirement

Add `is_platform_admin` boolean to users table:

```sql
-- Migration: 010_platform_admin.sql
ALTER TABLE users ADD COLUMN is_platform_admin BOOLEAN DEFAULT FALSE;

-- Set yourself as admin (replace with your user ID)
UPDATE users SET is_platform_admin = TRUE WHERE email = 'dave@yourdomain.com';
```

---

## File Structure

```
frontend/app/admin/
├── layout.tsx                    # Admin layout with sidebar
├── page.tsx                      # Command Center (home)
├── revenue/
│   └── page.tsx                  # Revenue dashboard
├── clients/
│   ├── page.tsx                  # Client directory
│   └── [id]/
│       └── page.tsx              # Client detail + impersonate
├── campaigns/
│   └── page.tsx                  # All campaigns (global)
├── leads/
│   └── page.tsx                  # All leads (global)
├── activity/
│   └── page.tsx                  # Global activity log
├── replies/
│   └── page.tsx                  # Global reply inbox
├── costs/
│   ├── page.tsx                  # Cost overview
│   ├── ai/
│   │   └── page.tsx              # AI spend breakdown
│   └── channels/
│       └── page.tsx              # Channel costs
├── system/
│   ├── page.tsx                  # System status
│   ├── errors/
│   │   └── page.tsx              # Error log (Sentry)
│   ├── queues/
│   │   └── page.tsx              # Prefect monitor
│   └── rate-limits/
│       └── page.tsx              # Rate limit status
├── compliance/
│   ├── page.tsx                  # Compliance overview
│   ├── suppression/
│   │   └── page.tsx              # Global suppression list
│   └── bounces/
│       └── page.tsx              # Bounce/spam tracker
└── settings/
    ├── page.tsx                  # Platform settings
    └── users/
        └── page.tsx              # User management

frontend/components/admin/
├── AdminSidebar.tsx              # Admin navigation
├── AdminHeader.tsx               # Header with alerts
├── KPICard.tsx                   # Metric card component
├── AlertBanner.tsx               # System alerts
├── LiveActivityFeed.tsx          # Real-time activity
├── ClientHealthIndicator.tsx     # Client health score
├── CostChart.tsx                 # Cost visualization
├── SystemStatusIndicator.tsx     # Service status dots
└── DataTable.tsx                 # Reusable data table
```

---

## Page Specifications

### 1. Command Center (`/admin`)

The war room. First thing you see when you log in.

**Layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│  AGENCY OS COMMAND                      Last updated: 30s ago   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐       │
│  │ MRR       │ │ Clients   │ │ Leads     │ │ AI Spend  │       │
│  │ $47,500   │ │ 19 active │ │ 1,247     │ │ $89/$500  │       │
│  │ ▲ 12%     │ │ ▲ 2 new   │ │ today     │ │ 18%       │       │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘       │
│                                                                 │
│  SYSTEM STATUS                                                  │
│  ● API  ● Prefect  ● Database  ● Redis  ● Webhooks             │
│                                                                 │
│  ALERTS (3)                                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 🔴 Client "GrowthLab" - 3 failed enrichments            │   │
│  │ 🟡 Apollo API rate limit 80% consumed                   │   │
│  │ 🟡 Client "ScaleUp" - no activity 48hrs                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  LIVE ACTIVITY                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 14:32 LeadGen Pro    Email sent to john@acme.com        │   │
│  │ 14:31 GrowthLab      Lead enriched (ALS: 78)            │   │
│  │ 14:31 ScaleUp Co     Reply received (interested)        │   │
│  │ 14:30 LeadGen Pro    LinkedIn connection sent           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Data Sources:**
- MRR: `SELECT SUM(mrr) FROM clients WHERE subscription_status = 'active'`
- Clients: `SELECT COUNT(*) FROM clients WHERE deleted_at IS NULL`
- Leads today: `SELECT COUNT(*) FROM leads WHERE created_at > NOW() - INTERVAL '24 hours'`
- AI Spend: Redis key `ai_spend:daily:{date}`
- System status: `/api/v1/health/ready` endpoint
- Activity: `SELECT * FROM activities ORDER BY created_at DESC LIMIT 20`

**Alerts Logic:**
- 🔴 Critical: Failed flows, payment failures, system down
- 🟡 Warning: Rate limits >80%, no activity 48hrs, high bounce rate
- 🟢 Info: New client signup, milestone reached

---

### 2. Revenue Dashboard (`/admin/revenue`)

**Metrics:**
| Metric | Calculation | Display |
|--------|-------------|---------|
| MRR | Sum of active subscriptions | $XX,XXX |
| ARR | MRR × 12 | $XXX,XXX |
| New MRR | This month's new subscriptions | $X,XXX |
| Churned MRR | This month's cancellations | $X,XXX |
| Net MRR Growth | New - Churned | $X,XXX |
| Churn Rate | Churned / Previous MRR | X.X% |
| ARPU | MRR / Active Clients | $X,XXX |

**Charts:**
1. MRR over time (line chart, 12 months)
2. Revenue by tier (pie chart: Ignition/Velocity/Dominance)
3. New vs Churned waterfall (bar chart)
4. Client count over time (line chart)

**Tables:**
1. Recent transactions (Stripe webhooks)
2. Upcoming renewals (next 30 days)
3. At-risk clients (past_due status)

---

### 3. Client Directory (`/admin/clients`)

**List View Columns:**
| Column | Source | Sortable |
|--------|--------|----------|
| Client Name | `clients.name` | Yes |
| Tier | `clients.tier` | Yes |
| MRR | Calculated from tier | Yes |
| Status | `clients.subscription_status` | Yes |
| Campaigns | Count of active campaigns | Yes |
| Leads | Count of leads | Yes |
| Last Activity | Latest activity timestamp | Yes |
| Health Score | Calculated (see below) | Yes |

**Health Score Calculation (0-100):**
```
- Active campaigns: +20 (if any active)
- Activity last 24h: +30
- Activity last 48h: +20 (if not 24h)
- No activity 48h+: -30
- Bounce rate <2%: +15
- Bounce rate >5%: -20
- Payment current: +15
- Payment past_due: -30
```

**Filters:**
- Status: All / Active / Trialing / Past Due / Paused / Cancelled
- Tier: All / Ignition / Velocity / Dominance
- Health: All / Healthy (70+) / At Risk (40-69) / Critical (<40)
- Search: By name

**Actions:**
- View details
- Impersonate (see as client)
- Pause subscription
- Cancel subscription

---

### 4. Client Detail (`/admin/clients/[id]`)

**Sections:**

**Header:**
- Client name, tier badge, status badge
- Health score indicator
- Quick actions: Impersonate, Pause, Cancel

**Overview Tab:**
- Subscription details (tier, status, renewal date)
- Credit balance and usage
- Team members list
- Created date, last activity

**Campaigns Tab:**
- All campaigns for this client
- Status, lead count, sent count, reply count

**Leads Tab:**
- All leads for this client
- ALS distribution chart
- Filter by tier, status

**Activity Tab:**
- Full activity log for this client
- Filter by channel, action

**Billing Tab:**
- Payment history
- Invoices
- Credit adjustments

**Impersonate Button:**
- Opens new tab as this client
- Shows banner "Viewing as [Client Name]"
- Read-only mode (no modifications)

---

### 5. AI Spend Dashboard (`/admin/costs/ai`)

**Layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│  AI SPEND - DECEMBER 2025                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TODAY                           MONTH TO DATE                  │
│  ┌─────────────────────┐        ┌─────────────────────┐        │
│  │ $89.42 / $500       │        │ $1,247.83           │        │
│  │ ████████░░░░ 18%    │        │ Projected: $1,890   │        │
│  └─────────────────────┘        └─────────────────────┘        │
│                                                                 │
│  BY AGENT                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Content Agent  ████████████████████  $523 (42%)         │   │
│  │ Reply Agent    █████████████        $412 (33%)          │   │
│  │ CMO Agent      ██████████           $312 (25%)          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  BY CLIENT (Top 10)                                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ LeadGen Pro     $287    GrowthLab       $245            │   │
│  │ ScaleUp Co      $198    Marketing Plus  $156            │   │
│  │ ...                                                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  DAILY TREND (30 days)                                          │
│  [Line chart showing daily AI spend]                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Data Sources:**
- Daily spend: Redis `ai_spend:daily:{date}`
- By agent: Redis `ai_spend:agent:{agent}:{date}`
- By client: Redis `ai_spend:client:{client_id}:{date}`

**Alerts:**
- 🔴 Daily limit reached (circuit breaker active)
- 🟡 >80% of daily limit consumed
- 🟡 Unusual spike (>2x average)

---

### 6. System Status (`/admin/system`)

**Services Grid:**
```
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ ● API       │ │ ● Database  │ │ ● Redis     │ │ ● Prefect   │
│ Healthy     │ │ Healthy     │ │ Healthy     │ │ Healthy     │
│ 45ms avg    │ │ 12ms avg    │ │ 3ms avg     │ │ 2 running   │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

**Prefect Flows Table:**
| Flow | Last Run | Status | Duration | Next Run |
|------|----------|--------|----------|----------|
| daily-enrichment | 2:00 AM | ✅ Success | 12m 34s | Tomorrow 2:00 AM |
| hourly-outreach | 2:00 PM | ✅ Success | 3m 12s | 3:00 PM |
| reply-recovery | 12:00 PM | ✅ Success | 1m 45s | 6:00 PM |

**Recent Errors (from Sentry):**
| Time | Error | Service | Count |
|------|-------|---------|-------|
| 14:23 | ConnectionTimeout | apollo.py | 3 |
| 14:01 | RateLimitExceeded | heyreach.py | 1 |

**Database Stats:**
- Connection pool: 5/10 active
- Query latency: p50 12ms, p95 45ms, p99 120ms
- Table sizes (leads, activities, etc.)

---

### 7. Global Suppression (`/admin/compliance/suppression`)

**Features:**
- View all suppressed emails
- Add single email
- Bulk import (CSV upload)
- Remove from suppression
- Search by email/domain
- Filter by reason (unsubscribe, bounce, spam, manual)

**Table Columns:**
| Email | Reason | Added By | Added Date | Actions |
|-------|--------|----------|------------|---------|
| spam@bad.com | spam_complaint | system | Dec 20 | Remove |
| john@example.com | unsubscribe | user request | Dec 19 | Remove |

**Bulk Import:**
- Accept CSV with `email` column
- Validate email format
- Show preview before import
- Report: X added, X duplicates, X invalid

---

### 8. Platform Settings (`/admin/settings`)

**Sections:**

**Limits:**
- Daily AI spend limit (AUD)
- Default rate limits per channel
- Clay fallback percentage (default 15%)

**Feature Flags:**
- Enable/disable voice channel
- Enable/disable direct mail
- Maintenance mode toggle

**Notifications:**
- Alert email address
- Slack webhook URL
- Alert thresholds

**Danger Zone:**
- Pause all campaigns (emergency)
- Reset rate limits
- Clear Redis cache

---

## API Endpoints Required

New admin-only endpoints to add:

```
GET  /api/v1/admin/stats                    # Command center stats
GET  /api/v1/admin/revenue                  # Revenue metrics
GET  /api/v1/admin/clients                  # All clients with health
GET  /api/v1/admin/clients/{id}             # Client detail
POST /api/v1/admin/clients/{id}/impersonate # Get impersonation token
GET  /api/v1/admin/campaigns                # All campaigns
GET  /api/v1/admin/leads                    # All leads
GET  /api/v1/admin/activity                 # Global activity feed
GET  /api/v1/admin/replies                  # Global reply inbox
GET  /api/v1/admin/costs/ai                 # AI spend breakdown
GET  /api/v1/admin/costs/channels           # Channel costs
GET  /api/v1/admin/system/status            # System health
GET  /api/v1/admin/system/errors            # Recent errors
GET  /api/v1/admin/system/queues            # Prefect status
GET  /api/v1/admin/system/rate-limits       # Rate limit status
GET  /api/v1/admin/suppression              # Suppression list
POST /api/v1/admin/suppression              # Add to suppression
POST /api/v1/admin/suppression/bulk         # Bulk import
DELETE /api/v1/admin/suppression/{id}       # Remove from suppression
GET  /api/v1/admin/settings                 # Platform settings
PUT  /api/v1/admin/settings                 # Update settings
GET  /api/v1/admin/users                    # All users
```

**Authorization:**
All endpoints require `is_platform_admin: true` on the authenticated user.

---

## Component Specifications

### KPICard

```tsx
interface KPICardProps {
  title: string;
  value: string | number;
  change?: number;        // Percentage change
  changeLabel?: string;   // "MoM", "WoW", etc.
  icon?: React.ReactNode;
  loading?: boolean;
}
```

### AlertBanner

```tsx
interface Alert {
  id: string;
  severity: 'critical' | 'warning' | 'info';
  message: string;
  timestamp: Date;
  link?: string;
  dismissible?: boolean;
}

interface AlertBannerProps {
  alerts: Alert[];
  onDismiss?: (id: string) => void;
}
```

### SystemStatusIndicator

```tsx
interface ServiceStatus {
  name: string;
  status: 'healthy' | 'degraded' | 'down';
  latency?: number;
  message?: string;
}

interface SystemStatusIndicatorProps {
  services: ServiceStatus[];
}
```

### LiveActivityFeed

```tsx
interface Activity {
  id: string;
  client_name: string;
  action: string;
  details: string;
  timestamp: Date;
  channel?: 'email' | 'sms' | 'linkedin' | 'voice' | 'mail';
}

interface LiveActivityFeedProps {
  activities: Activity[];
  maxItems?: number;
  pollingInterval?: number; // ms
}
```

---

## Data Refresh Strategy

| Data | Refresh Method | Interval |
|------|----------------|----------|
| KPI stats | Polling | 30 seconds |
| System status | Polling | 10 seconds |
| Activity feed | WebSocket or Polling | 5 seconds |
| Alerts | Polling | 30 seconds |
| Tables | On demand | User action |
| Charts | Polling | 60 seconds |

Consider using Supabase Realtime for activity feed if polling is too heavy.

---

## Mobile Responsiveness

**Priority:** Desktop-first, but should be usable on tablet.

**Breakpoints:**
- Desktop: Full layout with sidebar
- Tablet: Collapsible sidebar, stacked KPIs
- Mobile: Not required (admin work is desktop)

---

## Implementation Order

**Phase 1: Foundation**
1. Admin layout with sidebar
2. Admin route protection middleware
3. Command center page (static)

**Phase 2: Core Monitoring**
4. System status page
5. Client directory
6. Client detail page

**Phase 3: Operations**
7. Global campaigns view
8. Global leads view
9. Activity log
10. Reply inbox

**Phase 4: Financials**
11. Revenue dashboard
12. AI spend dashboard
13. Channel costs

**Phase 5: Compliance & Settings**
14. Suppression management
15. Bounce/spam tracker
16. Platform settings
17. User management

---

## Success Criteria

Admin dashboard is complete when you can:

1. ✅ See MRR, client count, and system status at a glance
2. ✅ Get alerted to problems before clients notice
3. ✅ View any client's data and impersonate if needed
4. ✅ Track AI and channel costs by client
5. ✅ Monitor Prefect flows and system health
6. ✅ Manage global suppression list
7. ✅ Adjust platform settings without code changes

---

## Next Steps

1. Create database migration for `is_platform_admin`
2. Create admin API routes
3. Build admin layout and components
4. Implement pages in order above

---
