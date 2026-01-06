# Phase 24F: Customer Import & Platform Intelligence

**Status:** 📋 Planned  
**Priority:** Pre-Launch (suppression critical)  
**Estimate:** 12 hours  
**Tasks:** 10

---

## Purpose

1. **Import existing customers:** From CRM (via OAuth) or CSV upload
2. **Suppression list:** Never contact client's existing customers
3. **Platform buyer signals:** Anonymized intelligence for lead scoring

---

## Architecture

```
IMPORT FLOW:
CRM connected (Phase 24E) OR CSV upload
        ↓
CustomerImportService processes each customer
        ↓
    ┌───────────────────┬────────────────────┐
    ↓                   ↓                    ↓
client_customers   suppression_list   platform_buyer_signals
(private)          (blocks outreach)   (anonymized, platform-wide)


SUPPRESSION CHECK:
JIT Validator (before send)
        ↓
SuppressionService.is_suppressed(domain)
        ↓
    ┌────────────┴────────────┐
    ↓                         ↓
  BLOCKED                   ALLOWED
(skip lead)              (continue send)


BUYER INTELLIGENCE:
Scorer Engine calculating lead score
        ↓
BuyerSignalService.get_score_boost(domain)
        ↓
"buildright.com.au bought agency services 3x"
        ↓
+15 points to lead score
```

---

## Database Schema

### Migration: 030_customer_import.sql

```sql
-- Client's existing customers
CREATE TABLE client_customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    
    company_name TEXT NOT NULL,
    domain TEXT,
    industry TEXT,
    employee_count_range TEXT,
    
    contact_email TEXT,
    contact_name TEXT,
    contact_title TEXT,
    
    status TEXT NOT NULL DEFAULT 'active',
    customer_since DATE,
    churned_at DATE,
    deal_value DECIMAL(12,2),
    
    can_use_as_reference BOOLEAN DEFAULT false,
    case_study_url TEXT,
    testimonial TEXT,
    logo_approved BOOLEAN DEFAULT false,
    
    source TEXT NOT NULL,
    external_id TEXT,
    imported_at TIMESTAMPTZ DEFAULT NOW(),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE (client_id, domain)
);

-- Suppression list (domain-level blocking)
CREATE TABLE suppression_list (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    
    domain TEXT,
    email TEXT,
    company_name TEXT,
    
    reason TEXT NOT NULL,
    source TEXT,
    customer_id UUID REFERENCES client_customers(id),
    notes TEXT,
    expires_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE (client_id, domain)
);

-- Platform-wide buyer signals (anonymized)
CREATE TABLE platform_buyer_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    domain TEXT NOT NULL UNIQUE,
    company_name TEXT,
    industry TEXT,
    employee_count_range TEXT,
    
    times_bought INTEGER DEFAULT 1,
    total_value DECIMAL(12,2),
    avg_deal_value DECIMAL(12,2),
    services_bought TEXT[],
    
    buyer_score INTEGER DEFAULT 50,
    
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_converted_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Tasks

| ID | Task | Est | Status |
|----|------|-----|--------|
| CUST-001 | Create migration 030_customer_import.sql | 1h | ⬜ |
| CUST-002 | Build CustomerImportService | 2h | ⬜ |
| CUST-003 | CSV upload + column mapping | 2h | ⬜ |
| CUST-004 | Build SuppressionService | 1h | ⬜ |
| CUST-005 | Update JIT Validator (check suppression) | 1h | ⬜ |
| CUST-006 | Update Scout Engine (filter suppressed) | 1h | ⬜ |
| CUST-007 | Build BuyerSignalService | 1h | ⬜ |
| CUST-008 | Update Scorer Engine (buyer boost) | 1h | ⬜ |
| CUST-009 | Customer import + suppression UI | 3h | ⬜ |
| CUST-010 | Write tests | 2h | ⬜ |

---

## Files to Create

```
supabase/migrations/030_customer_import.sql
src/services/customer_import_service.py
src/services/suppression_service.py
src/services/buyer_signal_service.py
src/api/routes/customers.py
src/api/routes/suppression.py
frontend/app/onboarding/customers/page.tsx
frontend/components/settings/SuppressionList.tsx
tests/test_services/test_suppression_service.py
tests/test_services/test_buyer_signal_service.py
```

## Files to Modify

```
src/services/jit_validator.py (add suppression check)
src/engines/scout.py (filter suppressed before pool)
src/engines/scorer.py (add buyer signal boost)
src/services/__init__.py (export new services)
src/api/main.py (register new routes)
```

---

## Suppression Reasons

| Reason | Description |
|--------|-------------|
| `existing_customer` | Currently paying customer |
| `past_customer` | Previously was customer |
| `competitor` | Direct competitor |
| `partner` | Business partner |
| `do_not_contact` | Requested no contact |
| `bounced` | Email bounced |
| `unsubscribed` | Opted out |

---

## Buyer Score Calculation

```python
def calculate_buyer_score(signal):
    score = 50  # Base score
    
    # Multiple purchases = strong signal
    if signal.times_bought >= 3:
        score += 30
    elif signal.times_bought >= 2:
        score += 20
    else:
        score += 10
    
    # Multiple service types = diversified buyer
    if len(signal.services_bought) >= 2:
        score += 10
    
    # Higher deal values = budget exists
    if signal.avg_deal_value >= 5000:
        score += 10
    
    return min(score, 100)
```

### Score Boost Conversion

```python
def get_score_boost(domain):
    signal = get_buyer_signal(domain)
    if not signal:
        return 0
    
    # Convert buyer_score (0-100) to boost points (0-15)
    return int(signal.buyer_score * 0.15)
```

---

## CSV Upload Column Mapping

```typescript
interface ColumnMapping {
  company_name: string;    // Required
  domain?: string;
  contact_email?: string;
  contact_name?: string;
  industry?: string;
  deal_value?: string;
}

// Example CSV
// Company,Website,Contact Email,Contact Name,Industry,Deal Size
// BuildRight,buildright.com.au,sarah@buildright.com.au,Sarah Chen,Construction,15000
```

---

## Onboarding Step: Import Customers

```typescript
// frontend/app/onboarding/customers/page.tsx

export default function ImportCustomers() {
  const { crmConnected, customersFound } = useCRMConnection();
  
  return (
    <OnboardingLayout step={3} totalSteps={6}>
      <h1>Import Your Existing Customers</h1>
      <p>We'll make sure we never accidentally contact them.</p>
      
      {crmConnected && customersFound > 0 && (
        <div className="p-4 bg-green-50 rounded-lg">
          <p>Found {customersFound} customers in your CRM!</p>
          <Button>Import All</Button>
        </div>
      )}
      
      <div className="mt-6">
        <p className="text-sm text-gray-600">Or upload a CSV file:</p>
        <CSVUploader onUpload={handleCSV} />
      </div>
      
      <Button variant="ghost" href="/onboarding/website">
        Skip - I'll add them later
      </Button>
    </OnboardingLayout>
  )
}
```

---

## T&Cs Coverage

Add to Terms of Service:

> "Agency OS uses aggregated, anonymized insights from platform activity to improve lead scoring and targeting for all users. This includes patterns such as which industries respond well to outreach and which company types purchase agency services. Your specific customer lists, contact details, and commercial terms are never shared with other users."
