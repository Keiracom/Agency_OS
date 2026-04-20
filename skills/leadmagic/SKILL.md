# SKILL: Leadmagic Email & Mobile Enrichment

**Replaces:** Hunter (T3) + Kaspr (T5)
**Status:** ⚠️ API key present but plan unpurchased — do NOT call until credits available
**Source:** Leadmagic API
**Credentials Required:** `LEADMAGIC_API_KEY`

---

## At-a-Glance (Anthropic tool-doc template — 6-vector hardened)

**What:** Find a person's work email (T3) or mobile (T5) given domain + name or LinkedIn URL. One email lookup = $0.015 AUD. One mobile lookup = $0.077 AUD. Both covered by single LEADMAGIC_API_KEY env var.

**When to use:**
- T3 email finder: after T2 has produced `{first_name, last_name, company_domain}` and we need a verified contact email before outreach
- T5 mobile finder: after T2.5 has captured `linkedin_url` of a decision-maker and we need a mobile for SMS/voice channel
- Credit check (free): before any batch > 20 prospects to confirm budget headroom

**When NOT to use:**
- NOT for bulk email verification of already-known emails — use a dedicated verifier (future)
- NOT for company-wide email pattern discovery — use Hunter's domain-search endpoint instead
- NOT when only a `full_name` string is available without first/last split — the API requires separated names
- NOT during plan-unpurchased window (see Status above); calls return 403 and cost nothing but pollute logs

**Caveats:**
- Rate limit: 10 req/sec hard, 1 req/sec recommended. Exponential backoff on 429, 3 retries max.
- Cost: $0.015/email + $0.077/mobile (AUD). Monthly plan ≈ $155 AUD Essential tier.
- Data staleness: Leadmagic refreshes records on fetch; stale >90d records flagged with `status=stale` (filter out upstream for AU compliance).
- AU-specific: mobiles returned in E.164 with `+61` prefix. Reject any result not matching `^\+61\d{9}$` before persistence — cross-border numbers violate our outreach policy.
- No email verification endpoint — confidence score from find_email is the only reliability signal.

**Returns:**
- Email: `{found: bool, email: str|null, confidence: int (0-100), status: enum['valid','catchall','unknown','invalid'], position: str|null, linkedin_url: str|null}`
- Mobile: `{found: bool, mobile_number: str|null (E.164), mobile_confidence: int, status: enum['verified','unverified','invalid'], first_name, last_name, title, company}`
- Credits: `{email_credits: int, mobile_credits: int, plan: str}`

---

## Input Parameter Constraints (Poka-Yoke)

**Email finder inputs:**
- `first_name: str` — required. Non-empty, ≤40 chars. Reject if contains digits or special chars.
- `last_name: str` — required. Non-empty, ≤40 chars.
- `domain: str` — required. Must match `^([a-z0-9-]+\.)+[a-z]{2,}$` (bare domain, no https://, no trailing slash, lowercase). **AU enforcement:** reject if TLD is not in {.com.au, .net.au, .org.au, .edu.au, .gov.au} unless caller explicitly passes `au_only=False` (default `True`).
- `company: str` — optional. If provided, must be ≤200 chars.

**Mobile finder input:**
- `linkedin_url: str` — required. Must match `^https://(www\.|au\.|)linkedin\.com/in/[a-zA-Z0-9\-_]+/?$`. Reject any other URL shape — the API silently returns 0 matches on malformed input (do not let that reach production).

**Never pass:** raw email addresses, full HTTP URLs with query strings, or unvalidated free-text company names — these produce silent 0-match responses that waste credits and confuse downstream scoring.

---

## Input Examples (covers edge cases)

**T3 normal case:**
```json
{"first_name": "John", "last_name": "Smith", "domain": "acme.com.au"}
```

**T3 with company disambiguation (common-name case):**
```json
{"first_name": "John", "last_name": "Smith", "domain": "acme.com.au", "company": "Acme Consulting Pty Ltd"}
```

**T3 edge — hyphenated name:**
```json
{"first_name": "Mary-Jane", "last_name": "O'Neill", "domain": "smith-partners.com.au"}
```

**T5 normal case:**
```json
{"linkedin_url": "https://linkedin.com/in/johnsmith"}
```

**T5 edge — regional subdomain:**
```json
{"linkedin_url": "https://au.linkedin.com/in/johnsmith-au"}
```

---

## Response Trimming (what to persist, what to drop)

**T3 email response — PERSIST:** `email, confidence, status, linkedin_url` (if present). **DROP:** `position` (stale and low-reliability; re-sourced from T2.5 LinkedIn).

**T5 mobile response — PERSIST:** `mobile_number, mobile_confidence, status, first_name, last_name`. **DROP:** `title, company` (better sourced from T2.5).

Bloated responses waste downstream context. Persist only fields cited in the Siege Waterfall contract.

---

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/email-finder` | POST | Find email for person at domain |
| `/mobile-finder` | POST | Find mobile from LinkedIn URL |
| `/credits` | GET | Check credit balance |

## Email Finder (T3 Replacement)

### Input
```json
{
  "first_name": "John",
  "last_name": "Smith",
  "domain": "acme.com.au",
  "company": "Acme Pty Ltd"  // optional
}
```

### Output
```json
{
  "found": true,
  "email": "john.smith@acme.com.au",
  "confidence": 95,
  "status": "valid",
  "position": "CEO",
  "linkedin_url": "https://linkedin.com/in/johnsmith"
}
```

### Usage
```python
from src.integrations.leadmagic import get_leadmagic_client

client = get_leadmagic_client()
result = await client.find_email("John", "Smith", "acme.com.au")

if result.found:
    print(f"Email: {result.email} (confidence: {result.confidence}%)")
    print(f"Cost: ${result.cost_aud:.3f} AUD")
```

## Mobile Finder (T5 Replacement)

### Input
```json
{
  "linkedin_url": "https://linkedin.com/in/johnsmith"
}
```

### Output
```json
{
  "found": true,
  "mobile_number": "+61412345678",
  "mobile_confidence": 90,
  "status": "verified",
  "first_name": "John",
  "last_name": "Smith",
  "title": "CEO",
  "company": "Acme Pty Ltd"
}
```

### Usage
```python
from src.integrations.leadmagic import get_leadmagic_client

client = get_leadmagic_client()
result = await client.find_mobile("https://linkedin.com/in/johnsmith")

if result.found:
    print(f"Mobile: {result.mobile_number} (confidence: {result.mobile_confidence}%)")
    print(f"Cost: ${result.cost_aud:.3f} AUD")
```

## Credit Check

```python
from src.integrations.leadmagic import get_leadmagic_client

client = get_leadmagic_client()
balance = await client.get_credits()

print(f"Email credits: {balance.email_credits}")
print(f"Mobile credits: {balance.mobile_credits}")
print(f"Plan: {balance.plan}")
```

## Error Handling (Category → Action mapping)

| Error | HTTP Code | Category | Action |
|-------|-----------|----------|--------|
| Invalid request (malformed input) | 400 | caller_error | Validate against Input Parameter Constraints above; do NOT retry. |
| Auth / API key missing | 401 | config_error | Route to devops-6 (env vars missing). |
| Plan not purchased / credits exhausted | 402, 403 | config_error / budget | Escalate to Dave (budget decision). Do NOT keep hitting endpoint — logs pollution. |
| Rate limit | 429 | transient | Wait (exponential backoff: 1s, 2s, 4s) and retry, max 3 attempts. |
| Server error | 5xx | transient | Retry once after 5s. If still failing, escalate to devops-6. |
| `found: false` with 200 | — | miss | Persist `{found: false, reason: no_match}` — not an error, data signal. |

## Rate Limiting

- 1 second delay between requests (conservative)
- Max 10 requests/second (hard cap from API)
- Automatic retry with exponential backoff (3 attempts, 1s → 2s → 4s)

## Integration Points

| File | Usage |
|------|-------|
| `src/integrations/leadmagic.py` | Main client implementation |
| `src/integrations/siege_waterfall.py` | T3 + T5 integration |
| `src/engines/waterfall_verification_worker.py` | Waterfall orchestration |

## Governance

- **LAW II:** All costs logged in AUD
- **LAW XII:** Direct calls to `src/integrations/leadmagic.py` OUTSIDE skill execution are forbidden — use this skill as the interface
- **CEO Directive:** Hunter + Kaspr deprecated, Leadmagic is canonical source
- **WARNING:** Plan unpurchased — do not make live API calls until credits available

## Batch Operations

```python
# Batch email finder
prospects = [
    {"first_name": "John", "last_name": "Smith", "domain": "acme.com.au"},
    {"first_name": "Jane", "last_name": "Doe", "domain": "example.com.au"},
]
results = await client.batch_find_emails(prospects, max_concurrent=5)

# Batch mobile finder
urls = [
    "https://linkedin.com/in/johnsmith",
    "https://linkedin.com/in/janedoe",
]
results = await client.batch_find_mobiles(urls, max_concurrent=5)
```

## Migration Notes

1. **Hunter.io (T3)** → `leadmagic.find_email()`
2. **Kaspr (T5)** → `leadmagic.find_mobile()`
3. **Cost savings:** T3: $0.004/email, T5: $0.373/mobile
4. **No email verification endpoint** — confidence score from find_email is sufficient

---

## Template Checklist (for hardening other skills)

When upgrading other skill SKILL.md files to this standard, ensure each has:

- [ ] **At-a-Glance block** with What / When to use / When NOT to use / Caveats / Returns
- [ ] **Input Parameter Constraints** section with regex patterns, length limits, AU enforcement, poka-yoke rejection rules
- [ ] **Input Examples** with ≥3 cases including at least one edge case (hyphens, subdomains, optional fields)
- [ ] **Response Trimming** section naming which fields to PERSIST vs DROP
- [ ] **Error Handling table** with HTTP code + category + action routing (caller_error / config_error / transient / budget / miss)
- [ ] **LAW XII governance note** — skill is the canonical interface; direct integration calls forbidden
