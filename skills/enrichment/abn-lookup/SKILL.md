# SKILL: ABN Lookup Enrichment

**Tier:** 1  
**Cost:** $0.00 AUD (FREE)  
**Source:** data.gov.au ABN Lookup API  
**Credentials Required:** `ABN_LOOKUP_GUID`  
**Status:** ✅ Working (verified 2026-02-17)

---

## Quick Test

```bash
cd /home/elliotbot/clawd
source .venv/bin/activate
python skills/enrichment/abn-lookup/test.py
```

## Prerequisites

- [x] Credential: `ABN_LOOKUP_GUID` is set (d894987c-8df1-4daa-a527-04208c677c0b)
- [x] Dependency: `src/integrations/abn_client.py` exists

## How to Run

```bash
# Search by ABN
python skills/enrichment/abn-lookup/run.py --abn "33051775556"

# Search by company name
python skills/enrichment/abn-lookup/run.py --name "Telstra" --state "VIC"
```

## Input Format

| Field | Required | Description |
|-------|----------|-------------|
| `--abn` | One of | 11-digit ABN (spaces ok) |
| `--name` | One of | Company name to search |
| `--state` | No | State code (NSW, VIC, QLD, etc.) |

## Output Format

```json
{
  "found": true,
  "source": "abn_lookup",
  "cost_aud": 0.0,
  "abn": "33 051 775 556",
  "business_name": "TELSTRA CORPORATION LIMITED",
  "trading_name": "TELSTRA",
  "entity_type": "Australian Public Company",
  "state": "VIC",
  "postcode": "3000",
  "gst_registered": true
}
```

## Error Handling

| Error | Meaning | Action |
|-------|---------|--------|
| `No ABN match found` | ABN doesn't exist | Verify ABN format |
| `GUID not recognised` | Invalid API key | Check ABN_LOOKUP_GUID |
| `Connection error` | API unreachable | Retry in 30s |

## Governance

- **LAW II:** All costs in $AUD ($0.00 - FREE)
- **Rate limits:** Reasonable use policy (no hard limits)
- **Source:** https://abr.business.gov.au/Tools/WebServices
- **Registration:** Free at https://abr.business.gov.au/Tools/WebServices
