"""
S2b intelligence payload schema.

Sonnet comprehension extracts structured business intelligence from
scraped website content. Output consumed by S3 (ABN), S5 (intent),
S5.5 (vulnerability report), S6 (DM identification), S9 (messages).

Ratified: 2026-04-13. Part of Pipeline E S2 = Scrape + Comprehend.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class IntelligencePayload(BaseModel):
    """Structured business intelligence from Sonnet comprehension."""

    canonical_business_name: str = Field(
        ..., description="The actual business name as a customer would know it. Strip 'Home |', 'Welcome to', 'Pty Ltd'. E.g. 'Affordable Dental' not 'Your Trusted Dental Care Provider - Affordable Dental'."
    )
    services_offered: list[str] = Field(
        default_factory=list, description="Services the business provides. E.g. ['general dentistry', 'cosmetic dentistry', 'dental implants']."
    )
    target_audience: str | None = Field(
        None, description="Who the business serves. E.g. 'residential homeowners', 'small businesses', 'families'."
    )
    primary_location: str | None = Field(
        None, description="City/suburb + state. E.g. 'Newtown, NSW'. Extract from address, footer, or content."
    )
    state: str | None = Field(
        None, description="Australian state abbreviation: NSW, VIC, QLD, SA, WA, TAS, ACT, NT."
    )
    business_type_hint: str | None = Field(
        None, description="One of: sole_trader, small_practice, multi_location, franchise, chain, enterprise, unknown."
    )
    site_quality_signal: str | None = Field(
        None, description="One of: professional, basic, template, minimal, broken."
    )
    team_size_indicator: str | None = Field(
        None, description="One of: solo, small(2-5), medium(6-20), large(20+), unknown."
    )
    has_booking_system: bool = Field(
        False, description="Does the site have online booking/scheduling?"
    )
    has_ecommerce: bool = Field(
        False, description="Does the site sell products online?"
    )
    pain_indicators: list[str] = Field(
        default_factory=list, description="Marketing pain signals. E.g. ['no Google Ads', 'outdated design', 'no social media links']."
    )
    confidence: float = Field(
        0.0, ge=0.0, le=1.0, description="Confidence in the extraction quality. 1.0 = rich content, 0.3 = minimal info."
    )


COMPREHEND_SYSTEM_PROMPT = """You are a business intelligence analyst specialising in Australian SMBs.
Analyse the website content provided and extract structured signals about the business.

Return ONLY valid JSON matching this exact schema:
{
  "canonical_business_name": "The actual business name (strip website title noise)",
  "services_offered": ["service 1", "service 2"],
  "target_audience": "who they serve",
  "primary_location": "suburb, state",
  "state": "NSW/VIC/QLD/SA/WA/TAS/ACT/NT",
  "business_type_hint": "sole_trader|small_practice|multi_location|franchise|chain|enterprise|unknown",
  "site_quality_signal": "professional|basic|template|minimal|broken",
  "team_size_indicator": "solo|small(2-5)|medium(6-20)|large(20+)|unknown",
  "has_booking_system": true/false,
  "has_ecommerce": true/false,
  "pain_indicators": ["signal 1", "signal 2"],
  "confidence": 0.0-1.0
}

Rules:
- canonical_business_name must be the SHORT name a customer would use. "Maddocks" not "Maddocks Lawyers | Legal Services Melbourne".
- services_offered: list actual services mentioned on the site, not categories.
- primary_location: extract from address, footer, Google Maps embed, or content. If multiple locations, pick the first/main one.
- pain_indicators: note missing marketing infrastructure (no analytics, no ads, no social links, outdated design, no SSL, no mobile optimisation).
- confidence: 0.9+ if rich about page + clear services; 0.5 if just homepage with minimal text; 0.3 if barely any content.
- If uncertain about a field, use null. Do not fabricate."""
