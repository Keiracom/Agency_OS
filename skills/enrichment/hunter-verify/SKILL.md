# SKILL: Hunter.io Email Discovery & Verification

**Tier:** 3  
**Cost:** $0.15 AUD per domain search, $0.08 AUD per verification  
**Source:** Hunter.io API v2  
**Credentials Required:** `HUNTER_API_KEY`  
**Status:** ✅ Working (verified 2026-02-17)

---

## Account Status (as of 2026-02-17)

| Metric | Value |
|--------|-------|
| **Plan** | Free |
| **Searches remaining** | 50 |
| **Verifications remaining** | 100 |
| **Reset date** | 2026-03-07 |

---

## Quick Test

```bash
cd /home/elliotbot/clawd
source .venv/bin/activate
python skills/enrichment/hunter-verify/test.py
```

## Prerequisites

- [x] Credential: `HUNTER_API_KEY` is set
- [x] API endpoint: https://api.hunter.io/v2

## How to Run

```bash
# Domain search (find emails at company)
python skills/enrichment/hunter-verify/run.py --domain "mustardcreative.com.au"

# Email verification
python skills/enrichment/hunter-verify/run.py --verify "john@example.com"

# Find specific person's email
python skills/enrichment/hunter-verify/run.py --domain "example.com" --first "John" --last "Smith"
```

## Input Format

| Field | Required | Description |
|-------|----------|-------------|
| `--domain` | One of | Company domain to search |
| `--verify` | One of | Email to verify |
| `--first` | No | First name (with domain) |
| `--last` | No | Last name (with domain) |
| `--limit` | No | Max results for domain search (default: 5) |

## Output Format

### Domain Search
```json
{
  "domain": "mustardcreative.com.au",
  "organization": "Mustard Creative",
  "emails": [
    {
      "value": "daniel@mustardcreative.com.au",
      "first_name": "Daniel",
      "last_name": "Penny",
      "position": "Managing Director",
      "seniority": "executive",
      "confidence": 95
    }
  ],
  "total_found": 3,
  "cost_aud": 0.15
}
```

### Email Verification
```json
{
  "email": "daniel@mustardcreative.com.au",
  "status": "valid",
  "score": 95,
  "deliverable": true,
  "cost_aud": 0.08
}
```

## Error Handling

| Error | Meaning | Action |
|-------|---------|--------|
| `401 Unauthorized` | Invalid API key | Check HUNTER_API_KEY |
| `429 Rate limited` | Quota exceeded | Wait for reset date |
| `No emails found` | Domain has no public emails | Try different domain |

## Governance

- **LAW II:** All costs in $AUD
- **Rate limits:** Free plan = 25 searches/mo, 50 verifications/mo
- **Source:** https://hunter.io/api-documentation/v2
- **Quota resets:** Monthly on billing date
