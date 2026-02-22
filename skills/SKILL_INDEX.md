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

### Leadmagic (Email + Mobile)
**Location:** `skills/leadmagic/`  
**Purpose:** Email finder and mobile enrichment via Leadmagic API  
**Replaces:** Hunter.io (T3) + Kaspr (T5) — CEO Directive: Leadmagic is canonical source  
**Cost:** Email $0.015 AUD/record, Mobile $0.077 AUD/record  
**Note:** API key present but plan unpurchased — do not call until credits available  

## Skill Structure

Each skill follows the standard pattern:
- `SKILL.md` - Documentation and usage
- `run.py` - Main execution logic
- `test.py` - Test cases and validation
- `.env.example` - Required environment variables