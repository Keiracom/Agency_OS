# Elliot Dashboard - Technical Design

*A dashboard for visualizing Elliot's memory, decisions, and activity within Agency OS.*

## Overview

The Elliot Dashboard provides real-time visibility into:
- **Memory Contents**: Daily logs, weekly rollups, patterns
- **Knowledge Base**: Rules, learnings, decisions with outcomes
- **Agent Activity**: What Elliot is doing, thinking, processing
- **Agency OS Health**: Service status, recent operations

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Elliot        │     │   FastAPI       │     │   Next.js       │
│   (Clawdbot)    │────▶│   Backend       │────▶│   Dashboard     │
│                 │     │   (Railway)     │     │   (Vercel)      │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │              ┌────────┴────────┐              │
         │              │                 │              │
         ▼              ▼                 ▼              ▼
    ┌─────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────┐
    │ Files   │   │  Supabase   │   │   Redis     │   │ Realtime│
    │ (local) │◀─▶│  (Postgres) │   │  (Upstash)  │   │  (WS)   │
    └─────────┘   └─────────────┘   └─────────────┘   └─────────┘
```

### Data Flow

1. **Elliot → Files**: Normal memory operations (existing behavior)
2. **Sync Service → Supabase**: Watches files, syncs to database
3. **Supabase → Dashboard**: Real-time subscriptions for live updates
4. **Dashboard → API → Supabase**: User edits sync back
5. **Sync Service → Files**: Database changes write back to files

---

## Database Schema

See `schema.sql` for full implementation.

### Core Tables

| Table | Purpose |
|-------|---------|
| `elliot_daily_logs` | Daily memory entries |
| `elliot_weekly_rollups` | Weekly synthesized insights |
| `elliot_patterns` | Recurring patterns observed |
| `elliot_rules` | Non-negotiable operating rules |
| `elliot_learnings` | Extracted permanent lessons |
| `elliot_decisions` | Decision log with outcomes |
| `elliot_activity` | Real-time agent activity stream |
| `elliot_sync_state` | File sync metadata |

### Relationships

- Decisions can link to learnings (outcome → lesson)
- Patterns link to source daily/weekly entries
- Activity logs reference which memory files were accessed

---

## API Endpoints

See `api_spec.yaml` for full OpenAPI spec.

### Memory Endpoints
```
GET    /api/elliot/memory/daily           # List daily logs
GET    /api/elliot/memory/daily/{date}    # Get specific day
POST   /api/elliot/memory/daily           # Create/update daily log
GET    /api/elliot/memory/weekly          # List weekly rollups
GET    /api/elliot/memory/patterns        # Get patterns
```

### Knowledge Endpoints
```
GET    /api/elliot/knowledge/rules        # Get rules
PUT    /api/elliot/knowledge/rules        # Update rules
GET    /api/elliot/knowledge/learnings    # List learnings
POST   /api/elliot/knowledge/learnings    # Add learning
GET    /api/elliot/knowledge/decisions    # List decisions
POST   /api/elliot/knowledge/decisions    # Log decision
PATCH  /api/elliot/knowledge/decisions/{id}  # Update outcome
```

### Activity Endpoints
```
GET    /api/elliot/activity               # Activity stream
GET    /api/elliot/activity/stats         # Aggregated stats
POST   /api/elliot/activity               # Log activity (internal)
```

### Sync Endpoints
```
POST   /api/elliot/sync/trigger           # Manual sync
GET    /api/elliot/sync/status            # Sync status
```

### Health Endpoints
```
GET    /api/health/services               # All service health
GET    /api/health/prefect                # Prefect status
GET    /api/health/redis                  # Redis status
```

---

## Frontend Structure

See `components.md` for full component specs.

### Pages

```
/dashboard
├── /elliot                    # Main Elliot dashboard
│   ├── /memory               # Memory browser
│   │   ├── /daily           # Daily logs calendar view
│   │   ├── /weekly          # Weekly rollups
│   │   └── /patterns        # Pattern visualization
│   ├── /knowledge           # Knowledge base
│   │   ├── /rules           # Operating rules
│   │   ├── /learnings       # Lessons learned
│   │   └── /decisions       # Decision log
│   ├── /activity            # Real-time activity
│   └── /settings            # Elliot config
└── /health                    # Agency OS health
```

### Key Components

- **MemoryTimeline**: Zoomable timeline of daily → weekly → patterns
- **DecisionTracker**: Kanban-style decision tracking with outcomes
- **ActivityFeed**: Real-time feed of Elliot's actions
- **HealthGrid**: Service status grid with metrics
- **PatternGraph**: Network graph of connected patterns/learnings

---

## Sync Mechanism

### File → Database Sync

1. **Watch Mode**: Prefect flow monitors `/home/elliotbot/clawd/memory/` and `/knowledge/`
2. **On Change**: Parse markdown, extract structured data
3. **Upsert**: Update Supabase with conflict resolution
4. **Track**: Update `elliot_sync_state` with checksums

### Database → File Sync

1. **Supabase Trigger**: On row update, publish to Redis channel
2. **Sync Service**: Subscribes to changes, writes to files
3. **Lock**: Prevent sync loop with sync_source tracking

### Conflict Resolution

- **Last-write-wins** for simple fields
- **Merge** for array fields (learnings list, etc.)
- **Manual resolution** UI for complex conflicts

---

## Real-time Updates

### Supabase Subscriptions

```typescript
// Subscribe to activity feed
supabase
  .channel('elliot-activity')
  .on('postgres_changes', {
    event: 'INSERT',
    schema: 'public',
    table: 'elliot_activity'
  }, handleNewActivity)
  .subscribe()
```

### Events to Subscribe

| Table | Events | Use |
|-------|--------|-----|
| `elliot_activity` | INSERT | Live activity feed |
| `elliot_decisions` | INSERT, UPDATE | Decision updates |
| `elliot_daily_logs` | INSERT, UPDATE | Memory updates |
| `service_health` | UPDATE | Health status changes |

---

## Authentication

Uses existing Agency OS auth:

1. **Supabase Auth**: JWT-based, shared with main app
2. **RLS Policies**: All Elliot tables restricted to admin role
3. **API Auth**: Bearer token validation in FastAPI
4. **Dashboard**: Protected routes via Next.js middleware

```sql
-- Example RLS policy
CREATE POLICY "Admin only" ON elliot_daily_logs
  FOR ALL USING (auth.jwt() ->> 'role' = 'admin');
```

---

## Implementation Priority

### Phase 1: Core (Week 1)
- [ ] Database schema + migrations
- [ ] Basic API endpoints (CRUD)
- [ ] Memory browser UI (read-only)
- [ ] Activity feed (manual logging)

### Phase 2: Sync (Week 2)
- [ ] File → DB sync service
- [ ] Prefect flow for watching
- [ ] Sync status dashboard

### Phase 3: Real-time (Week 3)
- [ ] Supabase subscriptions
- [ ] Live activity feed
- [ ] Health monitoring

### Phase 4: Polish (Week 4)
- [ ] Pattern visualization
- [ ] Decision tracking UI
- [ ] Bi-directional sync
- [ ] Mobile responsive

---

## Files in This Directory

| File | Purpose |
|------|---------|
| `DESIGN.md` | This file - overview |
| `schema.sql` | Database schema |
| `api_spec.yaml` | OpenAPI specification |
| `components.md` | Frontend component specs |
| `sync_service.py` | Sync service implementation |

