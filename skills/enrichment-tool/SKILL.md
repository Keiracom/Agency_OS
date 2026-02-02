---
name: enrichment-tool
description: Lead and company data enrichment - Apollo for people/company lookup, Apify for scraping. ⚠️ PAID APIs - requires permission.
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
      enum: ["apollo", "apify"]
---

# Enrichment Tool 🔍

⚠️ **PAID APIs** - Requires explicit permission before use.

## Usage

```bash
python3 tools/enrichment_master.py <action> <provider> [options]
```

## Examples

```bash
# Search people (COSTS MONEY)
python3 tools/enrichment_master.py people apollo --domain "company.com"

# Company lookup (COSTS MONEY)
python3 tools/enrichment_master.py company apollo --domain "stripe.com"
```

## Replaces

- apollo, apify
