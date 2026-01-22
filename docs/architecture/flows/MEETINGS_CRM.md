# Meetings & CRM — Agency OS

**Purpose:** Manage meeting lifecycle (booking to outcome), track deals through sales pipeline, and push data to client CRMs (HubSpot, Pipedrive, Close).
**Status:** IMPLEMENTED
**Last Updated:** 2026-01-21

---

## Overview

The Meetings & CRM system handles the downstream outcomes of successful outreach campaigns. When a lead books a meeting, the system tracks the meeting through its lifecycle (confirmation, reminder, attendance, outcome), optionally creates deals, and pushes this data to the client's CRM.

This is a one-way push architecture: Agency OS pushes meeting and deal data to client CRMs but does not pull data back. Clients use their existing CRM as their system of record while Agency OS handles lead generation and qualification.

The system also provides attribution tracking to understand which outreach activities and channels contributed to meetings and revenue, feeding data back into Conversion Intelligence (CIS) for optimization.

---

## Code Locations

| Component | File | Purpose |
|-----------|------|---------|
| **Meeting Service** | `src/services/meeting_service.py` | Meeting CRUD, lifecycle, show rate analytics |
| **Deal Service** | `src/services/deal_service.py` | Deal CRUD, pipeline tracking, revenue attribution |
| **CRM Push Service** | `src/services/crm_push_service.py` | HubSpot/Pipedrive/Close integration |
| **Meetings API** | `src/api/routes/meetings.py` | Meeting list endpoints |
| **CRM API** | `src/api/routes/crm.py` | CRM connection/config endpoints |
| **Database Schema** | `supabase/migrations/028_downstream_outcomes.sql` | Meetings, deals, attribution tables |
| **CRM Schema** | `supabase/migrations/029_crm_push.sql` | CRM config and push log tables |

---

## Data Flow

### Meeting Booking to CRM Push

```
                        MEETING BOOKED
                              |
                              v
                   +--------------------+
                   | MeetingService.    |
                   | create()           |
                   +--------------------+
                              |
        +---------------------+---------------------+
        |                                           |
        v                                           v
+------------------+                    +---------------------------+
| Update Lead:     |                    | CRMPushService.           |
| - meeting_booked |                    | push_meeting_booked()     |
| - status =       |                    | (non-blocking)            |
| meeting_booked   |                    +---------------------------+
+------------------+                                |
                                    +---------------+---------------+
                                    |               |               |
                                    v               v               v
                              +----------+   +----------+   +-------+
                              | HubSpot  |   | Pipedrive|   | Close |
                              +----------+   +----------+   +-------+
                                    |               |               |
                                    v               v               v
                           +------------------------------------------------+
                           |          CRM Push Log (audit trail)            |
                           | - operation, status, crm_contact_id            |
                           | - crm_deal_id, request/response payload        |
                           +------------------------------------------------+
```

### Meeting Lifecycle

```
BOOKED → CONFIRMED → REMINDER_SENT → SHOWED_UP → OUTCOME_RECORDED → DEAL_CREATED
   |         |            |              |               |              |
   v         v            v              v               v              v
+-------+ +--------+ +--------+ +-------------+ +-----------+ +--------+
|booked | |confirmed|reminder | |showed_up    | |meeting_   | |deal_id |
|_at    | |_at      |sent_at  | |_confirmed_at| |outcome    | |created |
+-------+ +--------+ +--------+ +-------------+ +-----------+ +--------+
                                      |                            |
                                      v                            v
                               +-----------+               +---------------+
                               |no_show    |               |DealService.   |
                               |_reason    |               |create()       |
                               +-----------+               +---------------+
```

### Deal Pipeline

```
+---------------+   +----------+   +-------------+   +--------------+   +--------------+
| qualification |-->| proposal |-->| negotiation |-->| verbal_commit|-->| contract_sent|
+---------------+   +----------+   +-------------+   +--------------+   +--------------+
                                                            |
              +-----------------------------+----------------+
              |                             |
              v                             v
     +--------------+               +--------------+
     | closed_won   |               | closed_lost  |
     | - value      |               | - lost_reason|
     | - won = true |               | - won = false|
     +--------------+               +--------------+
              |
              v
     +--------------------------------+
     | Revenue Attribution            |
     | - first_touch / last_touch     |
     | - linear / time_decay          |
     +--------------------------------+
```

---

## Database Tables

### meetings

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | Primary key |
| `client_id` | UUID | Multi-tenancy |
| `lead_id` | UUID | Associated lead |
| `campaign_id` | UUID | Source campaign |
| `scheduled_at` | TIMESTAMPTZ | Meeting time |
| `duration_minutes` | INTEGER | Meeting length (default 30) |
| `meeting_type` | TEXT | discovery, demo, follow_up, close, onboarding, other |
| `booked_by` | TEXT | ai, human, lead |
| `booking_method` | TEXT | calendly, direct, phone |
| `meeting_link` | TEXT | Video call URL |
| `calendar_event_id` | TEXT | External calendar sync ID |
| `confirmed` | BOOLEAN | Lead confirmed attendance |
| `reminder_sent` | BOOLEAN | Reminder sent flag |
| `showed_up` | BOOLEAN | Attendance status |
| `meeting_outcome` | TEXT | good, bad, rescheduled, no_show, cancelled, pending |
| `meeting_notes` | TEXT | Notes from meeting |
| `next_steps` | TEXT | Agreed actions |
| `deal_created` | BOOLEAN | Deal was created from this meeting |
| `deal_id` | UUID | Reference to created deal |
| `converting_activity_id` | UUID | Activity that led to booking |
| `converting_channel` | channel_type | Channel that converted |
| `touches_before_booking` | INTEGER | Touch count before booking |
| `days_to_booking` | INTEGER | Days from first touch to booking |
| `rescheduled_count` | INTEGER | Number of reschedules |

### deals

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | Primary key |
| `client_id` | UUID | Multi-tenancy |
| `lead_id` | UUID | Associated lead |
| `meeting_id` | UUID | Source meeting |
| `name` | TEXT | Deal name |
| `value` | DECIMAL(12,2) | Deal value |
| `currency` | TEXT | Currency code (default AUD) |
| `probability` | INTEGER | Win probability 0-100 |
| `stage` | deal_stage_type | Pipeline stage |
| `stage_changed_at` | TIMESTAMPTZ | Last stage change |
| `expected_close_date` | DATE | Target close date |
| `closed_at` | TIMESTAMPTZ | Actual close timestamp |
| `won` | BOOLEAN | Win/loss outcome |
| `lost_reason` | deal_lost_reason_type | Why deal was lost |
| `lost_notes` | TEXT | Loss details |
| `days_to_close` | INTEGER | Total days from creation to close |
| `converting_activity_id` | UUID | Activity that created deal |
| `converting_channel` | channel_type | Channel that converted |
| `first_touch_channel` | channel_type | First outreach channel |
| `touches_before_deal` | INTEGER | Activities before deal creation |
| `external_crm` | TEXT | hubspot, pipedrive, close |
| `external_deal_id` | TEXT | CRM deal reference |

### client_crm_configs

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | Primary key |
| `client_id` | UUID | One config per client |
| `crm_type` | TEXT | hubspot, pipedrive, close |
| `api_key` | TEXT | For Pipedrive/Close |
| `oauth_access_token` | TEXT | For HubSpot |
| `oauth_refresh_token` | TEXT | For HubSpot |
| `oauth_expires_at` | TIMESTAMPTZ | Token expiry |
| `hubspot_portal_id` | TEXT | HubSpot account ID |
| `pipeline_id` | TEXT | Target pipeline |
| `stage_id` | TEXT | Target stage for new deals |
| `owner_id` | TEXT | Default deal owner |
| `is_active` | BOOLEAN | Connection active |
| `connection_status` | TEXT | pending, connected, error, disconnected |
| `last_successful_push_at` | TIMESTAMPTZ | Last successful push |
| `last_error` | TEXT | Most recent error |

### crm_push_log

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | Primary key |
| `client_id` | UUID | Multi-tenancy |
| `crm_config_id` | UUID | Config reference |
| `operation` | TEXT | find_contact, create_contact, create_deal, etc. |
| `lead_id` | UUID | Related lead |
| `meeting_id` | UUID | Related meeting |
| `crm_contact_id` | TEXT | CRM contact reference |
| `crm_deal_id` | TEXT | CRM deal reference |
| `crm_org_id` | TEXT | CRM organization (Pipedrive) |
| `request_payload` | JSONB | Request body for debugging |
| `response_payload` | JSONB | Response body for debugging |
| `status` | TEXT | success, failed, skipped |
| `error_code` | TEXT | Error type |
| `error_message` | TEXT | Error details |
| `duration_ms` | INTEGER | API call duration |

---

## CRM Integrations

### Supported CRMs

| CRM | Auth Method | Contact Entity | Deal Entity | Organization |
|-----|-------------|----------------|-------------|--------------|
| **HubSpot** | OAuth 2.0 | Contact | Deal | N/A (via contact) |
| **Pipedrive** | API Key | Person | Deal | Organization |
| **Close** | API Key | Lead (combined) | Opportunity | N/A |

### HubSpot OAuth Flow

```
1. Frontend: GET /api/v1/crm/connect/hubspot
   - Returns OAuth URL with state parameter

2. User redirected to HubSpot authorization page

3. HubSpot callback: GET /api/v1/crm/callback/hubspot?code=X&state=Y
   - Validates state (CSRF protection)
   - Exchanges code for tokens
   - Saves config with access_token, refresh_token, expires_at

4. Token refresh: Automatic before expiry
   - Checks oauth_expires_at before each API call
   - Refreshes if expiring within 5 minutes
```

### API Key Connection (Pipedrive/Close)

```
1. Frontend: POST /api/v1/crm/connect/pipedrive
   - Body: { "api_key": "..." }

2. Backend tests connection by fetching pipelines

3. If successful, saves config

4. Returns updated config with connection status
```

### Push Operation Flow

```python
async def push_meeting_booked(client_id, lead, meeting):
    # 1. Get CRM config for client
    config = await get_config(client_id)
    if not config:
        return CRMPushResult(skipped=True, reason="No CRM configured")

    # 2. Refresh OAuth token if needed (HubSpot)
    if config.crm_type == "hubspot":
        config = await _refresh_hubspot_token_if_needed(config)

    # 3. Find or create contact
    contact_id = await find_or_create_contact(config, lead)

    # 4. Create deal
    deal_id, org_id = await create_deal(config, lead, meeting, contact_id)

    # 5. Log operation
    await log_push(operation="create_deal", status="success", ...)

    return CRMPushResult(success=True, crm_contact_id=contact_id, crm_deal_id=deal_id)
```

---

## Meeting Types

| Type | Description | Typical Duration |
|------|-------------|------------------|
| `discovery` | Initial qualification call | 30 min |
| `demo` | Product demonstration | 45-60 min |
| `follow_up` | Post-demo follow-up | 30 min |
| `close` | Final negotiation/close | 30 min |
| `onboarding` | New customer onboarding | 60 min |
| `other` | Miscellaneous | 30 min |

## Meeting Outcomes

| Outcome | Description | Impact |
|---------|-------------|--------|
| `good` | Positive meeting, moving forward | Auto-sets showed_up=true |
| `bad` | Meeting happened but negative outcome | Auto-sets showed_up=true |
| `rescheduled` | Meeting moved to new time | Increments rescheduled_count |
| `no_show` | Lead did not attend | Auto-sets showed_up=false |
| `cancelled` | Meeting cancelled | Records reason in notes |
| `pending` | Meeting happened, outcome TBD | Default after show |

## Deal Stages

| Stage | Probability | Description |
|-------|-------------|-------------|
| `qualification` | 20% | Initial qualification |
| `proposal` | 40% | Proposal sent |
| `negotiation` | 60% | Active negotiation |
| `verbal_commit` | 80% | Verbal agreement |
| `contract_sent` | 90% | Contract awaiting signature |
| `closed_won` | 100% | Deal won |
| `closed_lost` | 0% | Deal lost |

## Lost Reasons

| Reason | Description |
|--------|-------------|
| `price_too_high` | Budget/price objection |
| `chose_competitor` | Selected alternative vendor |
| `no_budget` | No budget available |
| `timing_not_right` | Timing issue |
| `no_decision` | Unable to reach decision |
| `champion_left` | Internal advocate left |
| `project_cancelled` | Project no longer needed |
| `went_silent` | Lost contact |
| `bad_fit` | Solution mismatch |
| `other` | Other reasons |

---

## API Endpoints

### Meeting Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/clients/{client_id}/meetings` | GET | List meetings (supports `upcoming` filter) |

### CRM Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/crm/config` | GET | Get current CRM configuration |
| `/crm/config` | PUT | Update CRM config (pipeline, stage, owner) |
| `/crm/connect/hubspot` | POST | Start HubSpot OAuth flow |
| `/crm/callback/hubspot` | GET | HubSpot OAuth callback |
| `/crm/connect/pipedrive` | POST | Connect Pipedrive with API key |
| `/crm/connect/close` | POST | Connect Close with API key |
| `/crm/disconnect` | DELETE | Disconnect CRM integration |
| `/crm/test` | POST | Test CRM connection |
| `/crm/pipelines` | GET | List available pipelines |
| `/crm/stages/{pipeline_id}` | GET | List stages for pipeline |
| `/crm/users` | GET | List CRM users for owner dropdown |
| `/crm/logs` | GET | Get CRM push audit logs |

---

## Analytics Functions

### Show Rate Analysis

```sql
SELECT * FROM get_show_rate_analysis(client_id, days);
-- Returns: total_meetings, show_rate, no_show_rate, reschedule_rate,
--          confirmed_show_rate, reminded_show_rate
```

### Funnel Analytics

```sql
SELECT * FROM get_funnel_analytics(client_id, days);
-- Returns: total_leads, meetings_booked, meetings_showed, deals_created,
--          deals_won, total_pipeline_value, total_won_value,
--          show_rate, deal_win_rate, lead_to_meeting_rate, lead_to_win_rate
```

### Revenue Attribution

```sql
SELECT * FROM get_channel_revenue_attribution(client_id, days, model);
-- Models: 'first_touch', 'last_touch', 'linear', 'time_decay'
-- Returns: channel, deals_attributed, total_value, avg_deal_value, percentage_of_revenue
```

### Lost Deal Analysis

```sql
SELECT * FROM get_lost_deal_analysis(client_id, days);
-- Returns: lost_reason, count, total_lost_value, avg_days_in_pipeline, common_stage_lost
```

---

## Key Rules

1. **One-Way Push:** Agency OS pushes to client CRMs but never pulls data back.

2. **One CRM Per Client:** Each client can connect exactly one CRM integration.

3. **Non-Blocking CRM Push:** CRM push failures do not block meeting creation.

4. **Automatic Token Refresh:** HubSpot OAuth tokens are refreshed automatically before expiry.

5. **Contact Deduplication:** System searches for existing contact by email before creating new one.

6. **Deal Auto-Creation:** Deals can be created automatically when recording a "good" meeting outcome.

7. **Stage History Tracked:** All deal stage changes are recorded in `deal_stage_history` table via trigger.

8. **Attribution Models:** Four attribution models available for revenue analysis.

9. **Audit Trail:** All CRM operations are logged in `crm_push_log` with request/response payloads.

10. **Soft Deletes Only:** Never hard delete records; use `deleted_at` timestamp (Rule 14).

---

## Configuration

| Setting | Default | Notes |
|---------|---------|-------|
| `settings.hubspot_client_id` | - | HubSpot OAuth app client ID |
| `settings.hubspot_client_secret` | - | HubSpot OAuth app secret |
| `settings.hubspot_redirect_uri` | - | OAuth callback URL |
| `settings.hubspot_scopes` | - | OAuth scopes (comma-separated) |

### CRM Config Options

| Option | Description | Set Via |
|--------|-------------|---------|
| `pipeline_id` | Target pipeline for new deals | PUT /crm/config |
| `stage_id` | Target stage for new deals | PUT /crm/config |
| `owner_id` | Default deal owner | PUT /crm/config |

---

## Error Handling

| Error Type | Handling |
|------------|----------|
| No CRM configured | Returns `skipped=True`, meeting creation continues |
| OAuth token expired | Auto-refresh attempted, then fail if refresh fails |
| Contact creation failed | Logged to crm_push_log, meeting creation continues |
| Deal creation failed | Logged to crm_push_log, meeting creation continues |
| Rate limit hit | Logged, retry later |
| Invalid API key | Logged, config marked with error |

---

## Cross-References

- [`./OUTREACH.md`](./OUTREACH.md) - Outreach execution that leads to meetings
- [`../business/SCORING.md`](../business/SCORING.md) - ALS scoring that qualifies leads
- [`./REPLY_HANDLING.md`](./REPLY_HANDLING.md) - Reply handling that detects meeting intent
- [`../business/TIERS_AND_BILLING.md`](../business/TIERS_AND_BILLING.md) - Tier limits for meetings

---

For gaps and implementation status, see [`../TODO.md`](../TODO.md).
