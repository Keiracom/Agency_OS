# ABN Lookup Skill

**Purpose:** Look up Australian Business Number (ABN) details using the ABN Web Services API

## Overview

This skill provides automated ABN lookups using the official Australian Business Register (ABR) Web Services API. It can search by ABN number or business name and return comprehensive business details including entity information, GST status, and business names.

## Usage

```python
from skills.enrichment.abn_lookup.run import abn_lookup

# Lookup by ABN
result = await abn_lookup("33051775556")

# Search by business name
results = await abn_search_by_name("Telstra Corporation Limited")
```

## Features

- **ABN Lookup:** Direct ABN number validation and details retrieval
- **Name Search:** Business name search with advanced filtering
- **Entity Filtering:** Filter by entity type (Private, Public, Individual, etc.)
- **Location Filtering:** State and postcode filtering
- **Status Filtering:** Active/inactive ABN filtering

## Output Format

```json
{
  "abn": "33051775556",
  "entity_name": "Telstra Corporation Limited",
  "entity_type": "PUB",
  "entity_type_name": "Public Company",
  "status": "Active",
  "gst_status": "registered",
  "gst_effective_from": "2000-07-01",
  "address": "242 Exhibition Street, Melbourne VIC 3000",
  "state": "VIC",
  "business_names": [],
  "trading_name": null
}
```

## Environment Variables

- `ABN_LOOKUP_GUID` - Authentication GUID from ABN Web Services (required)

## API Integration

Uses `src/integrations/abn_client.py` for API communication with the ABR Web Services.

## Test Case

**Target:** Telstra ABN 33051775556  
**Expected:** Valid business entity with complete details

## Cost

Free API service provided by the Australian Business Register.