"""
Contract: src/agents/sdk_agents/email_agent.py
Purpose: SDK-powered email generation for Hot leads
Layer: 3 - agents
Imports: models, integrations (sdk_brain)
Consumers: content engine

This agent generates highly personalized cold emails for Hot leads (ALS 85+).
It uses enrichment data (funding, hiring, pain points) to craft emails that
reference specific, current information about the prospect.

Key features:
- Subject lines that reference specific research findings
- Opening lines that lead with THEIR news, not your product
- Body that connects their situation to a pain point
- Soft CTA that's easy to respond to
- Word count control (50-100 words for body)
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from src.integrations.sdk_brain import SDKBrainResult, create_sdk_brain

logger = logging.getLogger(__name__)


# ============================================
# OUTPUT SCHEMA
# ============================================


class EmailOutput(BaseModel):
    """Generated email output."""
    subject: str = Field(description="Email subject line (max 50 characters)")
    body: str = Field(description="Email body (50-100 words)")
    personalization_used: list[str] = Field(
        default_factory=list,
        description="What personalization elements were used"
    )
    estimated_word_count: int = Field(default=0, description="Estimated word count of body")
    tone: str = Field(default="professional", description="Tone used in the email")
    opening_type: str = Field(
        default="news_reference",
        description="Type of opening: news_reference, hiring_mention, pain_point, mutual_connection"
    )


class EmailVariants(BaseModel):
    """Multiple email variants for A/B testing."""
    primary: EmailOutput = Field(description="Primary email version")
    variant_a: EmailOutput | None = Field(default=None, description="A/B test variant A")
    variant_b: EmailOutput | None = Field(default=None, description="A/B test variant B")


# ============================================
# SYSTEM PROMPT
# ============================================


EMAIL_SYSTEM_PROMPT = """You are an expert B2B cold email copywriter. Your emails get 8-12% reply rates because they reference specific, current information about the recipient.

RULES:
1. Subject line: Max 50 chars, reference something SPECIFIC (funding, hiring, their post)
2. Opening: Lead with THEIR news/situation, NOT your product
3. Body: Connect their situation to a pain point, then your solution
4. CTA: Soft ask, one question, easy to answer
5. Length: 50-100 words max in the body
6. Tone: Professional but human, no buzzwords like "synergy" or "leverage"
7. No spam triggers: Avoid ALL CAPS, excessive punctuation, "FREE", "ACT NOW"

BAD EXAMPLE (generic, self-focused):
"Hi {name},

I hope this finds you well. We help companies like yours with lead generation. Our AI platform increases response rates by 3x. Would you like to learn more?

Best,
[Name]"

GOOD EXAMPLE (specific, prospect-focused):
"Hi Sarah,

Congrats on the $18M Series B - saw the TechCrunch piece. With 5 SDRs joining (per your careers page), lead response time usually suffers during ramp-up.

We've helped 3 post-Series B companies maintain <5 min response times while scaling their SDR team.

Worth a quick chat, or is timing off?

[Name]"

STRUCTURE:
1. [Hook] - Reference something specific about them (1 sentence)
2. [Bridge] - Connect to a likely pain point (1 sentence)
3. [Value] - Brief mention of how you can help (1 sentence)
4. [CTA] - Easy, low-commitment question (1 sentence)

OUTPUT FORMAT (JSON):
{
    "subject": "Congrats on the Series B, Sarah",
    "body": "Hi Sarah,\\n\\nCongrats on the $18M Series B - saw the TechCrunch piece. With 5 SDRs joining (per your careers page), lead response time usually suffers during ramp-up.\\n\\nWe've helped 3 post-Series B companies maintain <5 min response times while scaling their SDR team.\\n\\nWorth a quick chat, or is timing off?\\n\\n[Name]",
    "personalization_used": ["funding_mention", "hiring_data", "industry_specific_pain"],
    "estimated_word_count": 65,
    "tone": "professional_casual",
    "opening_type": "news_reference"
}

Remember: The goal is to start a conversation, not close a deal. Make it easy to reply."""


# ============================================
# EMAIL AGENT
# ============================================


async def run_sdk_email(
    lead_data: dict[str, Any],
    enrichment_data: dict[str, Any] | None = None,
    campaign_context: dict[str, Any] | None = None,
    client_intelligence: dict[str, Any] | None = None,
    client_id: UUID | None = None,
    generate_variants: bool = False,
) -> SDKBrainResult:
    """
    Generate personalized email for Hot lead using SDK.

    Args:
        lead_data: Lead info (name, company, title, etc.)
        enrichment_data: Optional SDK enrichment output (funding, hiring, etc.)
        campaign_context: Optional campaign info (product, ICP, tone)
        client_intelligence: Optional client proof points (case studies, testimonials, metrics)
        client_id: Optional client ID for cost tracking
        generate_variants: If True, generate A/B test variants

    Returns:
        SDKBrainResult with email content
    """
    # Build context from lead data
    first_name = lead_data.get("first_name", "")
    last_name = lead_data.get("last_name", "")
    f"{first_name} {last_name}".strip() or "there"
    company = lead_data.get("company_name") or lead_data.get("organization_name") or lead_data.get("company", "")
    title = lead_data.get("title", "")
    industry = lead_data.get("company_industry") or lead_data.get("organization_industry", "")
    employee_count = lead_data.get("company_employee_count") or lead_data.get("organization_employee_count", "")

    # Build enrichment context section
    enrichment_section = ""
    if enrichment_data:
        enrichment_parts = []

        # Funding info
        if enrichment_data.get("funding"):
            f = enrichment_data["funding"]
            funding_str = []
            if f.get("amount"):
                funding_str.append(f"Amount: {f['amount']}")
            if f.get("round"):
                funding_str.append(f"Round: {f['round']}")
            if f.get("date"):
                funding_str.append(f"Date: {f['date']}")
            if f.get("investors"):
                funding_str.append(f"Investors: {', '.join(f['investors'][:3])}")
            if funding_str:
                enrichment_parts.append(f"FUNDING: {'; '.join(funding_str)}")

        # Hiring info
        if enrichment_data.get("hiring"):
            h = enrichment_data["hiring"]
            hiring_str = []
            if h.get("total_open_roles"):
                hiring_str.append(f"{h['total_open_roles']} open roles")
            if h.get("sales_roles"):
                hiring_str.append(f"{h['sales_roles']} sales positions")
            if h.get("key_positions"):
                hiring_str.append(f"Key positions: {', '.join(h['key_positions'][:3])}")
            if hiring_str:
                enrichment_parts.append(f"HIRING: {'; '.join(hiring_str)}")

        # Recent news
        if enrichment_data.get("recent_news"):
            news_items = enrichment_data["recent_news"][:2]  # First 2 news items
            news_str = "; ".join([n.get("headline", "") for n in news_items if n.get("headline")])
            if news_str:
                enrichment_parts.append(f"RECENT NEWS: {news_str}")

        # Pain points
        if enrichment_data.get("pain_points"):
            pains = enrichment_data["pain_points"][:3]
            enrichment_parts.append(f"IDENTIFIED PAIN POINTS: {'; '.join(pains)}")

        # Personalization hooks
        if enrichment_data.get("personalization_hooks"):
            hooks = enrichment_data["personalization_hooks"][:3]
            enrichment_parts.append(f"SUGGESTED HOOKS: {'; '.join(hooks)}")

        # Competitor intel
        if enrichment_data.get("competitor_intel"):
            c = enrichment_data["competitor_intel"]
            if c.get("main_competitors"):
                enrichment_parts.append(f"COMPETITORS: {', '.join(c['main_competitors'][:3])}")

        enrichment_section = "\n- ".join(enrichment_parts)
        if enrichment_section:
            enrichment_section = "\n- " + enrichment_section

    # LinkedIn data section
    linkedin_section = ""
    linkedin_parts = []
    if lead_data.get("linkedin_headline"):
        linkedin_parts.append(f"Headline: {lead_data['linkedin_headline']}")
    if lead_data.get("linkedin_about"):
        about = lead_data["linkedin_about"][:300] + "..." if len(lead_data.get("linkedin_about", "")) > 300 else lead_data.get("linkedin_about", "")
        linkedin_parts.append(f"About: {about}")
    if lead_data.get("linkedin_recent_posts"):
        posts = lead_data["linkedin_recent_posts"][:500] + "..." if len(lead_data.get("linkedin_recent_posts", "")) > 500 else lead_data.get("linkedin_recent_posts", "")
        linkedin_parts.append(f"Recent posts: {posts}")
    if linkedin_parts:
        linkedin_section = "\n".join(linkedin_parts)

    # Campaign context section
    campaign_section = ""
    if campaign_context:
        campaign_parts = []
        if campaign_context.get("product_name"):
            campaign_parts.append(f"Product: {campaign_context['product_name']}")
        if campaign_context.get("value_prop"):
            campaign_parts.append(f"Value prop: {campaign_context['value_prop']}")
        if campaign_context.get("tone"):
            campaign_parts.append(f"Desired tone: {campaign_context['tone']}")
        if campaign_context.get("company_name"):
            campaign_parts.append(f"Your company: {campaign_context['company_name']}")
        if campaign_context.get("sender_name"):
            campaign_parts.append(f"Sender name: {campaign_context['sender_name']}")
        if campaign_parts:
            campaign_section = f"""
CAMPAIGN CONTEXT:
{chr(10).join(f'- {p}' for p in campaign_parts)}
"""

    # Client intelligence section (proof points for credibility)
    proof_section = ""
    if client_intelligence:
        proof_parts = []

        # Proof metrics (e.g., "40% increase in leads")
        if client_intelligence.get("proof_metrics"):
            metrics = client_intelligence["proof_metrics"][:3]
            if isinstance(metrics[0], dict):
                metrics_str = "; ".join([m.get("metric", "") for m in metrics if m.get("metric")])
            else:
                metrics_str = "; ".join(metrics[:3])
            if metrics_str:
                proof_parts.append(f"PROOF METRICS: {metrics_str}")

        # Named clients (social proof)
        if client_intelligence.get("proof_clients"):
            clients = client_intelligence["proof_clients"][:5]
            proof_parts.append(f"NAMED CLIENTS: {', '.join(clients)}")

        # Industries served
        if client_intelligence.get("proof_industries"):
            industries = client_intelligence["proof_industries"][:3]
            proof_parts.append(f"INDUSTRIES SERVED: {', '.join(industries)}")

        # Testimonials
        if client_intelligence.get("testimonials"):
            testimonials = client_intelligence["testimonials"][:2]
            for t in testimonials:
                if isinstance(t, dict) and t.get("quote"):
                    author = t.get("author", "Client")
                    proof_parts.append(f"TESTIMONIAL: \"{t['quote'][:100]}...\" - {author}")

        # Review ratings
        if client_intelligence.get("ratings"):
            ratings = client_intelligence["ratings"]
            rating_str = []
            for platform, data in ratings.items():
                if isinstance(data, dict) and data.get("rating"):
                    rating_str.append(f"{platform}: {data['rating']}/5")
            if rating_str:
                proof_parts.append(f"REVIEW RATINGS: {', '.join(rating_str)}")

        # Differentiators
        if client_intelligence.get("differentiators"):
            diffs = client_intelligence["differentiators"][:3]
            proof_parts.append(f"KEY DIFFERENTIATORS: {'; '.join(diffs)}")

        if proof_parts:
            proof_section = f"""
YOUR COMPANY'S PROOF POINTS (use 1-2 subtly in the email):
{chr(10).join(f'- {p}' for p in proof_parts)}
"""

    # Build the prompt
    variants_instruction = """
Also generate 2 variants for A/B testing:
- Variant A: Different subject line approach
- Variant B: Different opening hook

Return JSON with: {"primary": {...}, "variant_a": {...}, "variant_b": {...}}
""" if generate_variants else """
Return JSON with: {"subject": "...", "body": "...", "personalization_used": [...], "estimated_word_count": N, "tone": "...", "opening_type": "..."}
"""

    user_prompt = f"""Write a cold email to this prospect:

PROSPECT:
- Name: {first_name}
- Title: {title}
- Company: {company}
- Industry: {industry}
- Company size: {employee_count} employees

RESEARCH FINDINGS:{enrichment_section if enrichment_section else ' None available - use LinkedIn data instead'}

LINKEDIN DATA:
{linkedin_section if linkedin_section else 'N/A'}
{campaign_section}{proof_section}
INSTRUCTIONS:
1. Use the research findings to personalize the email
2. Lead with THEIR situation, not your product
3. Keep the body to 50-100 words
4. Make the subject line specific (reference funding, hiring, or their post)
5. End with a soft, easy-to-answer CTA

{variants_instruction}"""

    logger.info(f"Generating SDK email for {first_name} at {company}")

    # Create SDK brain with email config
    brain = create_sdk_brain("email")

    # Run the agent (no tools needed - uses provided data)
    output_schema = EmailVariants if generate_variants else EmailOutput

    result = await brain.run(
        prompt=user_prompt,
        tools=[],  # No tools needed for email generation
        output_schema=output_schema,
        system=EMAIL_SYSTEM_PROMPT,
    )

    if result.success:
        logger.info(
            f"SDK email generated for {first_name} at {company}",
            extra={
                "cost_aud": result.cost_aud,
                "turns": result.turns_used,
            }
        )
    else:
        logger.warning(f"SDK email generation failed for {first_name} at {company}: {result.error}")

    return result


async def generate_hot_lead_email(
    lead_data: dict[str, Any],
    enrichment_data: dict[str, Any] | None = None,
    campaign_context: dict[str, Any] | None = None,
    client_intelligence: dict[str, Any] | None = None,
    client_id: UUID | None = None,
) -> dict[str, Any] | None:
    """
    Convenience function to generate email for Hot lead.

    Args:
        lead_data: Lead data dict
        enrichment_data: Optional SDK enrichment data
        campaign_context: Optional campaign context
        client_intelligence: Optional client proof points
        client_id: Optional client ID

    Returns:
        Email dict with subject, body, metadata or None if failed
    """
    result = await run_sdk_email(
        lead_data=lead_data,
        enrichment_data=enrichment_data,
        campaign_context=campaign_context,
        client_intelligence=client_intelligence,
        client_id=client_id,
    )

    if not result.success:
        return None

    # Convert Pydantic model to dict if needed
    if result.data:
        if isinstance(result.data, EmailOutput):
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


async def generate_email_sequence(
    lead_data: dict[str, Any],
    enrichment_data: dict[str, Any] | None = None,
    campaign_context: dict[str, Any] | None = None,
    client_intelligence: dict[str, Any] | None = None,
    sequence_length: int = 3,
    client_id: UUID | None = None,
) -> list[dict[str, Any]]:
    """
    Generate a multi-touch email sequence for a Hot lead.

    Each email in the sequence has a different angle:
    1. Initial outreach (news/research hook)
    2. Follow-up (different pain point angle)
    3. Break-up (final attempt with urgency)

    Args:
        lead_data: Lead data dict
        enrichment_data: Optional SDK enrichment data
        campaign_context: Optional campaign context
        client_intelligence: Optional client proof points
        sequence_length: Number of emails to generate (1-5)
        client_id: Optional client ID

    Returns:
        List of email dicts for the sequence
    """
    sequence_length = min(max(sequence_length, 1), 5)  # Clamp to 1-5

    sequence_prompts = [
        ("initial", "This is the FIRST email in a sequence. Focus on the strongest personalization hook from research."),
        ("follow_up_1", "This is a FOLLOW-UP email. They haven't replied. Try a different angle - maybe focus on a different pain point or news item."),
        ("follow_up_2", "This is the SECOND FOLLOW-UP. Be brief. Reference that you've reached out before. Try a completely different hook."),
        ("value_add", "This is a VALUE-ADD email. Share something useful (insight, stat, resource) without asking for anything."),
        ("break_up", "This is a BREAK-UP email. Final attempt. Be respectful, mention you won't follow up again. Light urgency but no pressure."),
    ]

    emails = []

    for i in range(sequence_length):
        sequence_type, instruction = sequence_prompts[i]

        # Modify campaign context with sequence info
        modified_context = {
            **(campaign_context or {}),
            "sequence_position": i + 1,
            "sequence_type": sequence_type,
            "sequence_instruction": instruction,
        }

        result = await run_sdk_email(
            lead_data=lead_data,
            enrichment_data=enrichment_data,
            campaign_context=modified_context,
            client_intelligence=client_intelligence,
            client_id=client_id,
        )

        if result.success and result.data:
            email_data = result.data.model_dump() if isinstance(result.data, EmailOutput) else result.data
            emails.append({
                **email_data,
                "sequence_position": i + 1,
                "sequence_type": sequence_type,
                "source": "sdk",
                "cost_aud": result.cost_aud,
            })
        else:
            # Log failure but continue with remaining emails
            logger.warning(f"Failed to generate email {i + 1} in sequence: {result.error}")

    return emails
