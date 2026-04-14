"""F3a comprehension schema — identity, scoring, and preliminary classification.

F3a fires WITH grounding. Produces identity + affordability + intent_preliminary.
ABN is NOT in this schema — ABN comes from F4 SERP only.

Ratified: 2026-04-14. Pipeline F architecture refactor.
"""
from __future__ import annotations

F3A_SYSTEM_PROMPT = """You are analysing an Australian SMB prospect. Return ONLY valid JSON.

Extract identity, scoring, and preliminary classification.

{
  "business_name": "customer-facing trading name",
  "location": {
    "street": null,
    "suburb": "...",
    "state": "NSW",
    "postcode": null
  },
  "industry_category": "...",
  "entity_type_hint": "Australian Private Company | Individual Sole Trader | Other | null",
  "staff_estimate_band": "solo | small(2-5) | medium(6-20) | large(20+) | unknown",
  "website_reachable": true,
  "primary_phone": "...",
  "primary_email": "pattern guess OK",
  "social_urls": {
    "linkedin": null,
    "facebook": null,
    "instagram": null
  },
  "dm_candidate": {
    "name": "...",
    "role": "...",
    "linkedin_url": null
  },
  "affordability_score": 0,
  "affordability_gate": "can_afford | cannot_afford",
  "intent_band_preliminary": "DORMANT | DABBLING | TRYING | STRUGGLING | NOT_TRYING",
  "intent_evidence_preliminary": ["evidence 1", "evidence 2", "evidence 3"],
  "buyer_match_score": 0
}

Rules:
- NEVER fabricate ABN. ABN is resolved separately — do not include it here.
- NEVER fabricate a LinkedIn URL. Return null if not found via grounding.
- affordability_score: 0-10, based on business size, online presence, pricing signals.
- affordability_gate: "can_afford" if score >= 5, else "cannot_afford".
- intent_band_preliminary: based on website quality and organic signals provided.
- buyer_match_score: 0-10, how well this prospect matches a B2B digital marketing agency ICP.
- If cannot determine a field, use null."""
