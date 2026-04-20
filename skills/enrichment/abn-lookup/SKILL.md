# SKILL: ABN Lookup Enrichment

**Tier:** 1
**Cost:** $0.00 AUD (FREE)
**Source:** data.gov.au ABN Lookup API
**Credentials Required:** `ABN_LOOKUP_GUID`
**Status:** ✅ Working (verified 2026-02-17)

---

## At-a-Glance

**What:** Verify an Australian Business Number (ABN) against the public ABR register — free, authoritative, used as the T1 check in the enrichment waterfall.

**When to use:**
- T1 gate: confirm a prospect is a real registered AU business before spending money on paid enrichment tiers
- Entity-type classification: determine SMB vs Enterprise vs Public Company vs Government for affordability gate

**When NOT to use:**
- NOT for non-AU prospects — the API only covers Australian registrations
- NOT as an email finder (only legal entity data here)
- NOT without caching — the same ABN lookup repeatedly wastes latency though it's free (rate limits exist)

**Caveats:**
- FREE but rate-limited (~100 req/min soft, documented as "reasonable use")
- Returns stale entity data up to 30 days old — dissolved companies may still show `active=true` briefly
- AU-only: any non-AU prospect returns `{found: false}`
- `entity_type` must be treated as enum (see Input Constraints) — free-text matching has caused affordability-gate bugs historically (the public-company substring-vs-exact-match regression)

**Returns:** `{found: bool, abn: str|null, entity_name: str|null, entity_type: enum, status: enum['Active','Cancelled'], state: str, postcode: str}`. `found: false` when ABN not found or invalid.

## Input Parameter Constraints (poka-yoke)

- `abn: str` — required. Must match `^\d{11}$` after stripping spaces. Reject any other format up-front.
- `business_name: str` — optional alternative to abn. Must be ≤200 chars. Fuzzy-matches ABR; always prefer `abn` when available.

## Response Trimming

PERSIST: `abn, entity_name, entity_type, status, state, postcode, registration_date`. DROP: historical name changes array (rarely used downstream), GST details (separate concern), trading-name aliases (use T1.25 trading-name-chain skill for that).

## Error Handling

| Error | Signal | Category | Action |
|-------|--------|----------|--------|
| Invalid ABN format | client-side reject | caller_error | Strip spaces + regex check before API call. |
| ABN not found | 200 + empty result | miss | Persist `{found: false, reason: not_registered}`. |
| GUID missing/invalid | 401 | config_error | Route to devops-6 — `ABN_LOOKUP_GUID` env. |
| Rate limit | implicit throttle | transient | Exponential backoff, max 3 retries. |
| API down | 5xx or timeout | transient | Retry once after 10s. If still failing, escalate to devops-6; T1 is non-blocking for discovery phase. |

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
