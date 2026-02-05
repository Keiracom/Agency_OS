---
name: enrichment-tool
description: Lead and company data enrichment - Apollo for people/company lookup, Prospeo for email finding. ⚠️ PAID APIs - requires permission.
metadata:
  clawdbot:
    emoji: "🔍"
schema:
  type: object
  required: ["action", "provider"]
  properties:
    action:
      type: string
      enum: ["people", "company", "run", "results"]
    provider:
      type: string
      enum: ["apollo", "prospeo"]
---

# Enrichment Tool 🔍

## Purpose (CEO Summary)

This tool connects to paid data enrichment APIs to find contact information and company details for lead generation. It's the "data engine" that powers Agency OS's ability to identify and qualify prospects before outreach.

**When to use:** When you need to find email addresses, phone numbers, company size, or firmographic data for a list of target companies or people.

**When NOT to use:** For casual lookups or testing. Every call costs money.

---

## ⚠️ PAID APIs — Cost Awareness Required

### Apollo (Primary - Lead & Company Data)

| Operation | Cost (USD) | Cost (AUD) | Notes |
|-----------|------------|------------|-------|
| People Search | ~$0.03/credit | ~$0.05/credit | 1 credit per result |
| Company Enrichment | ~$0.05/record | ~$0.08/record | Full firmographics |
| Contact Export | ~$0.10/contact | ~$0.16/contact | Email + phone |
| Bulk Search (1000) | ~$30 | ~$47 | Batch pricing |

**Monthly Budget Impact:** A typical campaign (500 leads) costs ~$50-80 AUD in Apollo credits.

### Prospeo (Secondary - Email Verification)

| Operation | Cost (USD) | Cost (AUD) | Notes |
|-----------|------------|------------|-------|
| Email Finder | ~$0.02/lookup | ~$0.03/lookup | Domain → email |
| Email Verify | ~$0.01/verify | ~$0.015/verify | Validity check |
| Bulk (1000) | ~$15 | ~$23 | Volume discount |

**Exchange Rate Used:** 1 USD = 1.55 AUD (verify current rate for large operations)

---

## Usage

```bash
python3 tools/enrichment_master.py <action> <provider> [options]
```

## Examples

**Conceptual Summary:** These commands query external APIs to retrieve contact/company data. Each call deducts credits from our account.

```bash
# Search people at a company (COSTS ~$0.05 AUD per result)
python3 tools/enrichment_master.py people apollo --domain "company.com"

# Company lookup (COSTS ~$0.08 AUD per record)
python3 tools/enrichment_master.py company apollo --domain "stripe.com"

# Find email via Prospeo (COSTS ~$0.03 AUD per lookup)
python3 tools/enrichment_master.py people prospeo --name "John Smith" --domain "acme.com"
```

---

## Governance Compliance

- **LAW I:** Read this file before first use each session
- **LAW II:** All costs shown in $AUD
- **LAW III:** Always state estimated cost before bulk operations
- **LAW IV:** Conceptual summaries included above

---

## Replaces

- apollo (archived)
- apify (moved to scraping)
