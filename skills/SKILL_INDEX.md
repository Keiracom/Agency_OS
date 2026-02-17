# Skill Index

This directory contains automated skills organized by category.

## Enrichment Skills

### ABN Lookup
**Location:** `skills/enrichment/abn-lookup/`  
**Purpose:** Look up Australian Business Number (ABN) details using the ABN Web Services API  
**Test Case:** Telstra ABN 33051775556  

### Bright Data LinkedIn
**Location:** `skills/enrichment/brightdata-linkedin/`  
**Purpose:** LinkedIn profile data extraction using Bright Data API  
**Dataset:** gd_l1vikfnt1wgvvqz95w  
**Test Case:** Mustard Creative LinkedIn URL  

### Bright Data GMB
**Location:** `skills/enrichment/brightdata-gmb/`  
**Purpose:** Google Maps business search via Bright Data Google Maps SERP API  
**Cost:** $0.0015/request AUD  
**Test Case:** "marketing agency Melbourne"  
**Note:** Replaces the deprecated DIY GMB scraper. See Directive #020a for validation.

### Hunter Email Verification
**Location:** `skills/enrichment/hunter-verify/`  
**Purpose:** Domain email verification using Hunter.io API  
**Plan:** Free plan, 50 searches/cycle, resets 2026-03-07  
**Test Case:** mustardcreative.com.au  

## Skill Structure

Each skill follows the standard pattern:
- `SKILL.md` - Documentation and usage
- `run.py` - Main execution logic
- `test.py` - Test cases and validation
- `.env.example` - Required environment variables