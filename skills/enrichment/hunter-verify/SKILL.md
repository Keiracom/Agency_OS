# Hunter Email Verification Skill

**Purpose:** Domain email verification using Hunter.io API

## Overview

This skill provides automated email verification and domain email discovery using the Hunter.io API. It can verify email addresses, find emails associated with domains, and extract contact information for lead generation and outreach campaigns.

**Plan Details:** Free plan, 50 searches/cycle, resets 2026-03-07

## Usage

```python
from skills.enrichment.hunter_verify.run import verify_domain, find_emails

# Verify domain and find emails
result = await verify_domain("mustardcreative.com.au")

# Find specific email patterns
emails = await find_emails("mustardcreative.com.au", limit=10)
```

## Features

- **Domain Verification:** Check if domain accepts emails
- **Email Discovery:** Find email addresses associated with a domain
- **Email Verification:** Validate specific email addresses
- **Contact Enrichment:** Extract names, positions, and social profiles
- **Confidence Scoring:** Quality scores for discovered emails
- **Rate Limiting:** Built-in respect for API rate limits

## Plan Information

- **Type:** Free Plan
- **Limit:** 50 searches per monthly cycle
- **Reset Date:** 2026-03-07
- **Upgrade:** Available for higher volume needs

## Output Format

```json
{
  "domain": "mustardcreative.com.au",
  "disposable": false,
  "webmail": false,
  "accept_all": false,
  "pattern": "{first}.{last}",
  "organization": "Mustard Creative",
  "emails": [
    {
      "value": "hello@mustardcreative.com.au",
      "type": "generic",
      "confidence": 95,
      "first_name": null,
      "last_name": null,
      "position": null,
      "department": null,
      "verification": {
        "date": "2026-02-17",
        "status": "valid"
      }
    }
  ],
  "sources": [
    {
      "domain": "mustardcreative.com.au",
      "uri": "https://mustardcreative.com.au/contact",
      "extracted_on": "2026-01-15"
    }
  ]
}
```

## Environment Variables

- `HUNTER_API_KEY` - Hunter.io API key (required)

## API Integration

Uses Hunter.io REST API directly for email verification and domain searches.

## Test Case

**Target:** mustardcreative.com.au  
**Expected:** Valid domain with discoverable email patterns and organization details

## Cost & Limits

- **Free Plan:** 50 searches/month
- **Reset:** 2026-03-07
- **Cost per search:** $0 (free plan)
- **Paid plans:** Available for higher volumes