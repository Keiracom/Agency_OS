# Bright Data LinkedIn Skill

**Purpose:** LinkedIn profile data extraction using Bright Data API

## Overview

This skill extracts LinkedIn profile data using Bright Data's LinkedIn dataset API. It can retrieve comprehensive profile information including professional experience, education, skills, and contact details from LinkedIn URLs.

## Usage

```python
from skills.enrichment.brightdata_linkedin.run import linkedin_profile_lookup

# Extract profile data from LinkedIn URL
result = await linkedin_profile_lookup("https://www.linkedin.com/company/mustard-creative/")
```

## Features

- **Profile Extraction:** Full LinkedIn profile data retrieval
- **Company Profiles:** Support for company and personal LinkedIn pages  
- **Structured Data:** Normalized output format for easy processing
- **Rate Limiting:** Built-in request throttling to respect API limits
- **Error Handling:** Robust error handling for network and API issues

## Dataset Information

- **Dataset ID:** gd_l1vikfnt1wgvvqz95w
- **Provider:** Bright Data
- **Coverage:** Global LinkedIn profiles
- **Refresh Rate:** Real-time extraction

## Output Format

```json
{
  "profile_url": "https://www.linkedin.com/company/mustard-creative/",
  "name": "Mustard Creative",
  "headline": "Digital Marketing Agency",
  "location": "Melbourne, Victoria, Australia",
  "industry": "Marketing Services",
  "company_size": "11-50 employees",
  "founded": "2015",
  "website": "https://www.mustardcreative.com.au",
  "specialties": ["Digital Marketing", "Web Development", "Brand Strategy"],
  "description": "Full-service digital marketing agency...",
  "employees_count": 35,
  "follower_count": 1250
}
```

## Environment Variables

- `BRIGHTDATA_API_KEY` - Bright Data API key (required)

## API Integration

Uses Bright Data API directly with the LinkedIn dataset gd_l1vikfnt1wgvvqz95w.

## Test Case

**Target:** Mustard Creative LinkedIn URL  
**Expected:** Valid company profile with complete business details

## Cost

Per-request pricing based on Bright Data LinkedIn dataset rates.