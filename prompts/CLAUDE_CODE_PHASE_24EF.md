# Claude Code Prompt: Phase 24E (CRM Integration) + Phase 24F (Customer Import) + Test Mode

**Copy this entire prompt into a new Claude Code session.**

---

## Your Role

You are the Builder Agent for Agency OS Phase 24E, 24F, and Test Mode implementation. Your job is to:

1. Build CRM OAuth for profile + customer extraction (HubSpot, Pipedrive)
2. Build generic webhook push for meeting bookings
3. Build customer import and suppression system
4. Build platform buyer intelligence
5. Build test mode for safe E2E testing
6. Follow the specs exactly
7. Test as you build

---

## Before You Start

### Read These Files (In Order)

1. `docs/phases/PHASE_24E_CRM_PUSH.md` — CRM integration spec
2. `docs/phases/PHASE_24F_CUSTOMER_IMPORT.md` — Customer import spec
3. `skills/crm/CRM_INTEGRATION_SKILL.md` — Patterns and implementations
4. `PROGRESS.md` — Current status
5. `skills/agents/BUILDER_SKILL.md` — Code patterns and standards

### Verify Environment

```bash
# Check you can access the codebase
ls -la src/services/
ls -la supabase/migrations/

# Check latest migration number
ls supabase/migrations/ | tail -5
```

---

## Architecture Overview

### What We Pull (OAuth - One Time at Onboarding)

```
Client connects HubSpot/Pipedrive
        ↓
We extract:
- Name, email, phone (sender profile)
- Company name
- Existing customers (closed-won deals → suppression list)
        ↓
Store in: clients table, client_customers table, suppression_list table
```

### What We Push (Webhook - Ongoing)

```
Meeting booked in Agency OS
        ↓
POST to client's webhook URL
        ↓
Client handles it (Zapier → their CRM)
```

### Test Mode (All Outputs Redirected)

```
TEST_MODE=true
        ↓
All emails → david.stephens@keiracom.com
All SMS → +61457543392
All voice → +61457543392
All LinkedIn → https://www.linkedin.com/in/david-stephens-8847a636a/
```

---

## Implementation Order

### Phase 24E: CRM Integration (15h, 12 tasks)

**Part A: Database**
```
CRM-001: Create OAuth + webhook tables migration
```

**Part B: OAuth Pull (Profile + Customers)**
```
CRM-002: HubSpot OAuth flow (authorize + callback)
CRM-003: HubSpot extract profile (name, email, phone, company)
CRM-004: HubSpot extract customers (closed-won deals)
CRM-005: Pipedrive OAuth flow
CRM-006: Pipedrive extract profile
CRM-007: Pipedrive extract customers (won deals)
```

**Part C: Webhook Push (Meeting Bookings)**
```
CRM-008: Build WebhookPushService
CRM-009: Integrate with Closer Engine
```

**Part D: UI + Tests**
```
CRM-010: Onboarding CRM connect UI
CRM-011: Settings webhook URL UI
CRM-012: Write tests
```

---

### Phase 24F: Customer Import & Suppression (12h, 10 tasks)

```
CUST-001: Create customer + suppression + buyer signal tables
CUST-002: Build CustomerImportService
CUST-003: CSV upload + column mapping
CUST-004: Build SuppressionService
CUST-005: Update JIT Validator (check suppression)
CUST-006: Update Scout Engine (filter suppressed)
CUST-007: Build BuyerSignalService
CUST-008: Update Scorer Engine (buyer boost)
CUST-009: Customer import + suppression UI
CUST-010: Write tests
```

---

### Test Mode Implementation (3h, 6 tasks)

```
TEST-001: Add TEST_MODE config and env vars
TEST-002: Update Email Engine with redirect
TEST-003: Update SMS Engine with redirect
TEST-004: Update Voice Engine with redirect
TEST-005: Update LinkedIn Engine with redirect
TEST-006: Add daily send limit safeguard
```

---

## File Naming Conventions

### Migrations
```
supabase/migrations/029_crm_integration.sql    # CRM OAuth + webhook tables
supabase/migrations/030_customer_import.sql    # Customer + suppression + buyer signals
```

### Services
```
src/services/crm_oauth_service.py              # OAuth flows
src/services/webhook_push_service.py           # Webhook push
src/services/customer_import_service.py        # Customer import
src/services/suppression_service.py            # Suppression checks
src/services/buyer_signal_service.py           # Buyer intelligence
```

### API Routes
```
src/api/routes/oauth.py                        # OAuth endpoints
src/api/routes/webhooks.py                     # Add webhook config endpoints
src/api/routes/customers.py                    # Customer import
src/api/routes/suppression.py                  # Suppression management
```

### Frontend
```
frontend/app/onboarding/connect-crm/page.tsx   # CRM OAuth buttons
frontend/app/onboarding/profile/page.tsx       # Confirm sender profile
frontend/app/onboarding/customers/page.tsx     # Import customers
frontend/components/settings/WebhookSettings.tsx
frontend/components/settings/SuppressionList.tsx
```

---

## Database Schemas

### Migration 029: CRM Integration

```sql
-- OAuth tokens for CRM connections (one-time extraction)
CREATE TABLE client_crm_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    
    -- Provider
    provider TEXT NOT NULL,  -- 'hubspot', 'pipedrive'
    
    -- OAuth tokens (encrypted at rest)
    access_token TEXT,
    refresh_token TEXT,
    expires_at TIMESTAMPTZ,
    
    -- What we extracted
    extracted_profile JSONB,      -- {name, email, phone, company}
    extracted_customers_count INTEGER DEFAULT 0,
    
    -- Status
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
    
    -- Webhook URL
    webhook_url TEXT NOT NULL,
    
    -- Optional auth
    auth_header TEXT,  -- e.g., "Bearer xxx" or "Basic xxx"
    
    -- What to send
    send_meeting_booked BOOLEAN DEFAULT true,
    send_meeting_completed BOOLEAN DEFAULT false,
    send_deal_won BOOLEAN DEFAULT false,
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    last_push_at TIMESTAMPTZ,
    last_error TEXT,
    consecutive_failures INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE (client_id)
);

-- Webhook push log (audit trail)
CREATE TABLE webhook_push_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id),
    
    -- What we pushed
    event_type TEXT NOT NULL,  -- 'meeting_booked', 'meeting_completed', 'deal_won'
    
    -- References
    lead_id UUID REFERENCES leads(id),
    meeting_id UUID REFERENCES meetings(id),
    deal_id UUID REFERENCES deals(id),
    
    -- Request/Response
    request_url TEXT,
    request_payload JSONB,
    response_status INTEGER,
    response_body TEXT,
    
    -- Status
    status TEXT NOT NULL,  -- 'success', 'failed'
    error TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_crm_connections_client ON client_crm_connections(client_id);
CREATE INDEX idx_webhook_configs_client ON client_webhook_configs(client_id);
CREATE INDEX idx_webhook_log_client ON webhook_push_log(client_id);
CREATE INDEX idx_webhook_log_created ON webhook_push_log(created_at DESC);

-- RLS
ALTER TABLE client_crm_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE client_webhook_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhook_push_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Clients can view own CRM connections"
    ON client_crm_connections FOR ALL
    USING (client_id IN (SELECT id FROM clients WHERE user_id = auth.uid()));

CREATE POLICY "Clients can manage own webhook config"
    ON client_webhook_configs FOR ALL
    USING (client_id IN (SELECT id FROM clients WHERE user_id = auth.uid()));

CREATE POLICY "Clients can view own webhook logs"
    ON webhook_push_log FOR SELECT
    USING (client_id IN (SELECT id FROM clients WHERE user_id = auth.uid()));
```

### Migration 030: Customer Import

```sql
-- Client's existing customers (for suppression + social proof)
CREATE TABLE client_customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    
    -- Company identification
    company_name TEXT NOT NULL,
    domain TEXT,
    industry TEXT,
    employee_count_range TEXT,
    
    -- Primary contact
    contact_email TEXT,
    contact_name TEXT,
    contact_title TEXT,
    
    -- Customer data
    status TEXT NOT NULL DEFAULT 'active',  -- 'active', 'churned'
    customer_since DATE,
    churned_at DATE,
    deal_value DECIMAL(12,2),
    
    -- Social proof
    can_use_as_reference BOOLEAN DEFAULT false,
    case_study_url TEXT,
    testimonial TEXT,
    logo_approved BOOLEAN DEFAULT false,
    
    -- Import metadata
    source TEXT NOT NULL,  -- 'hubspot', 'pipedrive', 'csv', 'manual'
    external_id TEXT,      -- ID in source system
    imported_at TIMESTAMPTZ DEFAULT NOW(),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE (client_id, domain)
);

-- Suppression list (domain-level blocking)
CREATE TABLE suppression_list (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    
    -- What to block
    domain TEXT,
    email TEXT,
    company_name TEXT,
    
    -- Why suppressed
    reason TEXT NOT NULL,  -- 'existing_customer', 'competitor', 'do_not_contact', 'bounced', 'unsubscribed'
    
    -- Reference
    source TEXT,  -- 'crm_import', 'csv_import', 'manual', 'bounce', 'unsubscribe'
    customer_id UUID REFERENCES client_customers(id),
    notes TEXT,
    expires_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE (client_id, domain)
);

-- Platform-wide buyer signals (anonymized, no client reference)
CREATE TABLE platform_buyer_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Company identification
    domain TEXT NOT NULL UNIQUE,
    company_name TEXT,
    industry TEXT,
    employee_count_range TEXT,
    
    -- Aggregated signals
    times_bought INTEGER DEFAULT 1,
    total_value DECIMAL(12,2),
    avg_deal_value DECIMAL(12,2),
    services_bought TEXT[],
    
    -- Scoring
    buyer_score INTEGER DEFAULT 50,  -- 0-100
    
    -- Timestamps
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_converted_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_customers_client ON client_customers(client_id);
CREATE INDEX idx_customers_domain ON client_customers(domain);
CREATE INDEX idx_suppression_client ON suppression_list(client_id);
CREATE INDEX idx_suppression_domain ON suppression_list(domain);
CREATE INDEX idx_suppression_email ON suppression_list(email);
CREATE INDEX idx_buyer_signals_domain ON platform_buyer_signals(domain);
CREATE INDEX idx_buyer_signals_score ON platform_buyer_signals(buyer_score DESC);

-- RLS
ALTER TABLE client_customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE suppression_list ENABLE ROW LEVEL SECURITY;
-- platform_buyer_signals has no RLS (anonymized, platform-wide)

CREATE POLICY "Clients can manage own customers"
    ON client_customers FOR ALL
    USING (client_id IN (SELECT id FROM clients WHERE user_id = auth.uid()));

CREATE POLICY "Clients can manage own suppression list"
    ON suppression_list FOR ALL
    USING (client_id IN (SELECT id FROM clients WHERE user_id = auth.uid()));
```

---

## Test Mode Implementation

### Settings Addition

```python
# src/config/settings.py

class Settings(BaseSettings):
    # ... existing settings ...
    
    # Test Mode - redirects all outbound to test recipients
    TEST_MODE: bool = False
    TEST_EMAIL_RECIPIENT: str = ""
    TEST_SMS_RECIPIENT: str = ""
    TEST_VOICE_RECIPIENT: str = ""
    TEST_LINKEDIN_RECIPIENT: str = ""
    
    # Safety limits
    DAILY_EMAIL_LIMIT: int = 1000  # Per client
    TEST_MODE_DAILY_LIMIT: int = 10  # When TEST_MODE=true
```

### Engine Updates Pattern

```python
# src/engines/email.py

async def send_email(self, lead: Lead, content: EmailContent) -> SendResult:
    recipient = lead.email
    
    # Test mode redirect
    if settings.TEST_MODE and settings.TEST_EMAIL_RECIPIENT:
        original_recipient = recipient
        recipient = settings.TEST_EMAIL_RECIPIENT
        logger.info(f"TEST MODE: Redirecting email from {original_recipient} to {recipient}")
        
        # Add test mode header to content
        content.body = f"[TEST MODE - Originally to: {original_recipient}]\n\n{content.body}"
    
    # Check daily limit
    if settings.TEST_MODE:
        sent_today = await self.get_sent_count_today(lead.campaign.client_id)
        if sent_today >= settings.TEST_MODE_DAILY_LIMIT:
            return SendResult(sent=False, reason="test_mode_daily_limit_reached")
    
    # Send via Salesforge
    # ... rest of implementation
```

Apply same pattern to:
- `src/engines/sms.py`
- `src/engines/voice.py`
- `src/engines/linkedin.py`

---

## OAuth Flow Implementation

### HubSpot OAuth

```python
# src/services/crm_oauth_service.py

class CRMOAuthService:
    
    HUBSPOT_AUTH_URL = "https://app.hubspot.com/oauth/authorize"
    HUBSPOT_TOKEN_URL = "https://api.hubapi.com/oauth/v1/token"
    HUBSPOT_API_URL = "https://api.hubapi.com"
    
    def get_hubspot_auth_url(self, client_id: UUID, redirect_uri: str) -> str:
        """Generate HubSpot OAuth URL."""
        params = {
            "client_id": settings.HUBSPOT_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "scope": "crm.objects.contacts.read crm.objects.deals.read oauth",
            "state": str(client_id),  # Pass client_id through OAuth flow
        }
        return f"{self.HUBSPOT_AUTH_URL}?{urlencode(params)}"
    
    async def hubspot_exchange_code(self, code: str, redirect_uri: str) -> dict:
        """Exchange authorization code for tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.HUBSPOT_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "client_id": settings.HUBSPOT_CLIENT_ID,
                    "client_secret": settings.HUBSPOT_CLIENT_SECRET,
                    "redirect_uri": redirect_uri,
                    "code": code,
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def hubspot_extract_profile(self, access_token: str) -> dict:
        """Extract user profile from HubSpot."""
        async with httpx.AsyncClient() as client:
            # Get owner info
            response = await client.get(
                f"{self.HUBSPOT_API_URL}/crm/v3/owners",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            owners = response.json().get("results", [])
            
            if owners:
                owner = owners[0]
                return {
                    "name": f"{owner.get('firstName', '')} {owner.get('lastName', '')}".strip(),
                    "email": owner.get("email"),
                    "phone": owner.get("phone"),
                    "company": owner.get("teams", [{}])[0].get("name") if owner.get("teams") else None,
                }
            return {}
    
    async def hubspot_extract_customers(self, access_token: str) -> list:
        """Extract closed-won deals from HubSpot."""
        customers = []
        async with httpx.AsyncClient() as client:
            # Get closed-won deals
            response = await client.post(
                f"{self.HUBSPOT_API_URL}/crm/v3/objects/deals/search",
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "filterGroups": [{
                        "filters": [{
                            "propertyName": "dealstage",
                            "operator": "EQ",
                            "value": "closedwon"
                        }]
                    }],
                    "properties": ["dealname", "amount", "closedate", "hs_object_id"],
                    "limit": 100
                }
            )
            deals = response.json().get("results", [])
            
            for deal in deals:
                # Get associated company
                assoc_response = await client.get(
                    f"{self.HUBSPOT_API_URL}/crm/v3/objects/deals/{deal['id']}/associations/companies",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                companies = assoc_response.json().get("results", [])
                
                if companies:
                    company_id = companies[0]["id"]
                    company_response = await client.get(
                        f"{self.HUBSPOT_API_URL}/crm/v3/objects/companies/{company_id}",
                        headers={"Authorization": f"Bearer {access_token}"},
                        params={"properties": "name,domain,industry,numberofemployees"}
                    )
                    company = company_response.json().get("properties", {})
                    
                    customers.append({
                        "company_name": company.get("name"),
                        "domain": company.get("domain"),
                        "industry": company.get("industry"),
                        "employee_count": company.get("numberofemployees"),
                        "deal_value": deal.get("properties", {}).get("amount"),
                        "closed_date": deal.get("properties", {}).get("closedate"),
                    })
        
        return customers
```

### Pipedrive OAuth (Similar Pattern)

```python
    PIPEDRIVE_AUTH_URL = "https://oauth.pipedrive.com/oauth/authorize"
    PIPEDRIVE_TOKEN_URL = "https://oauth.pipedrive.com/oauth/token"
    
    def get_pipedrive_auth_url(self, client_id: UUID, redirect_uri: str) -> str:
        params = {
            "client_id": settings.PIPEDRIVE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "state": str(client_id),
        }
        return f"{self.PIPEDRIVE_AUTH_URL}?{urlencode(params)}"
    
    # ... similar exchange_code, extract_profile, extract_customers methods
```

---

## Webhook Push Implementation

```python
# src/services/webhook_push_service.py

class WebhookPushService:
    
    async def push_meeting_booked(
        self,
        client_id: UUID,
        lead: Lead,
        meeting: Meeting
    ) -> WebhookPushResult:
        """Push meeting booking to client's webhook."""
        
        # Get webhook config
        config = await self.get_config(client_id)
        if not config or not config.is_active:
            return WebhookPushResult(skipped=True, reason="No webhook configured")
        
        if not config.send_meeting_booked:
            return WebhookPushResult(skipped=True, reason="Meeting notifications disabled")
        
        # Build payload
        payload = {
            "event": "meeting_booked",
            "timestamp": datetime.utcnow().isoformat(),
            "lead": {
                "name": lead.full_name,
                "email": lead.email,
                "phone": lead.phone,
                "company": lead.organization_name,
                "title": lead.title,
                "linkedin_url": lead.linkedin_url,
            },
            "meeting": {
                "id": str(meeting.id),
                "scheduled_at": meeting.scheduled_at.isoformat(),
                "duration_minutes": meeting.duration_minutes,
                "meeting_type": meeting.meeting_type,
                "meeting_link": meeting.meeting_link,
            },
            "campaign": {
                "id": str(lead.campaign_id),
                "name": lead.campaign.name,
            }
        }
        
        # Send webhook
        try:
            headers = {"Content-Type": "application/json"}
            if config.auth_header:
                headers["Authorization"] = config.auth_header
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    config.webhook_url,
                    json=payload,
                    headers=headers
                )
            
            # Log result
            await self.log_push(
                client_id=client_id,
                event_type="meeting_booked",
                lead_id=lead.id,
                meeting_id=meeting.id,
                request_url=config.webhook_url,
                request_payload=payload,
                response_status=response.status_code,
                response_body=response.text[:1000],
                status="success" if response.is_success else "failed",
                error=None if response.is_success else f"HTTP {response.status_code}"
            )
            
            if response.is_success:
                config.last_push_at = datetime.utcnow()
                config.consecutive_failures = 0
            else:
                config.consecutive_failures += 1
                config.last_error = f"HTTP {response.status_code}"
            
            await self.db.commit()
            
            return WebhookPushResult(
                success=response.is_success,
                status_code=response.status_code
            )
            
        except Exception as e:
            await self.log_push(
                client_id=client_id,
                event_type="meeting_booked",
                lead_id=lead.id,
                meeting_id=meeting.id,
                request_url=config.webhook_url,
                request_payload=payload,
                status="failed",
                error=str(e)
            )
            
            config.consecutive_failures += 1
            config.last_error = str(e)
            await self.db.commit()
            
            return WebhookPushResult(success=False, error=str(e))
```

---

## Onboarding Flow Updates

### New Onboarding Pages

```
frontend/app/onboarding/
├── page.tsx                    # Entry point - redirects to step 1
├── connect-crm/
│   └── page.tsx               # Step 1: Connect CRM (OAuth buttons)
├── profile/
│   └── page.tsx               # Step 2: Confirm sender profile
├── customers/
│   └── page.tsx               # Step 3: Import customers (suppression)
├── website/
│   └── page.tsx               # Step 4: Website URL for ICP
├── icp-review/
│   └── page.tsx               # Step 5: Review ICP
├── webhook/
│   └── page.tsx               # Step 6: Webhook URL (optional)
└── complete/
    └── page.tsx               # Done - redirect to dashboard
```

### Step 1: Connect CRM

```typescript
// frontend/app/onboarding/connect-crm/page.tsx

export default function ConnectCRM() {
  const handleHubSpot = () => {
    window.location.href = '/api/oauth/hubspot/authorize'
  }
  
  const handlePipedrive = () => {
    window.location.href = '/api/oauth/pipedrive/authorize'
  }
  
  return (
    <OnboardingLayout step={1} totalSteps={6}>
      <h1>Connect Your CRM</h1>
      <p>We'll import your profile and existing customers to get you started faster.</p>
      
      <div className="space-y-4">
        <Button onClick={handleHubSpot} variant="outline" className="w-full">
          <HubSpotIcon /> Connect HubSpot
        </Button>
        
        <Button onClick={handlePipedrive} variant="outline" className="w-full">
          <PipedriveIcon /> Connect Pipedrive
        </Button>
        
        <Button href="/onboarding/profile" variant="ghost" className="w-full">
          Skip - I'll enter manually
        </Button>
      </div>
    </OnboardingLayout>
  )
}
```

---

## Environment Variables Needed

```bash
# Add to .env and Railway

# HubSpot OAuth (register at developers.hubspot.com)
HUBSPOT_CLIENT_ID=
HUBSPOT_CLIENT_SECRET=

# Pipedrive OAuth (register at developers.pipedrive.com)
PIPEDRIVE_CLIENT_ID=
PIPEDRIVE_CLIENT_SECRET=

# Test Mode
TEST_MODE=false
TEST_EMAIL_RECIPIENT=david.stephens@keiracom.com
TEST_SMS_RECIPIENT=+61457543392
TEST_VOICE_RECIPIENT=+61457543392
TEST_LINKEDIN_RECIPIENT=https://www.linkedin.com/in/david-stephens-8847a636a/
TEST_MODE_DAILY_LIMIT=10
```

---

## Progress Tracking

After completing each task, update PROGRESS.md:

```markdown
| CRM-001 | Create OAuth + webhook tables migration | ✅ |
```

And add to session log:

```markdown
### [Date] - Phase 24E Progress

#### Completed:
- **CRM-001**: Created `supabase/migrations/029_crm_integration.sql`
  - client_crm_connections table for OAuth tokens
  - client_webhook_configs table for webhook push
  - webhook_push_log table for audit trail
```

---

## Task Checklist

### Phase 24E: CRM Integration (15h)

- [ ] CRM-001: Create migration 029_crm_integration.sql
- [ ] CRM-002: HubSpot OAuth flow (authorize + callback)
- [ ] CRM-003: HubSpot extract profile
- [ ] CRM-004: HubSpot extract customers
- [ ] CRM-005: Pipedrive OAuth flow
- [ ] CRM-006: Pipedrive extract profile
- [ ] CRM-007: Pipedrive extract customers
- [ ] CRM-008: Build WebhookPushService
- [ ] CRM-009: Integrate webhook push with Closer Engine
- [ ] CRM-010: Onboarding CRM connect UI
- [ ] CRM-011: Settings webhook URL UI
- [ ] CRM-012: Write tests

### Phase 24F: Customer Import (12h)

- [ ] CUST-001: Create migration 030_customer_import.sql
- [ ] CUST-002: Build CustomerImportService
- [ ] CUST-003: CSV upload + column mapping
- [ ] CUST-004: Build SuppressionService
- [ ] CUST-005: Update JIT Validator (check suppression)
- [ ] CUST-006: Update Scout Engine (filter suppressed)
- [ ] CUST-007: Build BuyerSignalService
- [ ] CUST-008: Update Scorer Engine (buyer boost)
- [ ] CUST-009: Customer import + suppression UI
- [ ] CUST-010: Write tests

### Test Mode (3h)

- [ ] TEST-001: Add TEST_MODE config and env vars
- [ ] TEST-002: Update Email Engine with redirect
- [ ] TEST-003: Update SMS Engine with redirect
- [ ] TEST-004: Update Voice Engine with redirect
- [ ] TEST-005: Update LinkedIn Engine with redirect
- [ ] TEST-006: Add daily send limit safeguard

---

## Key Rules

### DO:
- Follow this spec exactly
- Use existing patterns from other services
- Add proper error handling
- Write tests as you build
- Update PROGRESS.md after each task

### DON'T:
- Skip tasks or reorder without reason
- Create tables without RLS policies
- Store OAuth tokens without encryption consideration
- Forget to register routes in main.py
- Forget to export services in __init__.py

---

## Escalation

Stop and ask human if:
- Need HubSpot/Pipedrive OAuth credentials (not registered yet)
- Unclear about OAuth callback URL configuration
- Database migration conflicts with existing schema
- Unsure about encryption approach for tokens

---

## Start Here

1. Check latest migration number: `ls supabase/migrations/ | tail -1`
2. Start with CRM-001: Create migration 029_crm_integration.sql
3. Build through all Phase 24E tasks
4. Then Phase 24F tasks
5. Then Test Mode tasks
6. Report progress after each phase

**Begin with CRM-001!**
