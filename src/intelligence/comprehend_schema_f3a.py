"""Stage 3 — IDENTIFY: comprehension schema — identity and DM identification only.

Stage 3 IDENTIFY fires WITH grounding. Produces identity + DM candidate.
Scoring (affordability, intent, buyer_match) moved to Stage 7 ANALYSE.
ABN is NOT in this schema — ABN comes from Stage 2 VERIFY SERP only.

Pipeline F v2. Ratified: 2026-04-15.
"""
from __future__ import annotations

STAGE3_IDENTIFY_PROMPT = """You are identifying the decision-maker at an Australian SMB who would approve purchasing marketing services. Return ONLY valid JSON.

Your primary objective is finding the PERSON who makes buying decisions at this business — the owner, founder, managing director, CEO, or principal. Every Australian SMB has someone running it. Find them.

You have candidate data from prior search results. Use it as a starting point but DO NOT trust it blindly — verify everything against all publicly available information. Search the business website, LinkedIn, ASIC records, ABN registry, business directories, news articles, and any other public source.

For dm_candidate: you must identify the individual with authority to approve a marketing engagement. This is typically the business owner, founder, managing director, principal, or senior partner. Search thoroughly — their name appears somewhere publicly associated with this business. If you find multiple candidates, select the most senior person with decision-making authority.

{
  "business_name": "customer-facing trading name",
  "location": {
    "street": null,
    "suburb": "...",
    "state": "...",
    "postcode": null
  },
  "industry_category": "...",
  "entity_type_hint": "Australian Private Company | Individual Sole Trader | Other | null",
  "staff_estimate_band": "solo | small(2-5) | medium(6-20) | large(20+) | unknown",
  "is_enterprise_or_chain": false,
  "website_reachable": true,
  "primary_phone": "...",
  "primary_email": "general contact email",
  "social_urls": {
    "linkedin": null,
    "facebook": null,
    "instagram": null
  },
  "dm_candidate": {
    "name": "REQUIRED — the person who runs this business",
    "role": "their title or position",
    "linkedin_url": null
  }
}

Rules:
- dm_candidate.name is the most important field. Do not return null unless you have exhausted all publicly available information about who runs this business.
- dm_candidate.name must be a real person's full name or null. Never return descriptions like "Owner" or "Director" as the name.
- is_enterprise_or_chain: set to true if this is a franchise, national chain, government body, publicly listed company, or enterprise with more than 200 employees.
- NEVER fabricate ABN. ABN is resolved separately.
- NEVER fabricate a LinkedIn URL. Return null if not confirmed via grounding.
- If cannot determine a field, use null. But for dm_candidate.name, try harder before returning null."""
