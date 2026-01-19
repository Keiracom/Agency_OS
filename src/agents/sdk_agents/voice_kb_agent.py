"""
Contract: src/agents/sdk_agents/voice_kb_agent.py
Purpose: SDK-powered voice knowledge base for Hot leads
Layer: 3 - agents
Imports: models, integrations (sdk_brain)
Consumers: voice engine

This agent generates comprehensive voice knowledge bases for AI voice calls
to Hot leads (ALS 85+). The KB enables the voice AI to:

1. Open calls with specific, relevant hooks
2. Handle objections with company-specific responses
3. Navigate conversations intelligently
4. Sound informed and prepared (not robotic)

The KB includes:
- Pronunciation guides for names
- Company context summary
- Opening hooks based on research
- Pain point discussion guides
- Objection response templates
- Topics to avoid
- Competitor intelligence
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from src.integrations.sdk_brain import SDKBrain, SDKBrainResult, create_sdk_brain

logger = logging.getLogger(__name__)


# ============================================
# OUTPUT SCHEMA
# ============================================


class PronunciationGuide(BaseModel):
    """Pronunciation guides for the voice AI."""
    contact_name: str = Field(description="Contact name with phonetic guide if unusual")
    company_name: str = Field(description="Company name with phonetic guide if unusual")
    industry_terms: list[str] = Field(
        default_factory=list,
        description="Industry-specific terms the voice AI should know"
    )


class ObjectionResponse(BaseModel):
    """Response template for specific objection."""
    objection: str = Field(description="The objection type")
    response: str = Field(description="Suggested response")
    follow_up: str | None = Field(default=None, description="Follow-up if response doesn't work")


class ObjectionHandlers(BaseModel):
    """Objection handling templates."""
    not_interested: str = Field(
        default="I understand. What made you say that?",
        description="Response when prospect says they're not interested"
    )
    no_budget: str = Field(
        default="I hear you on budget. When do you typically review vendor budgets?",
        description="Response for budget objections"
    )
    bad_timing: str = Field(
        default="No problem at all. When would be a better time to connect?",
        description="Response for timing objections"
    )
    using_competitor: str = Field(
        default="That's great - what's working well for you with them?",
        description="Response when using competitor"
    )
    need_to_think: str = Field(
        default="Of course. What specific aspects would you like to think through?",
        description="Response for 'need to think about it'"
    )
    send_info: str = Field(
        default="Happy to send over some info. What would be most useful - case studies, pricing, or a product overview?",
        description="Response for 'just send me info'"
    )
    custom_objections: list[ObjectionResponse] = Field(
        default_factory=list,
        description="Custom objection responses based on research"
    )


class CompetitorContext(BaseModel):
    """Competitor intelligence for the call."""
    likely_current_tools: str | None = Field(
        default=None,
        description="What tools they likely use based on job posts, tech stack"
    )
    main_competitors: list[str] = Field(
        default_factory=list,
        description="Main competitors to be aware of"
    )
    our_advantage: str | None = Field(
        default=None,
        description="Our key advantage vs their likely tools"
    )
    avoid_mentioning: list[str] = Field(
        default_factory=list,
        description="Competitors to avoid bringing up first"
    )


class VoiceKBOutput(BaseModel):
    """Complete voice knowledge base output."""

    # Pronunciation and basics
    pronunciation: PronunciationGuide = Field(description="Pronunciation guides")

    # Company context
    company_context: str = Field(
        description="One paragraph summary of company, recent news, situation"
    )
    company_talking_points: list[str] = Field(
        default_factory=list,
        description="Key talking points about their company"
    )

    # Opening strategies
    opening_hooks: list[str] = Field(
        description="Specific opening hooks to use based on research"
    )
    recommended_opener: str | None = Field(
        default=None,
        description="Recommended opening line for this specific prospect"
    )

    # Pain point discussion
    pain_points: list[str] = Field(
        default_factory=list,
        description="Pain points to potentially discuss"
    )
    pain_point_questions: list[str] = Field(
        default_factory=list,
        description="Questions to ask about pain points"
    )

    # Objection handling
    objection_responses: ObjectionHandlers = Field(
        description="Objection handling templates"
    )

    # Topics and navigation
    do_not_mention: list[str] = Field(
        default_factory=list,
        description="Topics to avoid (with reasons)"
    )
    conversation_starters: list[str] = Field(
        default_factory=list,
        description="Conversation starters based on research"
    )
    transition_phrases: list[str] = Field(
        default_factory=list,
        description="Phrases to transition between topics"
    )

    # Competitor intelligence
    competitor_intel: CompetitorContext | None = Field(
        default=None,
        description="Competitor intelligence"
    )

    # Meeting booking
    meeting_ask: str = Field(
        default="Would you be open to a 15-minute call this week to explore this further?",
        description="How to ask for the meeting"
    )
    calendar_link_mention: str = Field(
        default="I can send over a calendar link right after this call if that's easier.",
        description="How to mention calendar booking"
    )

    # Closing
    closing_summary: str = Field(
        default="Thanks for your time today. I'll send over a quick recap email.",
        description="How to close the call"
    )


# ============================================
# SYSTEM PROMPT
# ============================================


VOICE_KB_SYSTEM_PROMPT = """You are building a knowledge base for an AI voice agent making B2B sales calls. The voice agent needs context to have natural, informed conversations.

Your output will be used by the voice AI to:
1. Open the call with something specific and relevant
2. Handle objections with company-specific responses
3. Navigate the conversation intelligently
4. Sound informed and prepared (not robotic)
5. Know what topics to avoid

QUALITY STANDARDS:

GOOD opening hook (specific, based on research):
"Congrats on the Series B! I saw the TechCrunch coverage - that's exciting growth."

BAD opening hook (generic):
"Hi, how are you today? Do you have a few minutes?"

GOOD objection response (specific to their situation):
"I understand budget's tight after the Series B - most of that's going to product and hiring. Our clients typically see ROI in 90 days which fits most post-funding budget cycles."

BAD objection response (generic):
"I understand. Let me tell you about our pricing options."

GOOD pain point question (informed):
"With 5 SDRs starting in Q2, how are you thinking about maintaining lead response times during ramp-up?"

BAD pain point question (generic):
"What are your biggest challenges right now?"

OUTPUT FORMAT (JSON):
{
    "pronunciation": {
        "contact_name": "First LAST (phonetic if unusual, e.g., 'Siobhan' = 'shi-VAWN')",
        "company_name": "COM-pa-ny (phonetic if unusual)",
        "industry_terms": ["term1", "term2"]
    },
    "company_context": "One paragraph summary of company, recent news, situation",
    "company_talking_points": ["Point 1", "Point 2"],
    "opening_hooks": [
        "Congrats on the Series B!",
        "Saw you're hiring 5 SDRs"
    ],
    "recommended_opener": "Hi {first_name}, this is [Name] from [Company]. Congrats on the Series B - saw the announcement. Quick question...",
    "pain_points": [
        "Lead response time during scaling",
        "Onboarding new SDRs while maintaining quality"
    ],
    "pain_point_questions": [
        "With the team growing, how are you handling lead response times?",
        "How's the SDR ramp-up going with the new hires?"
    ],
    "objection_responses": {
        "not_interested": "I hear you. Before I let you go - with 5 SDRs starting, what's your current plan for lead response during ramp-up?",
        "no_budget": "Makes sense post-funding - most of that's going to hiring. When does your next budget cycle start?",
        "bad_timing": "Totally understand - Q2 with the new SDRs is probably hectic. Would next quarter be better to reconnect?",
        "using_competitor": "Ah, who are you using? [Listen] That's solid. How's it handling the volume with the team growth?",
        "need_to_think": "Of course. What aspects would be most useful to think through - the integration, pricing, or implementation timeline?",
        "send_info": "Happy to. What would help most - a case study from a similar post-Series B company, or just pricing overview?",
        "custom_objections": [
            {"objection": "We just hired someone for this", "response": "That's great! What role - are they building out the SDR ops?", "follow_up": "Our tool actually helps new hires ramp faster - worth a look?"}
        ]
    },
    "do_not_mention": [
        "Recent layoffs at their competitor (sensitive topic)",
        "Their failed product launch last year"
    ],
    "conversation_starters": [
        "Your LinkedIn post about outbound challenges resonated",
        "The funding announcement mentioned expanding sales - how's that going?"
    ],
    "transition_phrases": [
        "That connects to something I wanted to ask...",
        "Speaking of that...",
        "That actually relates to why I called..."
    ],
    "competitor_intel": {
        "likely_current_tools": "HubSpot, Outreach (based on job posts)",
        "main_competitors": ["Outreach", "Salesloft"],
        "our_advantage": "We specialize in post-funding SDR ramp - they're more enterprise-focused",
        "avoid_mentioning": ["Apollo (they may use it for data)"]
    },
    "meeting_ask": "Would 15 minutes this week work to show you how we've helped similar companies?",
    "calendar_link_mention": "I can drop a calendar link in your inbox right after this - might be easier.",
    "closing_summary": "Appreciate your time, {first_name}. I'll send a quick recap with that case study."
}

IMPORTANT:
- Be SPECIFIC. Use actual information from the research.
- Every objection response should reference something specific about their situation.
- The voice AI will sound robotic if you give generic responses.
- Include phonetic pronunciations for any unusual names."""


# ============================================
# VOICE KB AGENT
# ============================================


async def run_sdk_voice_kb(
    lead_data: dict[str, Any],
    enrichment_data: dict[str, Any] | None = None,
    campaign_context: dict[str, Any] | None = None,
    client_id: UUID | None = None,
) -> SDKBrainResult:
    """
    Generate voice knowledge base for Hot lead using SDK.

    Args:
        lead_data: Lead info (name, company, title, etc.)
        enrichment_data: Optional SDK enrichment output
        campaign_context: Optional campaign info
        client_id: Optional client ID for cost tracking

    Returns:
        SDKBrainResult with voice KB
    """
    # Build context from lead data
    first_name = lead_data.get("first_name", "")
    last_name = lead_data.get("last_name", "")
    name = f"{first_name} {last_name}".strip() or "Unknown"
    company = lead_data.get("company_name") or lead_data.get("organization_name") or lead_data.get("company", "")
    title = lead_data.get("title", "")
    industry = lead_data.get("company_industry") or lead_data.get("organization_industry", "")
    employee_count = lead_data.get("company_employee_count") or lead_data.get("organization_employee_count", "")
    city = lead_data.get("company_city") or lead_data.get("organization_city", "")
    country = lead_data.get("company_country") or lead_data.get("organization_country", "")
    location = f"{city}, {country}" if city and country else (city or country or "")

    # Build enrichment context
    enrichment_section = "No additional research available."
    if enrichment_data:
        enrichment_parts = []

        # Funding
        if enrichment_data.get("funding"):
            f = enrichment_data["funding"]
            funding_details = []
            if f.get("amount"):
                funding_details.append(f"Amount: {f['amount']}")
            if f.get("round"):
                funding_details.append(f"Round: {f['round']}")
            if f.get("date"):
                funding_details.append(f"Date: {f['date']}")
            if f.get("investors"):
                funding_details.append(f"Investors: {', '.join(f['investors'][:3])}")
            if funding_details:
                enrichment_parts.append(f"FUNDING: {'; '.join(funding_details)}")

        # Hiring
        if enrichment_data.get("hiring"):
            h = enrichment_data["hiring"]
            hiring_details = []
            if h.get("total_open_roles"):
                hiring_details.append(f"{h['total_open_roles']} total open roles")
            if h.get("sales_roles"):
                hiring_details.append(f"{h['sales_roles']} sales roles")
            if h.get("key_positions"):
                hiring_details.append(f"Key: {', '.join(h['key_positions'][:4])}")
            if hiring_details:
                enrichment_parts.append(f"HIRING: {'; '.join(hiring_details)}")

        # Recent news
        if enrichment_data.get("recent_news"):
            news_items = []
            for n in enrichment_data["recent_news"][:3]:
                if n.get("headline"):
                    news_item = n["headline"]
                    if n.get("date"):
                        news_item += f" ({n['date']})"
                    news_items.append(news_item)
            if news_items:
                enrichment_parts.append(f"RECENT NEWS:\n  - " + "\n  - ".join(news_items))

        # Pain points
        if enrichment_data.get("pain_points"):
            pains = enrichment_data["pain_points"][:4]
            enrichment_parts.append(f"IDENTIFIED PAIN POINTS:\n  - " + "\n  - ".join(pains))

        # Personalization hooks
        if enrichment_data.get("personalization_hooks"):
            hooks = enrichment_data["personalization_hooks"][:4]
            enrichment_parts.append(f"PERSONALIZATION HOOKS:\n  - " + "\n  - ".join(hooks))

        # Competitor intel
        if enrichment_data.get("competitor_intel"):
            c = enrichment_data["competitor_intel"]
            comp_details = []
            if c.get("main_competitors"):
                comp_details.append(f"Competitors: {', '.join(c['main_competitors'][:4])}")
            if c.get("positioning"):
                comp_details.append(f"Positioning: {c['positioning']}")
            if comp_details:
                enrichment_parts.append(f"COMPETITOR INTEL: {'; '.join(comp_details)}")

        # Conversation starters
        if enrichment_data.get("conversation_starters"):
            starters = enrichment_data["conversation_starters"][:3]
            enrichment_parts.append(f"CONVERSATION STARTERS:\n  - " + "\n  - ".join(starters))

        if enrichment_parts:
            enrichment_section = "\n\n".join(enrichment_parts)

    # LinkedIn data
    linkedin_section = ""
    linkedin_parts = []
    if lead_data.get("linkedin_headline"):
        linkedin_parts.append(f"Headline: {lead_data['linkedin_headline']}")
    if lead_data.get("linkedin_about"):
        about = lead_data["linkedin_about"]
        if len(about) > 400:
            about = about[:400] + "..."
        linkedin_parts.append(f"About: {about}")
    if lead_data.get("linkedin_recent_posts"):
        posts = lead_data["linkedin_recent_posts"]
        if len(posts) > 600:
            posts = posts[:600] + "..."
        linkedin_parts.append(f"Recent posts: {posts}")
    if linkedin_parts:
        linkedin_section = "\n".join(linkedin_parts)

    # Product context
    product_section = """
OUR PRODUCT:
- Name: Agency OS
- Category: AI-powered outbound lead generation
- Value: Multi-channel outreach (email, LinkedIn, SMS, voice, direct mail) with AI personalization
- Differentiator: Unified platform with AI that learns what works for each prospect"""

    if campaign_context:
        custom_product = []
        if campaign_context.get("product_name"):
            custom_product.append(f"- Name: {campaign_context['product_name']}")
        if campaign_context.get("value_prop"):
            custom_product.append(f"- Value: {campaign_context['value_prop']}")
        if campaign_context.get("differentiator"):
            custom_product.append(f"- Differentiator: {campaign_context['differentiator']}")
        if custom_product:
            product_section = "OUR PRODUCT:\n" + "\n".join(custom_product)

    user_prompt = f"""Build a voice knowledge base for calling this prospect:

PROSPECT:
- Name: {name}
- Title: {title}
- Company: {company}
- Industry: {industry}
- Company size: {employee_count} employees
- Location: {location}

LINKEDIN DATA:
{linkedin_section if linkedin_section else 'N/A'}

RESEARCH FINDINGS:
{enrichment_section}

{product_section}

Create a comprehensive voice knowledge base. The voice AI needs to:
1. Sound informed about their company and situation
2. Have specific opening hooks based on research
3. Handle objections with company-specific responses
4. Know what topics to avoid

Make every response SPECIFIC to their situation. Generic responses make the voice AI sound robotic.

Return JSON matching the schema."""

    logger.info(f"Generating SDK voice KB for {name} at {company}")

    # Create SDK brain with voice_kb config
    brain = create_sdk_brain("voice_kb")

    # Run the agent (no tools needed - uses provided data)
    result = await brain.run(
        prompt=user_prompt,
        tools=[],  # No tools needed for KB generation
        output_schema=VoiceKBOutput,
        system=VOICE_KB_SYSTEM_PROMPT,
    )

    if result.success:
        logger.info(
            f"SDK voice KB generated for {name} at {company}",
            extra={
                "cost_aud": result.cost_aud,
                "turns": result.turns_used,
            }
        )
    else:
        logger.warning(f"SDK voice KB generation failed for {name} at {company}: {result.error}")

    return result


async def generate_hot_lead_voice_kb(
    lead_data: dict[str, Any],
    enrichment_data: dict[str, Any] | None = None,
    campaign_context: dict[str, Any] | None = None,
    client_id: UUID | None = None,
) -> dict[str, Any] | None:
    """
    Convenience function to generate voice KB for Hot lead.

    Args:
        lead_data: Lead data dict
        enrichment_data: Optional SDK enrichment data
        campaign_context: Optional campaign context
        client_id: Optional client ID

    Returns:
        Voice KB dict or None if failed
    """
    result = await run_sdk_voice_kb(
        lead_data=lead_data,
        enrichment_data=enrichment_data,
        campaign_context=campaign_context,
        client_id=client_id,
    )

    if not result.success:
        return None

    # Convert Pydantic model to dict if needed
    if result.data:
        if isinstance(result.data, VoiceKBOutput):
            return {
                **result.data.model_dump(),
                "source": "sdk",
                "cost_aud": result.cost_aud,
            }
        elif isinstance(result.data, dict):
            return {
                **result.data,
                "source": "sdk",
                "cost_aud": result.cost_aud,
            }

    return None


def get_basic_voice_kb(lead_data: dict[str, Any]) -> dict[str, Any]:
    """
    Generate a basic voice KB for non-Hot leads.

    This is a fallback that doesn't use SDK (cheaper).

    Args:
        lead_data: Lead data dict

    Returns:
        Basic voice KB dict
    """
    first_name = lead_data.get("first_name", "there")
    company = lead_data.get("company_name") or lead_data.get("company", "your company")
    title = lead_data.get("title", "")

    return {
        "pronunciation": {
            "contact_name": first_name,
            "company_name": company,
            "industry_terms": [],
        },
        "company_context": f"{company} - {lead_data.get('company_industry', 'company')}",
        "company_talking_points": [],
        "opening_hooks": [f"Hi {first_name}, this is a quick call about..."],
        "recommended_opener": f"Hi {first_name}, this is [Name] from [Company]. Quick question for you.",
        "pain_points": [],
        "pain_point_questions": [],
        "objection_responses": {
            "not_interested": "I understand. What made you say that?",
            "no_budget": "I hear you on budget. When do you typically review this?",
            "bad_timing": "No problem. When would be better?",
            "using_competitor": "That's great - what's working well for you?",
            "need_to_think": "Of course. What would you like to think through?",
            "send_info": "Happy to. What would be most useful?",
            "custom_objections": [],
        },
        "do_not_mention": [],
        "conversation_starters": [],
        "transition_phrases": [
            "That connects to something I wanted to ask...",
            "Speaking of that...",
        ],
        "competitor_intel": None,
        "meeting_ask": "Would 15 minutes work to explore this further?",
        "calendar_link_mention": "I can send a calendar link right after.",
        "closing_summary": f"Thanks for your time, {first_name}. I'll send a quick recap.",
        "source": "standard",
        "cost_aud": 0.0,
    }
