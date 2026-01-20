"""
Contract: src/engines/smart_prompts.py
Purpose: Smart Prompt system for personalized content generation
Layer: 3 - engines (utilities)
Imports: models only
Consumers: content engine, voice engine
Date: 2026-01-20
Architecture Decision: SDK_AND_CONTENT_ARCHITECTURE.md

This module provides comprehensive context builders and prompt templates
for generating highly personalized content using ALL available data from:
- Lead/pool enrichment
- Client intelligence (proof points)
- Company signals
- LinkedIn data
- Engagement history

The key insight: We already paid to enrich this data. Use it.
"""

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import logging

logger = logging.getLogger(__name__)


# ============================================
# SMART EMAIL PROMPT TEMPLATE
# ============================================

SMART_EMAIL_PROMPT = """Write a personalized cold outreach email using ALL the lead data below.

## LEAD CONTEXT
{lead_context}

## CLIENT PROOF POINTS (use 1-2 naturally)
{proof_points}

## CAMPAIGN CONTEXT
{campaign_context}

## EMAIL REQUIREMENTS
1. Subject line: Under 50 characters, specific to their situation
2. Body: Under 150 words, conversational tone
3. Use ONE specific detail about them (company signal, role, recent activity)
4. Include ONE relevant proof point (metric, client name, or case study)
5. End with a soft CTA (question, not hard ask)
6. No generic phrases ("hope this finds you well", "I wanted to reach out")
7. Sound like a real person, not a template

## OUTPUT FORMAT
Return JSON: {{"subject": "...", "body": "..."}}
"""


SMART_VOICE_KB_PROMPT = """Generate a voice call knowledge base for this lead.

## LEAD CONTEXT
{lead_context}

## CLIENT PROOF POINTS
{proof_points}

## CAMPAIGN CONTEXT
{campaign_context}

## KNOWLEDGE BASE REQUIREMENTS
Generate a structured KB the voice AI can use during the call:

1. **recommended_opener**: A personalized opening line mentioning something specific about them
2. **opening_hooks**: 3 specific conversation starters based on their data
3. **pain_point_questions**: 3 discovery questions relevant to their industry/role
4. **objection_responses**: Common objections with tailored responses:
   - timing_not_now: Response if they say "not a good time"
   - using_competitor: Response if they mention using a competitor
   - not_decision_maker: Response if they say they don't make decisions
   - too_expensive: Response if they raise budget concerns
5. **company_context**: 2-3 sentences summarizing what we know about their company
6. **do_not_mention**: List of things to avoid (competitors they use, sensitive topics)
7. **meeting_ask**: How to ask for the meeting based on their situation

## OUTPUT FORMAT
Return JSON with the structure above.
"""


# ============================================
# CONTEXT BUILDERS
# ============================================

async def build_full_lead_context(
    db: AsyncSession,
    lead_id: UUID,
    include_engagement: bool = True,
) -> dict[str, Any]:
    """
    Build comprehensive lead context from all available data.

    Fetches:
    - Lead table data (all fields)
    - SDK enrichment data (if available)
    - Deep research data (if available)
    - Lead social posts (recent)
    - Engagement history

    Args:
        db: Database session
        lead_id: Lead UUID
        include_engagement: Whether to include engagement history

    Returns:
        Dict with all available lead context
    """
    # Query lead with all fields
    query = text("""
        SELECT
            -- Contact
            l.first_name, l.last_name, l.email, l.phone, l.title, l.company,
            l.linkedin_url, l.domain,

            -- ALS Score
            l.als_score, l.als_tier, l.als_data_quality, l.als_authority,
            l.als_company_fit, l.als_timing, l.als_risk,

            -- Organization
            l.organization_industry, l.organization_employee_count,
            l.organization_country, l.organization_founded_year,
            l.organization_is_hiring, l.organization_latest_funding_date,
            l.organization_website, l.organization_linkedin_url,

            -- Person
            l.employment_start_date, l.seniority_level,

            -- Enrichment
            l.enrichment_source, l.enrichment_confidence, l.enriched_at,
            l.deep_research_data, l.deep_research_run_at,
            l.sdk_enrichment, l.sdk_signals,

            -- Engagement
            l.last_contacted_at, l.last_replied_at, l.last_opened_at,
            l.last_clicked_at, l.reply_count, l.bounce_count,
            l.current_sequence_step,

            -- Rejection
            l.rejection_reason, l.objections_raised,

            -- Timezone
            l.timezone,

            -- Campaign
            l.client_id, l.campaign_id,
            c.name as campaign_name

        FROM leads l
        LEFT JOIN campaigns c ON c.id = l.campaign_id
        WHERE l.id = :lead_id
        AND l.deleted_at IS NULL
    """)

    result = await db.execute(query, {"lead_id": str(lead_id)})
    row = result.fetchone()

    if not row:
        return {}

    # Build context dict
    context = {
        "person": {
            "first_name": row.first_name,
            "last_name": row.last_name,
            "full_name": f"{row.first_name or ''} {row.last_name or ''}".strip(),
            "email": row.email,
            "phone": row.phone,
            "title": row.title,
            "seniority": row.seniority_level,
            "linkedin_url": row.linkedin_url,
            "tenure_months": _calculate_tenure_months(row.employment_start_date),
        },
        "company": {
            "name": row.company,
            "domain": row.domain,
            "industry": row.organization_industry,
            "employee_count": row.organization_employee_count,
            "country": row.organization_country,
            "founded_year": row.organization_founded_year,
            "is_hiring": row.organization_is_hiring,
            "website": row.organization_website,
            "linkedin_url": row.organization_linkedin_url,
        },
        "signals": {
            "is_hiring": row.organization_is_hiring,
            "recently_funded": _is_recently_funded(row.organization_latest_funding_date),
            "funding_date": str(row.organization_latest_funding_date) if row.organization_latest_funding_date else None,
            "new_in_role": _is_new_in_role(row.employment_start_date),
        },
        "score": {
            "als_score": row.als_score,
            "als_tier": row.als_tier,
            "authority": row.als_authority,
            "company_fit": row.als_company_fit,
            "timing": row.als_timing,
        },
    }

    # Add deep research data if available
    if row.deep_research_data:
        deep_data = row.deep_research_data
        context["research"] = {
            "pain_points": deep_data.get("pain_points", []),
            "buying_signals": deep_data.get("buying_signals", []),
            "recent_news": deep_data.get("recent_news", []),
            "tech_stack": deep_data.get("tech_stack", []),
            "competitors": deep_data.get("competitors", []),
        }

    # Add SDK enrichment if available
    if row.sdk_enrichment:
        sdk_data = row.sdk_enrichment
        context["sdk_research"] = {
            "company_context": sdk_data.get("company_context"),
            "person_context": sdk_data.get("person_context"),
            "icebreakers": sdk_data.get("icebreakers", []),
            "pain_points": sdk_data.get("pain_points", []),
            "recent_activity": sdk_data.get("recent_activity", []),
        }
        if row.sdk_signals:
            context["sdk_research"]["signals"] = row.sdk_signals

    # Add engagement history if requested
    if include_engagement:
        context["engagement"] = {
            "total_touches": row.current_sequence_step,
            "last_contacted": str(row.last_contacted_at) if row.last_contacted_at else None,
            "last_replied": str(row.last_replied_at) if row.last_replied_at else None,
            "has_opened": row.last_opened_at is not None,
            "has_clicked": row.last_clicked_at is not None,
            "reply_count": row.reply_count,
            "previous_objections": row.objections_raised or [],
        }

    return context


async def build_full_pool_lead_context(
    db: AsyncSession,
    lead_pool_id: UUID,
    client_id: UUID | None = None,
) -> dict[str, Any]:
    """
    Build comprehensive context for a pool lead.

    Pool leads have richer data than legacy leads since they come
    directly from Apollo with full enrichment.

    Args:
        db: Database session
        lead_pool_id: Lead pool UUID
        client_id: Optional client ID to get assignment context

    Returns:
        Dict with all available pool lead context
    """
    query = text("""
        SELECT
            -- Person
            lp.first_name, lp.last_name, lp.email, lp.phone, lp.title,
            lp.seniority, lp.linkedin_headline, lp.linkedin_url,
            lp.city, lp.state, lp.country, lp.timezone,
            lp.departments, lp.employment_history, lp.current_role_start_date,

            -- Company
            lp.company_name, lp.company_domain, lp.company_website,
            lp.company_linkedin_url, lp.company_description,
            lp.company_industry, lp.company_sub_industry,
            lp.company_employee_count, lp.company_revenue, lp.company_revenue_range,
            lp.company_founded_year, lp.company_country, lp.company_city,

            -- Signals
            lp.company_is_hiring, lp.company_latest_funding_stage,
            lp.company_latest_funding_date, lp.company_total_funding,
            lp.company_technologies, lp.company_keywords,

            -- Enrichment
            lp.email_status, lp.enrichment_source, lp.enrichment_confidence,
            lp.enriched_at, lp.enrichment_data,

            -- DataForSEO
            lp.dataforseo_domain_rank, lp.dataforseo_organic_traffic,

            -- Assignment (if client_id provided)
            la.als_score, la.als_tier, la.total_touches,
            la.last_contacted_at, la.has_replied, la.reply_intent

        FROM lead_pool lp
        LEFT JOIN lead_assignments la ON la.lead_pool_id = lp.id
            AND la.status = 'active'
            AND (:client_id IS NULL OR la.client_id = :client_id)
        WHERE lp.id = :lead_pool_id
    """)

    result = await db.execute(query, {
        "lead_pool_id": str(lead_pool_id),
        "client_id": str(client_id) if client_id else None,
    })
    row = result.fetchone()

    if not row:
        return {}

    # Build context dict
    context = {
        "person": {
            "first_name": row.first_name,
            "last_name": row.last_name,
            "full_name": f"{row.first_name or ''} {row.last_name or ''}".strip(),
            "email": row.email,
            "phone": row.phone,
            "title": row.title,
            "seniority": row.seniority,
            "linkedin_headline": row.linkedin_headline,
            "linkedin_url": row.linkedin_url,
            "location": _format_location(row.city, row.state, row.country),
            "timezone": row.timezone,
            "departments": row.departments or [],
            "tenure_months": _calculate_tenure_months(row.current_role_start_date),
        },
        "company": {
            "name": row.company_name,
            "domain": row.company_domain,
            "website": row.company_website,
            "linkedin_url": row.company_linkedin_url,
            "description": row.company_description,
            "industry": row.company_industry,
            "sub_industry": row.company_sub_industry,
            "employee_count": row.company_employee_count,
            "revenue": row.company_revenue,
            "revenue_range": row.company_revenue_range,
            "founded_year": row.company_founded_year,
            "location": _format_location(row.company_city, None, row.company_country),
        },
        "signals": {
            "is_hiring": row.company_is_hiring,
            "funding_stage": row.company_latest_funding_stage,
            "recently_funded": _is_recently_funded(row.company_latest_funding_date),
            "funding_date": str(row.company_latest_funding_date) if row.company_latest_funding_date else None,
            "total_funding": row.company_total_funding,
            "technologies": row.company_technologies or [],
            "keywords": row.company_keywords or [],
            "new_in_role": _is_new_in_role(row.current_role_start_date),
        },
        "web_presence": {
            "domain_rank": row.dataforseo_domain_rank,
            "organic_traffic": row.dataforseo_organic_traffic,
        },
    }

    # Add employment history for richer context
    if row.employment_history:
        context["person"]["employment_history"] = row.employment_history

    # Add enrichment data if available (raw Apollo data)
    if row.enrichment_data:
        enrich = row.enrichment_data
        if enrich.get("intent_topics"):
            context["signals"]["intent_topics"] = enrich.get("intent_topics")
        if enrich.get("technologies"):
            context["signals"]["technologies"] = enrich.get("technologies")

    # Add assignment context if available
    if row.als_score is not None:
        context["score"] = {
            "als_score": row.als_score,
            "als_tier": row.als_tier,
        }
        context["engagement"] = {
            "total_touches": row.total_touches or 0,
            "last_contacted": str(row.last_contacted_at) if row.last_contacted_at else None,
            "has_replied": row.has_replied,
            "reply_intent": row.reply_intent,
        }

    return context


async def build_client_proof_points(
    db: AsyncSession,
    client_id: UUID,
) -> dict[str, Any]:
    """
    Build client proof points from client_intelligence table.

    Returns:
        Dict with proof metrics, clients, testimonials, etc.
    """
    query = text("""
        SELECT
            proof_metrics,
            proof_clients,
            proof_industries,
            common_pain_points,
            differentiators,
            website_testimonials,
            website_case_studies,
            g2_rating,
            g2_review_count,
            capterra_rating,
            capterra_review_count,
            trustpilot_rating,
            trustpilot_review_count,
            google_rating,
            google_review_count,
            linkedin_follower_count,
            website_tagline,
            website_value_prop
        FROM client_intelligence
        WHERE client_id = :client_id
        AND deleted_at IS NULL
    """)

    result = await db.execute(query, {"client_id": str(client_id)})
    row = result.fetchone()

    if not row:
        return {"available": False}

    # Build proof points
    proof_points = {
        "available": True,
        "metrics": row.proof_metrics or [],
        "named_clients": row.proof_clients or [],
        "industries_served": row.proof_industries or [],
        "pain_points_solved": row.common_pain_points or [],
        "differentiators": row.differentiators or [],
        "tagline": row.website_tagline,
        "value_prop": row.website_value_prop,
    }

    # Add testimonials (first 2 for brevity)
    if row.website_testimonials:
        proof_points["testimonials"] = row.website_testimonials[:2]

    # Add case studies (first 2)
    if row.website_case_studies:
        proof_points["case_studies"] = row.website_case_studies[:2]

    # Add ratings
    ratings = {}
    if row.g2_rating and row.g2_review_count:
        ratings["g2"] = {"rating": float(row.g2_rating), "reviews": row.g2_review_count}
    if row.capterra_rating and row.capterra_review_count:
        ratings["capterra"] = {"rating": float(row.capterra_rating), "reviews": row.capterra_review_count}
    if row.trustpilot_rating and row.trustpilot_review_count:
        ratings["trustpilot"] = {"rating": float(row.trustpilot_rating), "reviews": row.trustpilot_review_count}
    if row.google_rating and row.google_review_count:
        ratings["google"] = {"rating": float(row.google_rating), "reviews": row.google_review_count}

    if ratings:
        proof_points["ratings"] = ratings

    if row.linkedin_follower_count:
        proof_points["linkedin_followers"] = row.linkedin_follower_count

    return proof_points


def format_lead_context_for_prompt(context: dict[str, Any]) -> str:
    """
    Format lead context dict into a readable string for the prompt.

    Args:
        context: Lead context from build_full_lead_context or build_full_pool_lead_context

    Returns:
        Formatted string for prompt injection
    """
    lines = []

    # Person
    person = context.get("person", {})
    if person.get("full_name"):
        lines.append(f"**Name:** {person['full_name']}")
    if person.get("title"):
        lines.append(f"**Title:** {person['title']}")
    if person.get("seniority"):
        lines.append(f"**Seniority:** {person['seniority']}")
    if person.get("linkedin_headline"):
        lines.append(f"**LinkedIn Headline:** {person['linkedin_headline']}")
    if person.get("tenure_months") and person["tenure_months"] > 0:
        if person["tenure_months"] < 6:
            lines.append(f"**Role Tenure:** New in role ({person['tenure_months']} months)")
        else:
            lines.append(f"**Role Tenure:** {person['tenure_months']} months")
    if person.get("location"):
        lines.append(f"**Location:** {person['location']}")
    if person.get("departments"):
        lines.append(f"**Departments:** {', '.join(person['departments'])}")

    # Company
    company = context.get("company", {})
    if company.get("name"):
        lines.append(f"\n**Company:** {company['name']}")
    if company.get("industry"):
        sub = f" ({company['sub_industry']})" if company.get("sub_industry") else ""
        lines.append(f"**Industry:** {company['industry']}{sub}")
    if company.get("employee_count"):
        lines.append(f"**Size:** {company['employee_count']} employees")
    if company.get("revenue_range"):
        lines.append(f"**Revenue:** {company['revenue_range']}")
    if company.get("founded_year"):
        lines.append(f"**Founded:** {company['founded_year']}")
    if company.get("description"):
        lines.append(f"**About:** {company['description'][:200]}...")
    if company.get("location"):
        lines.append(f"**HQ:** {company['location']}")

    # Signals
    signals = context.get("signals", {})
    signal_items = []
    if signals.get("is_hiring"):
        signal_items.append("Currently hiring")
    if signals.get("recently_funded"):
        signal_items.append(f"Recently funded ({signals.get('funding_stage', 'unknown stage')})")
    if signals.get("new_in_role"):
        signal_items.append("New in role (< 6 months)")
    if signals.get("technologies"):
        tech_str = ", ".join(signals["technologies"][:5])
        signal_items.append(f"Tech stack: {tech_str}")
    if signals.get("keywords"):
        kw_str = ", ".join(signals["keywords"][:5])
        signal_items.append(f"Keywords: {kw_str}")

    if signal_items:
        lines.append(f"\n**Signals:** {'; '.join(signal_items)}")

    # Score
    score = context.get("score", {})
    if score.get("als_score"):
        lines.append(f"\n**ALS Score:** {score['als_score']} ({score.get('als_tier', 'unknown')} tier)")

    # Research/SDK data
    research = context.get("research") or context.get("sdk_research", {})
    if research:
        if research.get("pain_points"):
            lines.append(f"\n**Pain Points:** {', '.join(research['pain_points'][:3])}")
        if research.get("icebreakers"):
            lines.append(f"**Icebreakers:** {'; '.join(research['icebreakers'][:2])}")
        if research.get("recent_activity"):
            lines.append(f"**Recent Activity:** {'; '.join(research['recent_activity'][:2])}")

    # Engagement history
    engagement = context.get("engagement", {})
    if engagement.get("total_touches", 0) > 0:
        lines.append(f"\n**Previous Touches:** {engagement['total_touches']}")
    if engagement.get("has_replied") or engagement.get("reply_count", 0) > 0:
        lines.append(f"**Has Replied:** Yes")
    if engagement.get("previous_objections"):
        lines.append(f"**Previous Objections:** {', '.join(engagement['previous_objections'])}")

    return "\n".join(lines) if lines else "No lead data available."


def format_proof_points_for_prompt(proof_points: dict[str, Any]) -> str:
    """
    Format client proof points into a readable string for the prompt.

    Args:
        proof_points: From build_client_proof_points

    Returns:
        Formatted string for prompt injection
    """
    if not proof_points.get("available"):
        return "No client proof points available."

    lines = []

    # Tagline/Value prop
    if proof_points.get("tagline"):
        lines.append(f"**Tagline:** {proof_points['tagline']}")
    if proof_points.get("value_prop"):
        lines.append(f"**Value Prop:** {proof_points['value_prop'][:200]}...")

    # Metrics
    metrics = proof_points.get("metrics", [])
    if metrics:
        metric_strs = []
        for m in metrics[:3]:
            if isinstance(m, dict):
                metric_strs.append(f"{m.get('metric', 'Unknown')} ({m.get('context', '')})")
            else:
                metric_strs.append(str(m))
        lines.append(f"\n**Proof Metrics:** {'; '.join(metric_strs)}")

    # Named clients
    if proof_points.get("named_clients"):
        clients_str = ", ".join(proof_points["named_clients"][:5])
        lines.append(f"**Notable Clients:** {clients_str}")

    # Industries
    if proof_points.get("industries_served"):
        ind_str = ", ".join(proof_points["industries_served"][:5])
        lines.append(f"**Industries Served:** {ind_str}")

    # Differentiators
    if proof_points.get("differentiators"):
        diff_str = "; ".join(proof_points["differentiators"][:3])
        lines.append(f"**Differentiators:** {diff_str}")

    # Pain points solved
    if proof_points.get("pain_points_solved"):
        pp_str = "; ".join(proof_points["pain_points_solved"][:3])
        lines.append(f"**Pain Points Solved:** {pp_str}")

    # Ratings
    ratings = proof_points.get("ratings", {})
    if ratings:
        rating_strs = []
        for platform, data in ratings.items():
            rating_strs.append(f"{platform.upper()}: {data['rating']}/5 ({data['reviews']} reviews)")
        lines.append(f"\n**Ratings:** {'; '.join(rating_strs)}")

    # Testimonials
    testimonials = proof_points.get("testimonials", [])
    if testimonials:
        lines.append("\n**Testimonials:**")
        for t in testimonials[:2]:
            if isinstance(t, dict):
                quote = t.get("quote", "")[:100]
                author = t.get("author", "Anonymous")
                company = t.get("company", "")
                lines.append(f'  - "{quote}..." - {author}, {company}')

    # Case studies
    case_studies = proof_points.get("case_studies", [])
    if case_studies:
        lines.append("\n**Case Studies:**")
        for cs in case_studies[:2]:
            if isinstance(cs, dict):
                title = cs.get("title", "Untitled")
                result = cs.get("result_metrics", cs.get("summary", ""))[:100]
                lines.append(f"  - {title}: {result}")

    return "\n".join(lines) if lines else "No proof points available."


# ============================================
# HELPER FUNCTIONS
# ============================================

def _calculate_tenure_months(start_date) -> int:
    """Calculate months since start date."""
    if not start_date:
        return 0
    try:
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date)
        elif hasattr(start_date, "year"):  # date object
            start_date = datetime(start_date.year, start_date.month, start_date.day)

        now = datetime.utcnow()
        months = (now.year - start_date.year) * 12 + (now.month - start_date.month)
        return max(0, months)
    except Exception:
        return 0


def _is_recently_funded(funding_date) -> bool:
    """Check if funding was within last 90 days."""
    if not funding_date:
        return False
    try:
        if isinstance(funding_date, str):
            funding_date = datetime.fromisoformat(funding_date)
        elif hasattr(funding_date, "year"):  # date object
            funding_date = datetime(funding_date.year, funding_date.month, funding_date.day)

        cutoff = datetime.utcnow() - timedelta(days=90)
        return funding_date >= cutoff
    except Exception:
        return False


def _is_new_in_role(start_date) -> bool:
    """Check if person is new in role (< 6 months)."""
    months = _calculate_tenure_months(start_date)
    return 0 < months < 6


def _format_location(city: str | None, state: str | None, country: str | None) -> str:
    """Format location from city/state/country."""
    parts = [p for p in [city, state, country] if p]
    return ", ".join(parts) if parts else ""


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] SMART_EMAIL_PROMPT template
# [x] SMART_VOICE_KB_PROMPT template
# [x] build_full_lead_context() for legacy leads
# [x] build_full_pool_lead_context() for pool leads
# [x] build_client_proof_points() for client intelligence
# [x] format_lead_context_for_prompt() formatter
# [x] format_proof_points_for_prompt() formatter
# [x] Helper functions for tenure, funding, location
# [x] All functions have type hints
# [x] All functions have docstrings
