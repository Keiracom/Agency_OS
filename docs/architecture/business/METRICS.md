# Metrics & Spend Control Architecture

**Purpose:** Define metrics aggregation, analytics, and AI spend control systems.
**Status:** IMPLEMENTED
**Code Status:** COMPLETE — All components operational

---

## 1. Overview

Agency OS tracks three categories of metrics:

| Category | Purpose | Primary Consumer |
|----------|---------|------------------|
| **Campaign Metrics** | Outreach performance (sends, opens, replies, conversions) | Client dashboard |
| **SDK Spend** | Claude API usage and cost tracking | Platform admin, billing |
| **Rate Limiting** | Protect mailbox warmup during testing | Outreach flow |

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      METRICS LAYER                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │  Reporter Engine │  │ SDK Usage Service│  │ Send Limiter │  │
│  │  (reporter.py)   │  │(sdk_usage_svc.py)│  │(send_limiter)│  │
│  └────────┬─────────┘  └────────┬─────────┘  └──────┬───────┘  │
│           │                     │                   │          │
│           ▼                     ▼                   ▼          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   PostgreSQL (Supabase)                  │  │
│  │  activities │ sdk_usage_log │ leads │ campaigns │ meets  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API LAYER (/api/v1/reports)                │
├─────────────────────────────────────────────────────────────────┤
│  /campaigns/{id}        │  Campaign metrics with channel breakdown │
│  /campaigns/{id}/daily  │  Daily trend breakdown                   │
│  /clients/{id}          │  Cross-campaign client metrics           │
│  /clients/{id}/dashboard-metrics  │  Outcome-focused dashboard    │
│  /clients/{id}/activities         │  Live activity feed           │
│  /clients/{id}/archive/content    │  Searchable content archive   │
│  /clients/{id}/best-of            │  High-performing examples     │
│  /leads/distribution    │  ALS tier distribution                   │
│  /leads/{id}/engagement │  Individual lead timeline                │
│  /activity/daily        │  Daily activity summary                  │
│  /pool/analytics        │  Lead pool metrics                       │
│  /pool/assignments/analytics  │  Assignment performance            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Reporter Engine

**File:** `src/engines/reporter.py` (690 lines)
**Layer:** 3 - Engines

### 3.1 Methods

| Method | Purpose | Returns |
|--------|---------|---------|
| `get_campaign_metrics()` | Per-campaign metrics with channel breakdown | Sends, delivery, open, click, reply, bounce, conversion rates |
| `get_client_metrics()` | Aggregate metrics across all client campaigns | Overall + per-campaign summary |
| `get_als_distribution()` | Lead distribution by ALS tier | Hot/Warm/Cool/Cold/Dead counts + percentages |
| `get_lead_engagement()` | Individual lead activity timeline | Opens, clicks, replies, channels used |
| `get_daily_activity()` | Hourly activity breakdown for a day | Per-hour + per-channel counts |

### 3.2 Metrics Calculated

**Per-Channel Metrics:**
```python
{
    "sent": int,
    "delivered": int,
    "opened": int,        # Email only
    "clicked": int,       # Email only
    "replied": int,
    "bounced": int,
    "unsubscribed": int,
    "converted": int,
    "delivery_rate": float,    # delivered / sent
    "open_rate": float,        # opened / delivered (email)
    "click_rate": float,       # clicked / opened (email)
    "click_through_rate": float,  # clicked / delivered (email)
    "reply_rate": float,       # replied / sent
    "conversion_rate": float,  # converted / sent
    "bounce_rate": float,      # bounced / sent
}
```

### 3.3 Data Sources

| Metric | Source Table | Action Field |
|--------|--------------|--------------|
| Sends | `activities` | `action = 'sent'` |
| Deliveries | `activities` | `action = 'delivered'` |
| Opens | `activities` | `action = 'opened'` |
| Clicks | `activities` | `action = 'clicked'` |
| Replies | `activities` | `action = 'replied'` |
| Bounces | `activities` | `action = 'bounced'` |
| Conversions | `activities` | `action = 'converted'` |
| Meetings | `meetings` | — |

---

## 4. SDK Usage & Cost Tracking

**File:** `src/services/sdk_usage_service.py` (294 lines)
**Layer:** 3 - Services
**Table:** `sdk_usage_log`

### 4.1 Purpose

Tracks every Claude API call made by SDK agents to:
1. Monitor AI spend per client
2. Identify cost optimization opportunities
3. Support billing reconciliation
4. Detect anomalies (runaway agents)

### 4.2 Methods

| Method | Purpose |
|--------|---------|
| `log_sdk_usage()` | Log individual SDK call with tokens, cost, duration |
| `log_sdk_result()` | Convenience wrapper for SDKBrainResult objects |
| `get_client_sdk_spend()` | Get spend breakdown by agent type for a client |
| `get_daily_sdk_spend()` | Get daily spend trend (optionally filtered by client) |

### 4.3 Fields Tracked

```python
{
    "client_id": UUID,           # Required
    "agent_type": str,           # icp_extraction, enrichment, email, voice_kb, objection
    "model_used": str,           # claude-sonnet-4-20250514, etc.
    "input_tokens": int,
    "output_tokens": int,
    "cached_tokens": int,        # Prompt caching
    "cost_aud": float,           # Total cost in AUD
    "turns_used": int,           # Agent turns
    "duration_ms": int,          # Execution time
    "tool_calls": list[dict],    # Tools invoked
    "success": bool,
    "error_message": str | None,
    "lead_id": UUID | None,
    "campaign_id": UUID | None,
}
```

### 4.4 Cost Limits per Agent

**Source:** `CLAUDE.md` SDK Cost Controls section

| Agent | Max Cost (AUD) | Max Turns |
|-------|----------------|-----------|
| Enrichment | $1.50 | 8 |
| Email | $0.50 | 3 |
| Voice KB | $2.00 | 3 |
| ICP Extraction | $1.00 | 5 |

### 4.5 Usage Pattern

```python
from src.services.sdk_usage_service import log_sdk_result

# After SDK agent execution
result = await sdk_brain.run(...)

await log_sdk_result(
    db,
    result,
    client_id=client_id,
    agent_type="email",
    lead_id=lead_id,
    campaign_id=campaign_id,
)
```

---

## 5. Send Limiter (TEST_MODE Protection)

**File:** `src/services/send_limiter.py` (107 lines)
**Layer:** 3 - Services

### 5.1 Purpose

Protects mailbox warmup during testing by enforcing daily send limits. Only active when `TEST_MODE=true`.

### 5.2 Methods

| Method | Purpose | Returns |
|--------|---------|---------|
| `check_email_limit()` | Check if client is under daily limit | `(is_allowed: bool, current_count: int)` |
| `get_remaining_quota()` | Get remaining emails for the day | `int` (-1 if no limit) |

### 5.3 Configuration

**Source:** `src/config/settings.py`

```python
TEST_MODE = True/False           # Enable/disable limiting
TEST_DAILY_EMAIL_LIMIT = 15      # Max emails per client per day
```

### 5.4 Usage in Outreach Flow

```python
from src.services.send_limiter import send_limiter

is_allowed, current_count = await send_limiter.check_email_limit(db, client_id)
if not is_allowed:
    logger.info(f"Daily email limit reached: {current_count}/{settings.TEST_DAILY_EMAIL_LIMIT}")
    return  # Skip sending
```

---

## 6. API Endpoints

**File:** `src/api/routes/reports.py` (1700+ lines)
**Prefix:** `/api/v1/reports`

### 6.1 Campaign Metrics

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/campaigns/{id}` | GET | Campaign performance with channel breakdown |
| `/campaigns/{id}/daily` | GET | Daily trend breakdown |

**Query Parameters:**
- `start_date` (optional): YYYY-MM-DD
- `end_date` (optional): YYYY-MM-DD (defaults to today)

### 6.2 Client Metrics

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/clients/{id}` | GET | Cross-campaign metrics |
| `/clients/{id}/dashboard-metrics` | GET | Outcome-focused dashboard (meetings, show rate) |
| `/clients/{id}/activities` | GET | Paginated activity feed |
| `/clients/{id}/archive/content` | GET | Searchable sent content archive |
| `/clients/{id}/best-of` | GET | High-performing content examples |

### 6.3 Lead Analytics

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/leads/distribution` | GET | ALS tier distribution |
| `/leads/{id}/engagement` | GET | Individual lead timeline |

### 6.4 Activity Analytics

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/activity/daily` | GET | Daily activity summary with hourly breakdown |

### 6.5 Pool Analytics

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/pool/analytics` | GET | Lead pool size, utilization, distributions |
| `/pool/assignments/analytics` | GET | Assignment metrics, top industries |
| `/pool/clients/{id}/analytics` | GET | Client-specific pool analytics |

---

## 7. Dashboard Metrics (Outcome-Focused)

**Endpoint:** `GET /clients/{id}/dashboard-metrics`

### 7.1 Philosophy

The dashboard shows **outcomes** (meetings, conversions), not commodity metrics (lead counts, credits). This keeps clients focused on business value, not implementation details.

### 7.2 Response Structure

```python
{
    "period": "2026-01",
    "outcomes": {
        "meetings_booked": 12,
        "show_rate": 75.0,          # Percentage
        "meetings_showed": 9,
        "deals_created": 3,
        "status": "on_track"        # "ahead" | "on_track" | "behind"
    },
    "comparison": {
        "meetings_vs_last_month": 4,
        "meetings_vs_last_month_pct": 50.0,
        "tier_target_low": 5,
        "tier_target_high": 15
    },
    "activity": {
        "prospects_in_pipeline": 150,
        "active_sequences": 45,
        "replies_this_month": 18,
        "reply_rate": 12.0
    },
    "campaigns": [
        {
            "id": "uuid",
            "name": "Q1 Outreach",
            "priority_pct": 60,
            "meetings_booked": 8,
            "reply_rate": 15.2,
            "show_rate": 80.0
        }
    ]
}
```

### 7.3 On-Track Status Calculation

```python
# Pro-rate expected meetings based on days elapsed
expected = tier_midpoint * (days_elapsed / days_in_month)

if meetings_booked >= expected * 1.1:
    return "ahead"
elif meetings_booked >= expected * 0.9:
    return "on_track"
else:
    return "behind"
```

### 7.4 Tier Meeting Targets

| Tier | Low | High | Midpoint |
|------|-----|------|----------|
| Ignition | 5 | 15 | 10 |
| Velocity | 15 | 35 | 25 |
| Dominance | 40 | 80 | 60 |

---

## 8. Frontend Integration

### 8.1 Hooks

**File:** `frontend/hooks/use-reports.ts`

```typescript
// Dashboard summary stats (meetings, pipeline, activity)
useDashboardStats(clientId)

// Campaign performance metrics
useCampaignPerformance(campaignId, startDate?, endDate?)

// Channel breakdown (email, linkedin, sms, voice)
useChannelMetrics(campaignId)

// ALS tier distribution
useALSDistribution(campaignId | clientId)

// Daily activity breakdown
useDailyActivity(date?)

// Searchable content archive
useContentArchive(clientId, filters)

// High-performing content examples
useBestOfShowcase(clientId, limit?, periodDays?)

// Outcome-focused dashboard (meetings, show rate)
useDashboardMetrics(clientId)

// Real-time activity feed (with polling)
useActivityFeed(clientId, options)
```

### 8.2 API Client

**File:** `frontend/lib/api/reports.ts`

All endpoints are typed and use the centralized API client with auth token injection.

### 8.3 Dashboard Components

| Component | Purpose |
|-----------|---------|
| `HeroMetricsCard` | Meetings booked, show rate, on-track status |
| `LiveActivityFeed` | Real-time activity stream |
| `BestOfShowcase` | High-performing content examples |
| `ContentArchive` | Searchable sent content history |

---

## 9. Data Retention

| Data Type | Retention | Notes |
|-----------|-----------|-------|
| Activities | Indefinite | Core business data |
| SDK Usage Logs | 90 days | Aggregated for billing, detail pruned |
| Metrics Cache | None | Computed on-demand |

---

## 10. Scheduled Jobs

| Job | Schedule | Purpose |
|-----|----------|---------|
| `daily_pacing_flow` | 7 AM AEST | Check pacing, alert if >120% or <50% |
| `daily_digest_flow` | 7 AM AEST | Send daily metrics email to clients |

---

## 11. Code Locations

| Component | File |
|-----------|------|
| Reporter Engine | `src/engines/reporter.py` |
| SDK Usage Service | `src/services/sdk_usage_service.py` |
| SDK Usage Log Model | `src/models/sdk_usage_log.py` |
| Send Limiter | `src/services/send_limiter.py` |
| Reports API | `src/api/routes/reports.py` |
| Frontend Hooks | `frontend/hooks/use-reports.ts` |
| Frontend API Client | `frontend/lib/api/reports.ts` |
| Dashboard Design | `frontend/design/dashboard/metrics.md` |

---

For gaps and implementation status, see `../TODO.md`.
