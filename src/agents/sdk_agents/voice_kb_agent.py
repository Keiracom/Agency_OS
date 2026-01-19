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
    """Objection handling templates - disarmingly honest persona."""
    not_interested: str = Field(
        default="Ha, I get that a lot. Honestly, most people aren't until something breaks. What would need to go wrong for you to care about this?",
        description="Response when prospect says they're not interested"
    )
    no_budget: str = Field(
        default="Yeah, nobody has budget for stuff they don't need yet. I'm not trying to sell you today - just curious if lead gen is even a problem for you?",
        description="Response for budget objections"
    )
    bad_timing: str = Field(
        default="When is it ever good timing, right? Look, I'll be honest - is this a real 'not now' or a polite 'go away'? Either's fine.",
        description="Response for timing objections"
    )
    using_competitor: str = Field(
        default="Oh nice, who? I'm genuinely curious. We lose deals to them sometimes - what made you pick them?",
        description="Response when using competitor"
    )
    need_to_think: str = Field(
        default="Sure. But real talk - is that code for 'I'm not the right person' or do you actually want to bring this up?",
        description="Response for 'need to think about it'"
    )
    send_info: str = Field(
        default="I can, but let's be real - you'll never read it. What would I need to say right now for you to actually care?",
        description="Response for 'just send me info'"
    )
    too_busy: str = Field(
        default="Same. I'll be quick and honest - if this isn't relevant in 30 seconds, tell me to piss off and I will.",
        description="Response for 'too busy'"
    )
    call_back_later: str = Field(
        default="I can, but we both know I'll catch you at another bad time. What's actually going on - is this just not a fit?",
        description="Response for 'call me back later'"
    )
    how_did_you_get_my_number: str = Field(
        default="LinkedIn and your website. I know, it's weird getting cold called. I researched you though - not just dialing random numbers.",
        description="Response for 'how did you get my number'"
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


VOICE_KB_SYSTEM_PROMPT = """You are building a knowledge base for an AI voice agent making B2B sales calls.

=== PERSONA: DISARMINGLY HONEST ===

The voice AI should sound like a real person who:
- Is genuinely curious, not pushy
- Admits uncomfortable truths ("let's be real - you'll never read it")
- Calls out the elephant in the room ("is this a polite 'go away'?")
- Uses casual language, not corporate speak
- Is slightly self-deprecating ("I get that a lot", "we lose deals to them sometimes")
- Asks real questions, not rhetorical ones
- Respects their time with directness
- Doesn't pretend everything is sunshine

TONE EXAMPLES:

"Not interested" response:
GOOD (honest): "Ha, I get that a lot. Honestly, most people aren't until something breaks. What would need to go wrong for you to care about this?"
BAD (salesy): "I understand. Let me share some value with you..."

"Send me info" response:
GOOD (honest): "I can, but let's be real - you'll never read it. What would I need to say right now for you to actually care?"
BAD (salesy): "Happy to! What would be most useful - case studies or pricing?"

"Too busy" response:
GOOD (honest): "Same. I'll be quick and honest - if this isn't relevant in 30 seconds, tell me to piss off and I will."
BAD (salesy): "I understand you're busy. I'll just take a moment of your time..."

"Using competitor" response:
GOOD (honest): "Oh nice, who? I'm genuinely curious. We lose deals to them sometimes - what made you pick them?"
BAD (salesy): "That's great! What's working well for you? [pivot to why we're better]"

=== RULES ===

1. Be SPECIFIC - use actual research about their company
2. Be HONEST - admit when you don't know, acknowledge awkward truths
3. Be CURIOUS - ask real questions you actually want answered
4. Be DIRECT - don't dance around, say what you mean
5. Be HUMAN - use casual language, contractions, occasional humor
6. NEVER use phrases like:
   - "I understand"
   - "I hear you"
   - "Totally get it"
   - "That's great!"
   - "Happy to help"
   - "Quick question for you"
   - "Do you have a few minutes?"

=== OUTPUT FORMAT (JSON) ===

{
    "pronunciation": {
        "contact_name": "First LAST (phonetic if unusual)",
        "company_name": "COM-pa-ny (phonetic if unusual)",
        "industry_terms": ["term1", "term2"]
    },
    "company_context": "One paragraph - what they do, recent news, situation",
    "company_talking_points": ["Specific thing 1", "Specific thing 2"],
    "opening_hooks": [
        "Saw the Series B news - congrats",
        "Noticed you're hiring 5 SDRs"
    ],
    "recommended_opener": "Hey {first_name}, saw [specific thing]. Quick honest question - is outbound even a priority right now, or am I wasting both our time?",
    "pain_points": [
        "Specific pain point from research",
        "Another specific pain point"
    ],
    "pain_point_questions": [
        "With 5 SDRs starting, how's lead response time holding up?",
        "Honest question - is your current setup actually working or just 'fine'?"
    ],
    "objection_responses": {
        "not_interested": "Ha, fair. Most people aren't until something breaks. What would need to go wrong for this to matter?",
        "no_budget": "Yeah, nobody budgets for stuff they don't need yet. Is lead gen actually a problem, or is this genuinely not a priority?",
        "bad_timing": "When is it ever good timing? Real talk - is this a 'not now' or a polite 'go away'? Either's fine.",
        "using_competitor": "Oh nice, who? Genuinely curious - we lose to them sometimes. What made you pick them?",
        "need_to_think": "Sure. But honest question - is that code for 'not the right person' or do you actually want to think about it?",
        "send_info": "I can, but let's be real - you'll never read it. What would I need to say now for you to care?",
        "too_busy": "Same. 30 seconds - if this isn't relevant, tell me and I'll go. Fair?",
        "call_back_later": "We both know I'll catch you at another bad time. What's actually going on?",
        "how_did_you_get_my_number": "LinkedIn and your website. Yeah, cold calls are weird. I did research you though - not just dialing random numbers.",
        "custom_objections": [
            {"objection": "Situation-specific objection", "response": "Honest response referencing their situation", "follow_up": "Follow-up if needed"}
        ]
    },
    "do_not_mention": [
        "Topic to avoid (reason)"
    ],
    "conversation_starters": [
        "Your post about X - was that based on real experience or just content?",
        "The funding news mentioned expanding sales. How's that actually going?"
    ],
    "transition_phrases": [
        "That actually relates to why I called...",
        "So here's my real question...",
        "Can I be direct about something?"
    ],
    "competitor_intel": {
        "likely_current_tools": "What they probably use based on job posts",
        "main_competitors": ["Competitor A", "Competitor B"],
        "our_advantage": "Specific advantage, honestly stated",
        "avoid_mentioning": ["Tools to not bring up first"]
    },
    "meeting_ask": "Look, would 15 minutes actually be useful, or would I be wasting your time?",
    "calendar_link_mention": "I can send a calendar link if that's easier - or just tell me to bugger off.",
    "closing_summary": "Appreciate the honesty, {first_name}. I'll send a quick recap - no essays, I promise."
}

Remember: The goal is to sound like a real person having a real conversation, not a sales robot following a script."""


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
    Uses disarmingly honest persona.

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
        "opening_hooks": [f"Hey {first_name}, quick honest question..."],
        "recommended_opener": f"Hey {first_name}, I'll be direct - is outbound lead gen even on your radar right now, or am I wasting both our time?",
        "pain_points": [],
        "pain_point_questions": [],
        "objection_responses": {
            "not_interested": "Ha, I get that a lot. Honestly, most people aren't until something breaks. What would need to go wrong for you to care about this?",
            "no_budget": "Yeah, nobody has budget for stuff they don't need yet. Is lead gen actually a problem for you?",
            "bad_timing": "When is it ever good timing? Real talk - is this a 'not now' or a polite 'go away'? Either's fine.",
            "using_competitor": "Oh nice, who? I'm genuinely curious - we lose deals to them sometimes. What made you pick them?",
            "need_to_think": "Sure. But honest question - is that code for 'not the right person' or do you actually want to think about it?",
            "send_info": "I can, but let's be real - you'll never read it. What would I need to say right now for you to actually care?",
            "too_busy": "Same. 30 seconds - if this isn't relevant, tell me and I'll go. Fair?",
            "call_back_later": "We both know I'll catch you at another bad time. What's actually going on?",
            "how_did_you_get_my_number": "LinkedIn and your website. Yeah, cold calls are weird. I did research you though.",
            "custom_objections": [],
        },
        "do_not_mention": [],
        "conversation_starters": [],
        "transition_phrases": [
            "That actually relates to why I called...",
            "So here's my real question...",
            "Can I be direct about something?",
        ],
        "competitor_intel": None,
        "meeting_ask": "Look, would 15 minutes actually be useful, or would I be wasting your time?",
        "calendar_link_mention": "I can send a calendar link if that's easier - or just tell me to bugger off.",
        "closing_summary": f"Appreciate the honesty, {first_name}. I'll send a quick recap - no essays, I promise.",
        "source": "standard",
        "cost_aud": 0.0,
    }
