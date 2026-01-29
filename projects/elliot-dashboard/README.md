# Elliot Dashboard

A real-time dashboard for visualizing Elliot's memory, decisions, learnings, and activity within the Agency OS ecosystem.

## Overview

The Elliot Dashboard provides visibility into:
- **Memory Contents**: Daily logs, weekly rollups, observed patterns
- **Knowledge Base**: Operating rules, extracted learnings, decision tracking with outcomes
- **Agent Activity**: Real-time stream of what Elliot is doing
- **Agency OS Health**: Service status monitoring

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Elliot        │     │   FastAPI       │     │   Next.js       │
│   (Clawdbot)    │────▶│   Backend       │────▶│   Dashboard     │
│   Local Files   │     │   (Railway)     │     │   (Vercel)      │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │  Sync Service         │  REST API             │  Realtime
         │  (Prefect)            │                       │  Subscriptions
         ▼                       ▼                       ▼
    ┌─────────────────────────────────────────────────────────┐
    │                    Supabase (PostgreSQL)                 │
    │  • elliot_daily_logs     • elliot_activity              │
    │  • elliot_decisions      • elliot_sync_state            │
    │  • elliot_learnings      • service_health               │
    │  • elliot_patterns       • elliot_rules                 │
    └─────────────────────────────────────────────────────────┘
```

## Files in This Project

| File | Purpose |
|------|---------|
| `DESIGN.md` | High-level architecture and design decisions |
| `schema.sql` | Complete Supabase database schema |
| `api_spec.yaml` | OpenAPI 3.1 specification for all endpoints |
| `api_router.py` | FastAPI router implementation |
| `components.md` | Next.js frontend component specifications |
| `sync_service.py` | Prefect-based file↔database sync service |

## Quick Start

### 1. Database Setup

Run the schema in Supabase SQL Editor:

```bash
# Copy schema.sql contents to Supabase SQL Editor and execute
```

This creates:
- All Elliot memory/knowledge tables
- Activity tracking tables
- Service health monitoring
- Sync state tracking
- Row Level Security policies (admin only)
- Realtime subscriptions

### 2. Backend Integration

Add the router to your FastAPI app:

```python
# In your main.py or routes/__init__.py
from api_router import elliot_router

app.include_router(elliot_router, prefix="/api/elliot")
```

Dependencies needed:
```
fastapi
pydantic
supabase
```

### 3. Sync Service Deployment

Deploy as a Prefect flow on Railway:

```bash
# Set environment variables
export SUPABASE_URL=...
export SUPABASE_SERVICE_ROLE_KEY=...
export REDIS_URL=...

# Run one-time sync
python sync_service.py sync file_to_db

# Run file watcher (continuous)
python sync_service.py watch
```

### 4. Frontend Setup

Add pages to your Next.js dashboard:

```
app/dashboard/elliot/
├── page.tsx           # Overview
├── memory/
│   ├── daily/
│   └── patterns/
├── knowledge/
│   ├── rules/
│   ├── learnings/
│   └── decisions/
└── activity/
```

See `components.md` for full component specs and implementation details.

## Key Features

### Memory Timeline
- Calendar heatmap of daily activity
- Drill-down from year → week → day
- Pattern overlays showing recurring themes

### Decision Tracker
- Kanban board: Pending → Success/Partial/Failure
- Outcome tracking with learning extraction
- Days-since-decision indicators

### Real-time Activity Feed
- Live updates via Supabase subscriptions
- Filter by type, channel, session
- Token usage tracking

### Sync System
- Bidirectional file ↔ database sync
- Checksum-based change detection
- Conflict detection and resolution UI
- Queue-based processing with debouncing

## Authentication

Uses Agency OS Supabase auth:
- JWT-based authentication
- Admin-only access via RLS policies
- Protected API endpoints

## Environment Variables

```bash
# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...  # For sync service only

# Redis (Upstash)
REDIS_URL=redis://...

# Optional
PREFECT_API_URL=https://prefect-server-production-f9b1.up.railway.app/api
```

## Implementation Phases

### Phase 1: Core (Week 1)
- [x] Database schema design
- [x] API endpoint specs
- [ ] Basic CRUD endpoints
- [ ] Memory browser UI (read-only)

### Phase 2: Sync (Week 2)
- [x] Sync service design
- [ ] File → DB sync implementation
- [ ] Prefect flow deployment
- [ ] Sync status dashboard

### Phase 3: Real-time (Week 3)
- [ ] Supabase subscriptions
- [ ] Live activity feed
- [ ] Health monitoring

### Phase 4: Polish (Week 4)
- [ ] Pattern visualization (D3/force graph)
- [ ] Decision tracking Kanban
- [ ] Bi-directional sync
- [ ] Mobile responsive

## Notes

- The sync service runs on the same machine as Clawdbot (file access required)
- Use service role key for sync service (bypasses RLS)
- Activity logging can be integrated directly into Clawdbot if needed
- Consider rate limiting sync for high-activity periods
