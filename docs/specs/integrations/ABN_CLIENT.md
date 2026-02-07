# ABN Lookup Integration

**File:** `src/integrations/abn_client.py`  
**Purpose:** Australian Business Number lookup (Tier 1 of SIEGE Waterfall)  
**Phase:** SIEGE (System Overhaul)  
**API Docs:** https://abr.business.gov.au/Documentation/WebServiceResponse

---

## Overview

ABN Lookup provides **FREE** access to the Australian Business Register (ABR). As Tier 1 of the SIEGE Waterfall, it runs first for all leads and provides foundational business data at zero cost.

---

## Capabilities

- ABN (Australian Business Number) lookup
- ACN (Australian Company Number) for companies
- Business/Entity Name verification
- Trading Names (deprecated post-2012)
- Business Names (ASIC registered)
- State/Territory location
- Postcode
- GST registration status
- Entity type (Company, Sole Trader, Trust, etc.)
- ABN status (Active/Cancelled)

---

## API Endpoints

**Base URL:** `https://abr.business.gov.au/abrxmlsearch/AbrXmlSearch.asmx`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `SearchByABN` | SOAP | Lookup by ABN |
| `SearchByName` | SOAP | Lookup by business name |
| `ABRSearchByNameSimpleProtocol` | GET | Simple name search (REST-like) |

**Note:** API uses SOAP/XML. The client handles conversion to/from Python dicts.

---

## Cost Per Operation ($AUD)

| Operation | Cost |
|-----------|------|
| Any ABN lookup | **$0.00 AUD** |
| Name search | **$0.00 AUD** |

**100% FREE** with GUID registration.

---

## Rate Limits

No hard rate limits published. API operates under "reasonable use policy."

Recommended: Max 10 requests/second to avoid throttling.

---

## Error Handling

```python
from src.integrations.abn_client import ABNClient, ABNLookupError

client = ABNClient()

try:
    result = await client.lookup_abn("12345678901")
except ABNLookupError as e:
    if "invalid ABN" in str(e):
        # ABN format invalid
        pass
    elif "not found" in str(e):
        # ABN doesn't exist
        pass
    else:
        # API error
        logger.error(f"ABN lookup failed: {e}")
```

---

## Usage Pattern

```python
from src.integrations.abn_client import ABNClient

client = ABNClient()

# Lookup by ABN
result = await client.lookup_abn("12 345 678 901")  # Spaces OK
print(f"Business: {result.entity_name}")
print(f"Status: {result.abn_status}")
print(f"GST: {'Registered' if result.gst_registered else 'Not Registered'}")
print(f"Entity Type: {result.entity_type}")
print(f"Location: {result.state}, {result.postcode}")

# Search by name
results = await client.search_by_name(
    name="Acme",
    state="NSW",
    postcode="2000",
)
for business in results:
    print(f"{business.abn}: {business.entity_name}")
```

---

## Response Structure

```python
@dataclass
class ABNResult:
    abn: str
    acn: str | None = None
    entity_name: str | None = None
    trading_name: str | None = None  # Deprecated
    business_names: list[str] = field(default_factory=list)
    entity_type: str | None = None  # "Company", "Sole Trader", etc.
    entity_type_code: str | None = None  # "PRV", "IND", etc.
    state: str | None = None
    postcode: str | None = None
    abn_status: str = "Unknown"  # "Active", "Cancelled"
    gst_registered: bool = False
    gst_from_date: str | None = None
    last_updated: str | None = None
    cost_aud: float = 0.0  # Always 0
```

---

## Entity Type Codes

| Code | Entity Type |
|------|-------------|
| IND | Individual/Sole Trader |
| PRV | Australian Private Company |
| PUB | Australian Public Company |
| TRT | Trust |
| PTR | Partnership |
| SGE | State Government Entity |
| CGE | Commonwealth Government Entity |
| LGE | Local Government Entity |
| COP | Co-operative |
| SUP | Superannuation Fund |

---

## State Codes

```python
STATE_CODES = {
    "nsw": "NSW", "new south wales": "NSW",
    "vic": "VIC", "victoria": "VIC",
    "qld": "QLD", "queensland": "QLD",
    "wa": "WA", "western australia": "WA",
    "sa": "SA", "south australia": "SA",
    "tas": "TAS", "tasmania": "TAS",
    "act": "ACT", "australian capital territory": "ACT",
    "nt": "NT", "northern territory": "NT",
}
```

---

## Environment Variables

```bash
# Required - Register at https://abr.business.gov.au/RegisterForWebServices.aspx
ABN_GUID=your_registered_guid
```

---

## SIEGE Waterfall Integration

As Tier 1, ABN lookup runs first for all Australian leads:

```python
# Always runs (free tier)
abn_result = await abn_client.search_by_name(
    name=lead.company_name,
    state=lead.state,
)

if abn_result:
    lead.abn = abn_result.abn
    lead.entity_type = abn_result.entity_type
    lead.gst_registered = abn_result.gst_registered
```

---

## Dependencies

```python
# Required for XML parsing
pip install xmltodict
```

The client auto-converts SOAP/XML responses to Python dictionaries.
