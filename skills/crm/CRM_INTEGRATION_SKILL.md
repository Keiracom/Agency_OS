# SKILL.md — CRM Integration & Customer Intelligence

**Skill:** CRM Push + Customer Import + Platform Intelligence  
**Author:** Dave + Claude  
**Version:** 1.0  
**Created:** January 6, 2026  
**Phases:** 24E, 24F

---

## Purpose

Enable Agency OS to:
1. Push booked meetings to client's CRM (HubSpot, Pipedrive, Close)
2. Import client's existing customers for suppression
3. Aggregate buyer signals across the platform for lead scoring

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           AGENCY OS                                     │
│                                                                         │
│   ┌─────────────┐     ┌──────────────────┐     ┌───────────────────┐   │
│   │   Closer    │────►│  CRMPushService  │────►│  Client's CRM     │   │
│   │   Engine    │     │                  │     │  (HubSpot, etc)   │   │
│   └─────────────┘     └──────────────────┘     └───────────────────┘   │
│         │                                                               │
│         │ Meeting booked                                                │
│         ▼                                                               │
│   ┌─────────────┐                                                       │
│   │   Deals     │     (We track outcomes internally too)               │
│   │   Table     │                                                       │
│   └─────────────┘                                                       │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │                    CUSTOMER IMPORT FLOW                          │  │
│   │                                                                   │  │
│   │   Client's CRM ──► CustomerImportService ──► client_customers    │  │
│   │        or                    │                                    │  │
│   │   CSV Upload  ───────────────┘              suppression_list     │  │
│   │                                              │                    │  │
│   │                                              ▼                    │  │
│   │                              platform_buyer_signals (anonymized)  │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │                    SUPPRESSION CHECK                             │  │
│   │                                                                   │  │
│   │   JIT Validator ──► SuppressionService ──► Block if suppressed   │  │
│   │   Scout Engine  ──► SuppressionService ──► Filter before pool    │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │                    BUYER INTELLIGENCE                            │  │
│   │                                                                   │  │
│   │   Scorer Engine ──► BuyerSignalService ──► Boost if known buyer  │  │
│   └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### Phase 24E Tables

```sql
-- CRM configuration per client
CREATE TABLE client_crm_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    
    -- CRM type
    crm_type TEXT NOT NULL,  -- 'hubspot', 'pipedrive', 'close'
    
    -- Authentication (encrypt at rest)
    api_key TEXT,                    -- Pipedrive, Close
    oauth_access_token TEXT,         -- HubSpot
    oauth_refresh_token TEXT,        -- HubSpot
    oauth_expires_at TIMESTAMPTZ,    -- HubSpot
    
    -- Configuration
    pipeline_id TEXT,                -- Which pipeline for new deals
    stage_id TEXT,                   -- Which stage for "meeting booked"
    owner_id TEXT,                   -- Default deal owner
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    last_push_at TIMESTAMPTZ,
    last_error TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE (client_id)
);

-- Audit log for CRM pushes
CREATE TABLE crm_push_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id),
    
    -- What we pushed
    operation TEXT NOT NULL,  -- 'create_contact', 'create_deal'
    
    -- Our references
    lead_id UUID REFERENCES leads(id),
    meeting_id UUID REFERENCES meetings(id),
    
    -- Their references
    crm_contact_id TEXT,
    crm_deal_id TEXT,
    
    -- Request/Response (for debugging)
    request_payload JSONB,
    response_payload JSONB,
    
    -- Status
    status TEXT NOT NULL,  -- 'success', 'failed'
    error TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Phase 24F Tables

```sql
-- Client's existing customers
CREATE TABLE client_customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    
    -- Company identification
    company_name TEXT NOT NULL,
    domain TEXT,                     -- Primary matching key
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
    source TEXT NOT NULL,            -- 'hubspot', 'pipedrive', 'csv', 'manual'
    crm_id TEXT,
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
    domain TEXT,                     -- Primary (blocks entire company)
    email TEXT,                      -- Specific email override
    company_name TEXT,               -- Fuzzy match fallback
    
    -- Why suppressed
    reason TEXT NOT NULL,            -- 'existing_customer', 'competitor', 'do_not_contact', etc.
    
    -- Reference
    source TEXT,                     -- 'crm_import', 'csv_import', 'manual', 'bounce'
    customer_id UUID REFERENCES client_customers(id),
    
    -- Metadata
    notes TEXT,
    expires_at TIMESTAMPTZ,          -- Optional expiry
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE (client_id, domain)
);

-- Platform-wide buyer intelligence (anonymized)
CREATE TABLE platform_buyer_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Company identification (NO client reference)
    domain TEXT NOT NULL UNIQUE,
    company_name TEXT,
    industry TEXT,
    employee_count_range TEXT,
    
    -- Aggregated signals
    times_bought INTEGER DEFAULT 1,
    total_value DECIMAL(12,2),
    avg_deal_value DECIMAL(12,2),
    services_bought TEXT[],          -- ['seo', 'web_design', 'ppc']
    
    -- For lead scoring
    buyer_score INTEGER DEFAULT 50,  -- 0-100
    
    -- Timestamps
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_converted_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Service Implementations

### CRMPushService (Phase 24E)

```python
class CRMPushService:
    """
    One-way push: Agency OS → Client's CRM
    Triggered when: Meeting is booked
    """
    
    async def push_meeting_booked(
        self,
        client_id: UUID,
        lead: Lead,
        meeting: Meeting
    ) -> CRMPushResult:
        """Main entry point - called by Closer Engine."""
        
        # 1. Get CRM config
        config = await self.get_config(client_id)
        if not config or not config.is_active:
            return CRMPushResult(skipped=True, reason="No CRM configured")
        
        try:
            # 2. Find or create contact
            contact_id = await self.find_or_create_contact(config, lead)
            
            # 3. Create deal
            deal_id = await self.create_deal(config, lead, meeting, contact_id)
            
            # 4. Log success
            await self.log_push(
                client_id=client_id,
                operation="create_deal",
                lead_id=lead.id,
                meeting_id=meeting.id,
                crm_contact_id=contact_id,
                crm_deal_id=deal_id,
                status="success"
            )
            
            return CRMPushResult(success=True, crm_deal_id=deal_id)
            
        except Exception as e:
            # Log failure but don't break the meeting flow
            await self.log_push(
                client_id=client_id,
                operation="create_deal",
                lead_id=lead.id,
                meeting_id=meeting.id,
                status="failed",
                error=str(e)
            )
            return CRMPushResult(success=False, error=str(e))
    
    async def find_or_create_contact(self, config, lead) -> str:
        """Route to CRM-specific implementation."""
        if config.crm_type == "hubspot":
            return await self._hubspot_find_or_create_contact(config, lead)
        elif config.crm_type == "pipedrive":
            return await self._pipedrive_find_or_create_person(config, lead)
        elif config.crm_type == "close":
            return await self._close_find_or_create_lead(config, lead)
    
    async def create_deal(self, config, lead, meeting, contact_id) -> str:
        """Route to CRM-specific implementation."""
        deal_name = f"{lead.organization_name} - Agency OS"
        
        if config.crm_type == "hubspot":
            return await self._hubspot_create_deal(config, deal_name, contact_id, meeting)
        elif config.crm_type == "pipedrive":
            return await self._pipedrive_create_deal(config, deal_name, contact_id, meeting)
        elif config.crm_type == "close":
            return await self._close_create_opportunity(config, deal_name, contact_id, meeting)
```

### CustomerImportService (Phase 24F)

```python
class CustomerImportService:
    """
    Import client's existing customers from CRM or CSV.
    Populates: client_customers, suppression_list, platform_buyer_signals
    """
    
    async def import_from_crm(self, client_id: UUID) -> ImportResult:
        """Pull closed-won deals from client's CRM."""
        
        crm_config = await self.crm_service.get_config(client_id)
        if not crm_config:
            raise NoCRMConnectedError()
        
        # Fetch won deals
        if crm_config.crm_type == "hubspot":
            customers = await self._fetch_hubspot_won_deals(crm_config)
        elif crm_config.crm_type == "pipedrive":
            customers = await self._fetch_pipedrive_won_deals(crm_config)
        elif crm_config.crm_type == "close":
            customers = await self._fetch_close_won_opps(crm_config)
        
        # Process each customer
        imported = 0
        for customer in customers:
            await self._process_customer(client_id, customer)
            imported += 1
        
        return ImportResult(imported=imported, source=crm_config.crm_type)
    
    async def import_from_csv(
        self,
        client_id: UUID,
        file: UploadFile,
        column_mapping: dict
    ) -> ImportResult:
        """Import from CSV upload."""
        
        df = pd.read_csv(file.file)
        imported = 0
        
        for _, row in df.iterrows():
            email = row.get(column_mapping.get("email"))
            domain = extract_domain(email) if email else row.get(column_mapping.get("domain"))
            
            if not domain and not email:
                continue
            
            customer = CustomerData(
                company_name=row.get(column_mapping.get("company_name"), domain),
                domain=domain,
                contact_email=email,
                contact_name=row.get(column_mapping.get("contact_name")),
                industry=row.get(column_mapping.get("industry")),
                deal_value=row.get(column_mapping.get("deal_value")),
                status="active"
            )
            
            await self._process_customer(client_id, customer)
            imported += 1
        
        return ImportResult(imported=imported, source="csv")
    
    async def _process_customer(self, client_id: UUID, customer: CustomerData):
        """
        Process a single customer:
        1. Upsert to client_customers
        2. Add to suppression_list
        3. Update platform_buyer_signals
        """
        
        client = await self.get_client(client_id)
        
        # 1. Save customer record
        db_customer = await self._upsert_customer(client_id, customer)
        
        # 2. Add to suppression list
        await self.suppression_service.add(
            client_id=client_id,
            domain=customer.domain,
            reason="existing_customer",
            source="crm_import",
            customer_id=db_customer.id
        )
        
        # 3. Update platform buyer signals (anonymized)
        await self.buyer_signal_service.update_signal(
            domain=customer.domain,
            company_name=customer.company_name,
            industry=customer.industry,
            deal_value=customer.deal_value,
            service_type=client.primary_service
        )
```

### SuppressionService (Phase 24F)

```python
class SuppressionService:
    """
    Check and manage suppression list.
    Called by: JIT Validator, Scout Engine
    """
    
    async def is_suppressed(
        self,
        client_id: UUID,
        email: str = None,
        domain: str = None
    ) -> Optional[SuppressionReason]:
        """Check if email/domain is suppressed for this client."""
        
        # Extract domain from email if not provided
        if email and not domain:
            domain = extract_domain(email)
        
        # Check domain-level suppression
        if domain:
            suppression = await self.db.query(SuppressionList).filter(
                SuppressionList.client_id == client_id,
                SuppressionList.domain == domain.lower()
            ).first()
            
            if suppression:
                return SuppressionReason(
                    suppressed=True,
                    reason=suppression.reason,
                    details=f"Domain {domain} is suppressed: {suppression.reason}"
                )
        
        # Check email-level suppression
        if email:
            suppression = await self.db.query(SuppressionList).filter(
                SuppressionList.client_id == client_id,
                SuppressionList.email == email.lower()
            ).first()
            
            if suppression:
                return SuppressionReason(
                    suppressed=True,
                    reason=suppression.reason,
                    details=f"Email {email} is suppressed: {suppression.reason}"
                )
        
        return None
    
    async def add(
        self,
        client_id: UUID,
        domain: str = None,
        email: str = None,
        reason: str = "manual",
        source: str = "manual",
        notes: str = None,
        customer_id: UUID = None
    ):
        """Add to suppression list."""
        
        suppression = SuppressionList(
            client_id=client_id,
            domain=domain.lower() if domain else None,
            email=email.lower() if email else None,
            reason=reason,
            source=source,
            notes=notes,
            customer_id=customer_id
        )
        
        # Upsert (update if exists)
        await self.db.merge(suppression)
        await self.db.commit()
```

### BuyerSignalService (Phase 24F)

```python
class BuyerSignalService:
    """
    Manage platform-wide buyer intelligence.
    Aggregated, anonymized - no client reference.
    """
    
    async def update_signal(
        self,
        domain: str,
        company_name: str,
        industry: str,
        deal_value: float,
        service_type: str
    ):
        """Update or create buyer signal."""
        
        existing = await self.db.query(PlatformBuyerSignal).filter(
            PlatformBuyerSignal.domain == domain.lower()
        ).first()
        
        if existing:
            # Update aggregates
            existing.times_bought += 1
            existing.total_value = (existing.total_value or 0) + (deal_value or 0)
            existing.avg_deal_value = existing.total_value / existing.times_bought
            
            # Add service type if new
            if service_type and service_type not in (existing.services_bought or []):
                existing.services_bought = (existing.services_bought or []) + [service_type]
            
            existing.last_converted_at = datetime.utcnow()
            existing.buyer_score = self._calculate_score(existing)
            existing.updated_at = datetime.utcnow()
        else:
            # Create new signal
            signal = PlatformBuyerSignal(
                domain=domain.lower(),
                company_name=company_name,
                industry=industry,
                times_bought=1,
                total_value=deal_value,
                avg_deal_value=deal_value,
                services_bought=[service_type] if service_type else [],
                last_converted_at=datetime.utcnow(),
                buyer_score=60  # Default "known buyer" boost
            )
            self.db.add(signal)
        
        await self.db.commit()
    
    async def get_score_boost(self, domain: str) -> int:
        """Get score boost for known buyers. Used by Scorer Engine."""
        
        signal = await self.db.query(PlatformBuyerSignal).filter(
            PlatformBuyerSignal.domain == domain.lower()
        ).first()
        
        if not signal:
            return 0
        
        # Convert buyer_score (0-100) to boost points (0-15)
        return int(signal.buyer_score * 0.15)
    
    def _calculate_score(self, signal: PlatformBuyerSignal) -> int:
        """Calculate buyer score based on signals."""
        
        score = 50  # Base
        
        # Bought multiple times = strong signal
        if signal.times_bought >= 3:
            score += 30
        elif signal.times_bought >= 2:
            score += 20
        else:
            score += 10
        
        # Bought multiple service types = diversified buyer
        if len(signal.services_bought or []) >= 2:
            score += 10
        
        # Higher deal values = budget exists
        if (signal.avg_deal_value or 0) >= 5000:
            score += 10
        
        return min(score, 100)
```

---

## Integration Points

### Closer Engine (Phase 24E)

```python
# src/engines/closer.py

async def handle_meeting_booked(self, lead: Lead, meeting: Meeting):
    """Called when a meeting is confirmed."""
    
    # Existing logic
    await self.update_lead_status(lead, "meeting_booked")
    await self.send_confirmation_email(lead, meeting)
    
    # NEW: Push to CRM
    crm_result = await self.crm_push_service.push_meeting_booked(
        client_id=lead.campaign.client_id,
        lead=lead,
        meeting=meeting
    )
    
    if crm_result.success:
        logger.info(f"Pushed to CRM: deal_id={crm_result.crm_deal_id}")
    elif crm_result.error:
        logger.warning(f"CRM push failed: {crm_result.error}")
    # Don't fail the meeting if CRM push fails
```

### JIT Validator (Phase 24F)

```python
# src/services/jit_validator.py

async def validate(self, lead_pool_id: UUID, client_id: UUID, channel: str):
    """Pre-send validation - includes suppression check."""
    
    pool_lead = await self.get_pool_lead(lead_pool_id)
    
    # ... existing checks ...
    
    # NEW: Check suppression list
    suppression = await self.suppression_service.is_suppressed(
        client_id=client_id,
        email=pool_lead.email,
        domain=extract_domain(pool_lead.email)
    )
    
    if suppression:
        return ValidationResult(
            valid=False,
            reason=f"suppressed_{suppression.reason}",
            details=suppression.details
        )
    
    # ... rest of validation ...
```

### Scout Engine (Phase 24F)

```python
# src/engines/scout.py

async def filter_leads(self, leads: List[Lead], client_id: UUID) -> List[Lead]:
    """Filter leads before adding to pool - remove suppressed."""
    
    filtered = []
    for lead in leads:
        suppression = await self.suppression_service.is_suppressed(
            client_id=client_id,
            email=lead.email
        )
        
        if not suppression:
            filtered.append(lead)
        else:
            logger.info(f"Filtered suppressed lead: {lead.email} ({suppression.reason})")
    
    return filtered
```

### Scorer Engine (Phase 24F)

```python
# src/engines/scorer.py

async def calculate_score(self, lead: Lead) -> int:
    """Calculate lead score - includes buyer signal boost."""
    
    score = 0
    
    # ... existing scoring factors ...
    
    # NEW: Buyer signal boost
    domain = extract_domain(lead.email)
    buyer_boost = await self.buyer_signal_service.get_score_boost(domain)
    score += buyer_boost
    
    if buyer_boost > 0:
        lead.score_factors["known_buyer"] = buyer_boost
    
    return min(score, 100)
```

---

## API Endpoints

### Phase 24E: CRM

```python
# CRM Configuration
GET    /api/v1/crm/config               # Get current CRM config
POST   /api/v1/crm/connect/hubspot      # Start HubSpot OAuth
GET    /api/v1/crm/callback/hubspot     # OAuth callback
POST   /api/v1/crm/connect/pipedrive    # Connect with API key
POST   /api/v1/crm/connect/close        # Connect with API key
DELETE /api/v1/crm/disconnect           # Disconnect CRM
POST   /api/v1/crm/test                 # Test connection

# CRM Data (for UI dropdowns)
GET    /api/v1/crm/pipelines            # List pipelines
GET    /api/v1/crm/stages/{pipeline_id} # List stages
GET    /api/v1/crm/users                # List users
```

### Phase 24F: Customers & Suppression

```python
# Customer Import
POST   /api/v1/customers/import/crm     # Import from CRM
POST   /api/v1/customers/import/csv     # Upload CSV
GET    /api/v1/customers                # List customers
DELETE /api/v1/customers/{id}           # Remove customer

# Suppression
GET    /api/v1/suppression              # List suppressions
POST   /api/v1/suppression              # Add manual suppression
DELETE /api/v1/suppression/{id}         # Remove suppression

# Social Proof
PUT    /api/v1/customers/{id}/social-proof  # Update social proof settings
GET    /api/v1/customers/referenceable      # Get referenceable customers
```

---

## Frontend Components

### CRM Settings (Phase 24E)

```typescript
// frontend/components/settings/CRMSettings.tsx

export function CRMSettings() {
  const { data: config } = useCRMConfig()
  
  if (!config) {
    return <CRMConnectOptions />
  }
  
  return (
    <div>
      <CRMStatus config={config} />
      <PipelineSelector config={config} />
      <StageSelector config={config} />
      <OwnerSelector config={config} />
      <TestConnectionButton />
      <DisconnectButton />
    </div>
  )
}
```

### Customer Import (Phase 24F)

```typescript
// frontend/components/onboarding/CustomerImport.tsx

export function CustomerImport() {
  const [mode, setMode] = useState<'crm' | 'csv' | null>(null)
  
  return (
    <div>
      <h2>Import Your Existing Clients</h2>
      <p>We'll make sure we never contact your existing customers.</p>
      
      <ImportOptions onSelect={setMode} />
      
      {mode === 'crm' && <CRMImport />}
      {mode === 'csv' && <CSVUpload />}
      
      <SkipButton />
    </div>
  )
}
```

### Suppression Management (Phase 24F)

```typescript
// frontend/components/settings/SuppressionList.tsx

export function SuppressionList() {
  const { data: suppressions } = useSuppressionList()
  
  return (
    <div>
      <h2>Suppression List</h2>
      <p>Companies we'll never contact:</p>
      
      <SuppressionTable data={suppressions} />
      <AddSuppressionForm />
      <ReimportButton />
    </div>
  )
}
```

---

## Testing Checklist

### Phase 24E Tests

- [ ] CRM config saves correctly
- [ ] HubSpot OAuth flow works
- [ ] HubSpot contact creation works
- [ ] HubSpot deal creation works
- [ ] Pipedrive API key auth works
- [ ] Pipedrive person/deal creation works
- [ ] Close API key auth works
- [ ] Close lead/opportunity creation works
- [ ] Push triggers on meeting booked
- [ ] Push failure doesn't break meeting flow
- [ ] Push log records all operations

### Phase 24F Tests

- [ ] Customer import from HubSpot works
- [ ] Customer import from Pipedrive works
- [ ] CSV upload parses correctly
- [ ] Column mapping works
- [ ] Suppression added on import
- [ ] Platform signal updated on import
- [ ] JIT validator blocks suppressed leads
- [ ] Scout filters suppressed leads
- [ ] Scorer applies buyer boost
- [ ] Suppression management UI works
- [ ] Social proof settings save

---

## Common Issues & Fixes

### OAuth Token Expired

```python
# Check and refresh token before API call
if config.oauth_expires_at < datetime.utcnow():
    new_tokens = await self.refresh_oauth_token(config)
    config.oauth_access_token = new_tokens["access_token"]
    config.oauth_expires_at = datetime.utcnow() + timedelta(seconds=new_tokens["expires_in"])
    await self.db.commit()
```

### Domain Extraction Edge Cases

```python
def extract_domain(email: str) -> Optional[str]:
    """Extract domain from email, handling edge cases."""
    if not email or '@' not in email:
        return None
    
    domain = email.split('@')[1].lower().strip()
    
    # Skip common personal email domains
    personal_domains = {'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com'}
    if domain in personal_domains:
        return None
    
    return domain
```

### Rate Limiting

```python
# Add retry logic for CRM API calls
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def hubspot_api_call(self, method: str, url: str, **kwargs):
    response = await self.http.request(method, url, **kwargs)
    if response.status_code == 429:
        raise RateLimitError("HubSpot rate limit exceeded")
    response.raise_for_status()
    return response.json()
```

---

## Success Criteria

### Phase 24E Complete When:
- [ ] All 3 CRMs can be connected
- [ ] Meeting booked → Deal created in CRM
- [ ] OAuth refresh works automatically
- [ ] Push failures logged but don't break flow
- [ ] Settings UI functional

### Phase 24F Complete When:
- [ ] Customers import from CRM and CSV
- [ ] All imports create suppression entries
- [ ] Platform signals aggregate across clients
- [ ] JIT blocks suppressed leads
- [ ] Scout filters suppressed leads
- [ ] Scorer boosts known buyers
- [ ] All UIs functional
