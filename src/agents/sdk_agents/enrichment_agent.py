"""
DEPRECATED: FCO-002 (2026-02-05)
This module is deprecated. Use Smart Prompts (src/engines/smart_prompts.py) instead.
SDK enrichment replaced by Siege Waterfall data.
Kept for reference only - do not use in new code.

---
Contract: src/agents/sdk_agents/enrichment_agent.py
Purpose: SDK-powered deep research for Hot leads with signals
Layer: 3 - agents
Imports: models, integrations (sdk_brain, sdk_tools)
Consumers: scout engine

This agent performs deep web research for Hot leads that have priority signals
(recent funding, actively hiring, etc.). It uses web_search and web_fetch tools
to gather current, specific information for hyper-personalization.
"""
from __future__ import annotations

import warnings
warnings.warn("This SDK agent is deprecated. Use Smart Prompts instead.", DeprecationWarning)

import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from src.agents.sdk_agents.sdk_tools import ENRICHMENT_TOOLS
from src.integrations.sdk_brain import SDKBrainResult, create_sdk_brain

logger = logging.getLogger(__name__)


# ============================================
# OUTPUT SCHEMA
# ============================================


class FundingInfo(BaseModel):
    """Recent funding information."""

    amount: str | None = Field(default=None, description="Funding amount (e.g., '$18M')")
    date: str | None = Field(default=None, description="Funding date (YYYY-MM-DD)")
    investors: list[str] = Field(default_factory=list, description="Investor names")
    round: str | None = Field(default=None, description="Funding round (e.g., 'Series B')")


class HiringInfo(BaseModel):
    """Company hiring information."""

    total_open_roles: int = Field(default=0, description="Total open positions")
    sales_roles: int = Field(default=0, description="Sales/SDR positions open")
    key_positions: list[str] = Field(default_factory=list, description="Notable positions hiring")


class NewsItem(BaseModel):
    """Recent news item."""

    headline: str = Field(description="News headline")
    date: str | None = Field(default=None, description="Publication date")
    source: str | None = Field(default=None, description="Source publication")


class CompetitorIntel(BaseModel):
    """Competitor intelligence."""

    main_competitors: list[str] = Field(default_factory=list, description="Main competitor names")
    positioning: str | None = Field(
        default=None, description="How company positions vs competitors"
    )


class EnrichmentOutput(BaseModel):
    """Complete enrichment output from SDK agent."""

    funding: FundingInfo | None = Field(default=None, description="Recent funding details")
    hiring: HiringInfo | None = Field(default=None, description="Current hiring data")
    recent_news: list[NewsItem] = Field(default_factory=list, description="Recent news items")
    pain_points: list[str] = Field(default_factory=list, description="Identified pain points")
    personalization_hooks: list[str] = Field(
        default_factory=list, description="Personalization hooks to use"
    )
    competitor_intel: CompetitorIntel | None = Field(
        default=None, description="Competitor intelligence"
    )
    conversation_starters: list[str] = Field(
        default_factory=list, description="Conversation starters"
    )


# ============================================
# SYSTEM PROMPT
# ============================================


ENRICHMENT_SYSTEM_PROMPT = """You are a B2B sales research specialist. Your job is to research a company and contact person to find specific, current information that will make outreach highly personalized.

You have access to:
- web_search: Search Google for company news, funding, hiring
- web_fetch: Fetch and read webpage content
- linkedin_posts: Fetch recent LinkedIn posts (if URL available)

RESEARCH PRIORITIES:
1. Recent funding announcements (amount, investors, date)
2. Current job openings (especially sales/SDR roles)
3. Recent company news or press releases
4. The contact person's recent LinkedIn activity or interviews
5. Competitor landscape and positioning

RESEARCH PROCESS:
1. Search for "{company_name} funding 2025 2026" to find recent funding
2. Search for "{company_name} careers" or "{company_name} jobs" for hiring
3. Fetch the company's careers page if available
4. Search for "{company_name} news" for recent announcements
5. Search for "{person_name} {company_name}" for any interviews or mentions

OUTPUT FORMAT (JSON):
{
    "funding": {
        "amount": "$X million",
        "date": "YYYY-MM-DD",
        "investors": ["Investor A", "Investor B"],
        "round": "Series X"
    },
    "hiring": {
        "total_open_roles": 10,
        "sales_roles": 3,
        "key_positions": ["SDR", "AE", "Sales Manager"]
    },
    "recent_news": [
        {"headline": "...", "date": "...", "source": "..."}
    ],
    "pain_points": [
        "Scaling sales team post-funding",
        "Lead response time as volume grows"
    ],
    "personalization_hooks": [
        "Congrats on the Series B",
        "Saw you're hiring 3 SDRs"
    ],
    "competitor_intel": {
        "main_competitors": ["Competitor A"],
        "positioning": "..."
    },
    "conversation_starters": [
        "Your recent post about X resonated...",
        "With the funding news..."
    ]
}

IMPORTANT:
- Be SPECIFIC. Use actual numbers, names, dates from your research.
- If you can't find something, OMIT IT rather than making it up.
- Pain points should be INFERRED from hiring, funding, news - not generic.
- Personalization hooks should reference SPECIFIC things you found."""


# ============================================
# ENRICHMENT AGENT
# ============================================


@dataclass
class EnrichmentAgentResult:
    """Result from enrichment agent run."""

    success: bool
    data: EnrichmentOutput | None = None
    raw_data: dict[str, Any] | None = None
    error: str | None = None
    cost_aud: float = 0.0
    turns_used: int = 0
    tool_calls: list[dict] = field(default_factory=list)


async def run_sdk_enrichment(
    lead_data: dict[str, Any],
    client_id: UUID | None = None,
) -> SDKBrainResult:
    """
    Run SDK enrichment for a Hot lead with signals.

    This agent researches the company and contact to find specific,
    current information for hyper-personalization.

    Args:
        lead_data: Dict with lead info (name, company, title, linkedin_url, etc.)
        client_id: Optional client ID for cost tracking

    Returns:
        SDKBrainResult with enrichment data
    """
    # Build research prompt
    company = lead_data.get("company_name") or lead_data.get("organization_name") or "Unknown"
    first_name = lead_data.get("first_name", "")
    last_name = lead_data.get("last_name", "")
    name = f"{first_name} {last_name}".strip() or "Unknown"
    title = lead_data.get("title", "")
    linkedin_url = lead_data.get("linkedin_url", "")
    domain = (
        lead_data.get("company_domain")
        or lead_data.get("organization_domain")
        or lead_data.get("domain", "")
    )

    # Build context with existing data
    existing_data = []
    if lead_data.get("linkedin_headline"):
        existing_data.append(f"LinkedIn headline: {lead_data['linkedin_headline']}")
    if lead_data.get("linkedin_about"):
        existing_data.append(f"LinkedIn about: {lead_data['linkedin_about'][:200]}")
    if lead_data.get("linkedin_recent_posts"):
        existing_data.append(f"Recent posts: {lead_data['linkedin_recent_posts'][:300]}")
    if lead_data.get("company_industry") or lead_data.get("organization_industry"):
        existing_data.append(
            f"Industry: {lead_data.get('company_industry') or lead_data.get('organization_industry')}"
        )
    if lead_data.get("company_employee_count") or lead_data.get("organization_employee_count"):
        existing_data.append(
            f"Company size: {lead_data.get('company_employee_count') or lead_data.get('organization_employee_count')} employees"
        )

    existing_section = (
        "\n".join(f"- {d}" for d in existing_data) if existing_data else "None available"
    )

    user_prompt = f"""Research this company and contact for B2B outreach:

CONTACT:
- Name: {name}
- Title: {title}
- LinkedIn: {linkedin_url if linkedin_url else "Not available"}

COMPANY:
- Name: {company}
- Domain: {domain if domain else "Not available"}
- Industry: {lead_data.get("company_industry") or lead_data.get("organization_industry") or "Unknown"}
- Size: {lead_data.get("company_employee_count") or lead_data.get("organization_employee_count") or "Unknown"} employees

EXISTING DATA (from our enrichment):
{existing_section}

DO THIS:
1. Search for "{company} funding 2025 2026" to find recent funding
2. Search for "{company} careers" or check their website for hiring
3. Search for "{company} news" for recent announcements
4. If you find interesting sources, use web_fetch to get more details
5. Identify pain points based on what you learn

Return structured JSON with your findings. Be specific - use actual data you find."""

    logger.info(f"Starting SDK enrichment for {name} at {company}")

    # Create SDK brain with enrichment config
    brain = create_sdk_brain("enrichment")

    # Run the agent
    result = await brain.run(
        prompt=user_prompt,
        tools=ENRICHMENT_TOOLS,
        output_schema=EnrichmentOutput,
        system=ENRICHMENT_SYSTEM_PROMPT,
    )

    if result.success:
        logger.info(
            f"SDK enrichment succeeded for {name} at {company}",
            extra={
                "cost_aud": result.cost_aud,
                "turns": result.turns_used,
                "tool_calls": len(result.tool_calls),
            },
        )
    else:
        logger.warning(f"SDK enrichment failed for {name} at {company}: {result.error}")

    return result


async def enrich_hot_lead(
    lead_data: dict[str, Any],
    signals: list[str],
    client_id: UUID | None = None,
) -> dict[str, Any] | None:
    """
    Convenience function to enrich a Hot lead.

    Args:
        lead_data: Lead data dict
        signals: Priority signals that triggered SDK enrichment
        client_id: Optional client ID

    Returns:
        Enrichment data dict or None if failed
    """
    result = await run_sdk_enrichment(lead_data, client_id)

    if not result.success:
        return None

    # Convert Pydantic model to dict if needed
    if result.data:
        if isinstance(result.data, EnrichmentOutput):
            return result.data.model_dump()
        elif isinstance(result.data, dict):
            return result.data

    return None
