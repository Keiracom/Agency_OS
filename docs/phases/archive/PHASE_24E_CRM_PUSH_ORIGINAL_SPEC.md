# Phase 24E: CRM Integration

**Status:** 📋 Planned  
**Priority:** Pre-Launch (onboarding flow)  
**Estimate:** 15 hours  
**Tasks:** 12

---

## Purpose

1. **OAuth Pull (one-time):** Extract client's profile + existing customers from their CRM at onboarding
2. **Webhook Push (ongoing):** Send meeting bookings to client's webhook URL

---

## Architecture

```
ONBOARDING:
Client clicks "Connect HubSpot"
        ↓
    OAuth popup
        ↓
We extract: name, email, phone, company, customers
        ↓
    Store in database
        ↓
Continue onboarding


ONGOING:
Meeting booked in Agency OS
        ↓
POST to client's webhook URL
        ↓
{event: "meeting_booked", lead: {...}, meeting: {...}}
        ↓
Client handles it (Zapier → their CRM)
```

---

## Database Schema

### Migration: 029_crm_integration.sql

```sql
-- OAuth tokens for CRM connections (one-time extraction)
CREATE TABLE client_crm_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    
    provider TEXT NOT NULL,  -- 'hubspot', 'pipedrive'
    
    access_token TEXT,
    refresh_token TEXT,
    expires_at TIMESTAMPTZ,
    
    extracted_profile JSONB,
    extracted_customers_count INTEGER DEFAULT 0,
    
    connected_at TIMESTAMPTZ DEFAULT NOW(),
    last_sync_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE (client_id, provider)
);

-- Webhook configuration for meeting push
CREATE TABLE client_webhook_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    
    webhook_url TEXT NOT NULL,
    auth_header TEXT,
    
    send_meeting_booked BOOLEAN DEFAULT true,
    send_meeting_completed BOOLEAN DEFAULT false,
    send_deal_won BOOLEAN DEFAULT false,
    
    is_active BOOLEAN DEFAULT true,
    last_push_at TIMESTAMPTZ,
    last_error TEXT,
    consecutive_failures INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE (client_id)
);

-- Webhook push log
CREATE TABLE webhook_push_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id),
    
    event_type TEXT NOT NULL,
    lead_id UUID REFERENCES leads(id),
    meeting_id UUID REFERENCES meetings(id),
    deal_id UUID REFERENCES deals(id),
    
    request_url TEXT,
    request_payload JSONB,
    response_status INTEGER,
    response_body TEXT,
    
    status TEXT NOT NULL,
    error TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Tasks

### Part A: Database

| ID | Task | Est | Status |
|----|------|-----|--------|
| CRM-001 | Create migration 029_crm_integration.sql | 1h | ⬜ |

### Part B: OAuth Pull

| ID | Task | Est | Status |
|----|------|-----|--------|
| CRM-002 | HubSpot OAuth flow (authorize + callback) | 2h | ⬜ |
| CRM-003 | HubSpot extract profile (name, email, phone, company) | 1h | ⬜ |
| CRM-004 | HubSpot extract customers (closed-won deals) | 2h | ⬜ |
| CRM-005 | Pipedrive OAuth flow | 2h | ⬜ |
| CRM-006 | Pipedrive extract profile | 1h | ⬜ |
| CRM-007 | Pipedrive extract customers (won deals) | 2h | ⬜ |

### Part C: Webhook Push

| ID | Task | Est | Status |
|----|------|-----|--------|
| CRM-008 | Build WebhookPushService | 2h | ⬜ |
| CRM-009 | Integrate with Closer Engine (on meeting booked) | 1h | ⬜ |

### Part D: UI + Tests

| ID | Task | Est | Status |
|----|------|-----|--------|
| CRM-010 | Onboarding CRM connect page | 2h | ⬜ |
| CRM-011 | Settings webhook URL page | 1h | ⬜ |
| CRM-012 | Write tests | 2h | ⬜ |

---

## Files to Create

```
supabase/migrations/029_crm_integration.sql
src/services/crm_oauth_service.py
src/services/webhook_push_service.py
src/api/routes/oauth.py
frontend/app/onboarding/connect-crm/page.tsx
frontend/app/onboarding/profile/page.tsx
frontend/components/settings/WebhookSettings.tsx
tests/test_services/test_crm_oauth_service.py
tests/test_services/test_webhook_push_service.py
```

## Files to Modify

```
src/engines/closer.py (add webhook push on meeting booked)
src/api/main.py (register oauth routes)
src/services/__init__.py (export new services)
```

---

## Webhook Payload Format

```json
{
  "event": "meeting_booked",
  "timestamp": "2026-01-15T10:30:00Z",
  "lead": {
    "name": "Sarah Chen",
    "email": "sarah@buildright.com.au",
    "phone": "+61412345678",
    "company": "BuildRight Construction",
    "title": "Marketing Director",
    "linkedin_url": "https://linkedin.com/in/sarahchen"
  },
  "meeting": {
    "id": "uuid",
    "scheduled_at": "2026-01-20T14:00:00Z",
    "duration_minutes": 30,
    "meeting_type": "discovery_call",
    "meeting_link": "https://meet.google.com/xxx"
  },
  "campaign": {
    "id": "uuid",
    "name": "Q1 Construction Outreach"
  }
}
```

---

## Environment Variables

```bash
# HubSpot OAuth
HUBSPOT_CLIENT_ID=
HUBSPOT_CLIENT_SECRET=

# Pipedrive OAuth
PIPEDRIVE_CLIENT_ID=
PIPEDRIVE_CLIENT_SECRET=
```

---

## OAuth Registration Required

Before implementation, register OAuth apps:

1. **HubSpot:** https://developers.hubspot.com/
   - Create app
   - Get Client ID + Secret
   - Set redirect: `https://agency-os-production.up.railway.app/api/v1/oauth/hubspot/callback`

2. **Pipedrive:** https://developers.pipedrive.com/
   - Create app
   - Get Client ID + Secret
   - Set redirect: `https://agency-os-production.up.railway.app/api/v1/oauth/pipedrive/callback`
