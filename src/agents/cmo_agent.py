"""
Contract: src/agents/cmo_agent.py
Purpose: CMO (Chief Marketing Officer) agent for orchestration decisions
Layer: 4 - agents
Imports: models, engines, agents.base_agent
Consumers: orchestration flows

FILE: src/agents/cmo_agent.py
PURPOSE: CMO (Chief Marketing Officer) agent for orchestration decisions
PHASE: 6 (Agents)
TASK: AGT-002
DEPENDENCIES:
  - src/agents/base_agent.py
  - src/models/campaign.py
  - src/models/lead.py
  - src/engines/scorer.py
  - src/engines/allocator.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument (DI pattern)
  - Rule 12: Can import from engines, integrations, models
  - Rule 15: AI spend limiter via base agent
  - Pydantic AI for type-safe validation
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.base_agent import AgentResult, BaseAgent
from src.models.campaign import Campaign
from src.models.lead import Lead

# ============================================
# Output Models for Structured Responses
# ============================================


class CampaignAnalysis(BaseModel):
    """Campaign analysis result from CMO agent."""

    campaign_id: str
    campaign_name: str
    recommendation: str  # activate, pause, modify, continue
    reasoning: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    metrics: dict[str, Any] = Field(default_factory=dict)
    suggested_changes: list[str] = Field(default_factory=list)


class ChannelRecommendation(BaseModel):
    """Channel mix recommendation for a lead."""

    lead_id: str
    als_score: int
    als_tier: str
    recommended_channels: list[str]
    reasoning: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    priority_order: list[str] = Field(default_factory=list)
    budget_estimate_aud: float = 0.0


class LeadPrioritization(BaseModel):
    """Lead prioritization result."""

    campaign_id: str
    total_leads: int
    prioritized_leads: list[dict[str, Any]]
    tier_distribution: dict[str, int]
    reasoning: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    top_10_lead_ids: list[str] = Field(default_factory=list)


class TimingRecommendation(BaseModel):
    """Sequence timing recommendation."""

    lead_id: str
    current_step: int
    next_step: int
    recommended_delay_hours: int
    next_channel: str
    reasoning: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    send_at: str  # ISO datetime string


# ============================================
# CMO Agent
# ============================================


class CMOAgent(BaseAgent):
    """
    CMO (Chief Marketing Officer) AI Agent.

    Makes strategic decisions about:
    - Campaign activation, pausing, modification
    - Lead prioritization based on ALS scores
    - Channel mix selection for optimal conversion
    - Sequence timing and cadence
    - Budget allocation across campaigns

    Uses Pydantic AI with structured outputs for type-safe decisions.
    """

    @property
    def name(self) -> str:
        return "cmo"

    @property
    def system_prompt(self) -> str:
        return """You are the Chief Marketing Officer (CMO) AI for Agency OS.

Your role is to make strategic marketing decisions to maximize campaign ROI and lead conversion.

Core Responsibilities:
1. Campaign Strategy: Decide when to activate, pause, or modify campaigns based on performance metrics
2. Lead Prioritization: Rank leads by conversion potential using ALS scores and engagement data
3. Channel Selection: Recommend optimal channel mix (Email, SMS, LinkedIn, Voice, Direct Mail) for each lead
4. Timing Optimization: Determine ideal sequence timing to maximize reply rates
5. Budget Management: Allocate resources across campaigns for best ROI

Decision Framework:
- ALS Tiers:
  * Hot (85-100): All channels, high priority, premium touches (voice, mail)
  * Warm (60-84): Email, LinkedIn, Voice - strong prospects
  * Cool (35-59): Email, LinkedIn - nurture sequence
  * Cold (20-34): Email only - low-cost touches
  * Dead (0-19): Suppress, do not contact

- Channel Effectiveness Hierarchy:
  1. Voice calls (highest conversion, ALS 70+ only)
  2. LinkedIn (personal connection, professional context)
  3. Direct Mail (premium, ALS 85+ only)
  4. Email (scalable, threading for context)
  5. SMS (immediate, use sparingly)

- Timing Principles:
  * Business hours: 9 AM - 5 PM AEST Mon-Fri
  * Initial touch: 24-48 hours after enrichment
  * Follow-up cadence: 3-5 days for first 3 steps, then weekly
  * Stop after 7 steps or reply (whichever comes first)

- Campaign Health Indicators:
  * Reply rate > 5%: Excellent, continue
  * Reply rate 2-5%: Good, optimize
  * Reply rate < 2%: Review messaging/targeting
  * Bounce rate > 10%: Data quality issue
  * Unsubscribe rate > 1%: Messaging issue

Always provide clear reasoning and confidence scores. Be strategic but data-driven.
Australian market focus - professional, direct, value-oriented messaging."""

    async def analyze_campaign(
        self,
        db: AsyncSession,
        campaign_id: UUID,
    ) -> AgentResult[CampaignAnalysis]:
        """
        Analyze campaign performance and recommend actions.

        Args:
            db: Database session (passed by caller)
            campaign_id: Campaign UUID to analyze

        Returns:
            AgentResult with CampaignAnalysis
        """
        # Check budget
        if not await self.check_budget(estimated_tokens=2000):
            return AgentResult.fail("AI spend limit exceeded")

        # Get campaign with metrics
        stmt = select(Campaign).where(
            and_(
                Campaign.id == campaign_id,
                Campaign.deleted_at.is_(None),
            )
        )
        result = await db.execute(stmt)
        campaign = result.scalar_one_or_none()

        if not campaign:
            return AgentResult.fail(f"Campaign {campaign_id} not found")

        # Calculate metrics
        reply_rate = campaign.reply_rate
        conversion_rate = campaign.conversion_rate
        bounce_rate = (
            (campaign.total_leads - campaign.leads_contacted) / campaign.total_leads * 100
            if campaign.total_leads > 0
            else 0.0
        )

        # Get tier distribution
        tier_dist = await self._get_tier_distribution(db, campaign_id)

        # Prepare context for agent
        metrics_summary = f"""
Campaign: {campaign.name}
Status: {campaign.status.value}
Total Leads: {campaign.total_leads}
Contacted: {campaign.leads_contacted}
Replied: {campaign.leads_replied}
Converted: {campaign.leads_converted}
Reply Rate: {reply_rate:.2f}%
Conversion Rate: {conversion_rate:.2f}%
Bounce Rate: {bounce_rate:.2f}%
Tier Distribution: {tier_dist}
Channel Allocation: Email {campaign.allocation_email}%, SMS {campaign.allocation_sms}%, LinkedIn {campaign.allocation_linkedin}%, Voice {campaign.allocation_voice}%, Mail {campaign.allocation_mail}%
"""

        prompt = f"""Analyze this campaign and recommend next steps:

{metrics_summary}

Based on the metrics, should we:
1. ACTIVATE: Start/resume the campaign
2. PAUSE: Stop the campaign
3. MODIFY: Adjust targeting, messaging, or channel mix
4. CONTINUE: Keep running as-is

Provide specific reasoning and actionable suggestions."""

        # Create agent with structured output
        agent = self.create_agent(result_type=CampaignAnalysis)

        try:
            # Run agent
            result = await agent.run(prompt)

            # Record usage
            cost = await self.record_usage(
                input_tokens=len(prompt.split()) * 2,  # Rough estimate
                output_tokens=len(str(result.data)) * 2,
            )

            return AgentResult.ok(
                data=result.data,
                reasoning=result.data.reasoning,
                confidence=result.data.confidence,
                tokens_used=(len(prompt.split()) + len(str(result.data))) * 2,
                cost_aud=cost,
            )

        except Exception as e:
            return AgentResult.fail(f"Campaign analysis failed: {str(e)}")

    async def recommend_channel_mix(
        self,
        db: AsyncSession,
        lead_id: UUID,
    ) -> AgentResult[ChannelRecommendation]:
        """
        Recommend optimal channel mix for a lead.

        Args:
            db: Database session (passed by caller)
            lead_id: Lead UUID

        Returns:
            AgentResult with ChannelRecommendation
        """
        # Check budget
        if not await self.check_budget(estimated_tokens=1500):
            return AgentResult.fail("AI spend limit exceeded")

        # Get lead with ALS data
        stmt = select(Lead).where(
            and_(
                Lead.id == lead_id,
                Lead.deleted_at.is_(None),
            )
        )
        result = await db.execute(stmt)
        lead = result.scalar_one_or_none()

        if not lead:
            return AgentResult.fail(f"Lead {lead_id} not found")

        if not lead.als_score:
            return AgentResult.fail(f"Lead {lead_id} not scored yet")

        # Prepare lead profile
        lead_profile = f"""
Lead: {lead.full_name}
Email: {lead.email}
Phone: {lead.phone or "N/A"}
LinkedIn: {lead.linkedin_url or "N/A"}
Title: {lead.title or "N/A"}
Company: {lead.company or "N/A"}

ALS Score: {lead.als_score}
ALS Tier: {lead.als_tier or lead.get_als_tier()}
Component Scores:
- Data Quality: {lead.als_data_quality}/20
- Authority: {lead.als_authority}/25
- Company Fit: {lead.als_company_fit}/25
- Timing: {lead.als_timing}/15
- Risk: {lead.als_risk}/15

Organization:
- Industry: {lead.organization_industry or "N/A"}
- Size: {lead.organization_employee_count or "N/A"} employees
- Hiring: {lead.organization_is_hiring or False}
- Recent Funding: {lead.organization_latest_funding_date or "N/A"}

Engagement:
- Last Contacted: {lead.last_contacted_at or "Never"}
- Reply Count: {lead.reply_count}
- Current Step: {lead.current_sequence_step}
"""

        prompt = f"""Recommend the optimal channel mix for this lead:

{lead_profile}

Based on their ALS tier and profile, which channels should we use?
Available channels: Email, SMS, LinkedIn, Voice, Direct Mail

Provide priority order and reasoning for channel selection."""

        # Create agent with structured output
        agent = self.create_agent(result_type=ChannelRecommendation)

        try:
            # Run agent
            result = await agent.run(prompt)

            # Record usage
            cost = await self.record_usage(
                input_tokens=len(prompt.split()) * 2,
                output_tokens=len(str(result.data)) * 2,
            )

            return AgentResult.ok(
                data=result.data,
                reasoning=result.data.reasoning,
                confidence=result.data.confidence,
                tokens_used=(len(prompt.split()) + len(str(result.data))) * 2,
                cost_aud=cost,
            )

        except Exception as e:
            return AgentResult.fail(f"Channel recommendation failed: {str(e)}")

    async def prioritize_leads(
        self,
        db: AsyncSession,
        campaign_id: UUID,
        lead_ids: list[UUID],
    ) -> AgentResult[LeadPrioritization]:
        """
        Prioritize leads for outreach within a campaign.

        Args:
            db: Database session (passed by caller)
            campaign_id: Campaign UUID
            lead_ids: List of lead UUIDs to prioritize

        Returns:
            AgentResult with LeadPrioritization
        """
        # Check budget
        if not await self.check_budget(estimated_tokens=2500):
            return AgentResult.fail("AI spend limit exceeded")

        # Get leads with scoring data
        stmt = (
            select(Lead)
            .where(
                and_(
                    Lead.id.in_(lead_ids),
                    Lead.campaign_id == campaign_id,
                    Lead.deleted_at.is_(None),
                )
            )
            .order_by(Lead.als_score.desc())
        )
        result = await db.execute(stmt)
        leads = result.scalars().all()

        if not leads:
            return AgentResult.fail(f"No leads found for campaign {campaign_id}")

        # Build tier distribution
        tier_dist = {"hot": 0, "warm": 0, "cool": 0, "cold": 0, "dead": 0}
        for lead in leads:
            tier = lead.get_als_tier()
            tier_dist[tier] = tier_dist.get(tier, 0) + 1

        # Prepare lead summaries
        lead_summaries = []
        for i, lead in enumerate(leads[:20], 1):  # Top 20 for analysis
            lead_summaries.append(
                f"{i}. {lead.full_name} ({lead.company}) - ALS {lead.als_score} ({lead.get_als_tier()}) - "
                f"Step {lead.current_sequence_step}, Replies {lead.reply_count}"
            )

        leads_summary = "\n".join(lead_summaries)

        prompt = f"""Prioritize these leads for outreach:

Campaign: {campaign_id}
Total Leads: {len(leads)}
Tier Distribution: {tier_dist}

Top Leads:
{leads_summary}

Recommend the prioritization strategy. Which leads should we contact first?
Consider ALS score, tier, engagement history, and sequence position."""

        # Create agent with structured output
        agent = self.create_agent(result_type=LeadPrioritization)

        try:
            # Build prioritized list
            prioritized = []
            for lead in leads:
                prioritized.append(
                    {
                        "lead_id": str(lead.id),
                        "name": lead.full_name,
                        "company": lead.company,
                        "als_score": lead.als_score,
                        "als_tier": lead.get_als_tier(),
                        "current_step": lead.current_sequence_step,
                        "reply_count": lead.reply_count,
                    }
                )

            # Run agent
            result = await agent.run(prompt)

            # Add our computed data
            result.data.prioritized_leads = prioritized
            result.data.tier_distribution = tier_dist
            result.data.top_10_lead_ids = [str(lead.id) for lead in leads[:10]]

            # Record usage
            cost = await self.record_usage(
                input_tokens=len(prompt.split()) * 2,
                output_tokens=len(str(result.data)) * 2,
            )

            return AgentResult.ok(
                data=result.data,
                reasoning=result.data.reasoning,
                confidence=result.data.confidence,
                tokens_used=(len(prompt.split()) + len(str(result.data))) * 2,
                cost_aud=cost,
            )

        except Exception as e:
            return AgentResult.fail(f"Lead prioritization failed: {str(e)}")

    async def suggest_sequence_timing(
        self,
        db: AsyncSession,
        lead_id: UUID,
    ) -> AgentResult[TimingRecommendation]:
        """
        Suggest optimal timing for next sequence step.

        Args:
            db: Database session (passed by caller)
            lead_id: Lead UUID

        Returns:
            AgentResult with TimingRecommendation
        """
        # Check budget
        if not await self.check_budget(estimated_tokens=1200):
            return AgentResult.fail("AI spend limit exceeded")

        # Get lead
        stmt = select(Lead).where(
            and_(
                Lead.id == lead_id,
                Lead.deleted_at.is_(None),
            )
        )
        result = await db.execute(stmt)
        lead = result.scalar_one_or_none()

        if not lead:
            return AgentResult.fail(f"Lead {lead_id} not found")

        # Get campaign for sequence info
        stmt_campaign = select(Campaign).where(Campaign.id == lead.campaign_id)
        result_campaign = await db.execute(stmt_campaign)
        campaign = result_campaign.scalar_one_or_none()

        if not campaign:
            return AgentResult.fail(f"Campaign not found for lead {lead_id}")

        # Prepare timing context
        timing_context = f"""
Lead: {lead.full_name} ({lead.company})
ALS Score: {lead.als_score} ({lead.get_als_tier()})

Current Sequence:
- Current Step: {lead.current_sequence_step}
- Total Steps: {campaign.sequence_steps}
- Default Delay: {campaign.sequence_delay_days} days

Engagement History:
- Last Contacted: {lead.last_contacted_at or "Never"}
- Last Replied: {lead.last_replied_at or "Never"}
- Last Opened: {lead.last_opened_at or "Never"}
- Reply Count: {lead.reply_count}
- Bounce Count: {lead.bounce_count}

Campaign Schedule:
- Work Hours: {campaign.work_hours_start} - {campaign.work_hours_end} AEST
- Work Days: {campaign.work_days}
- Timezone: {campaign.timezone}
"""

        prompt = f"""Recommend timing for the next outreach step:

{timing_context}

Based on engagement and tier, when should we send the next message?
What channel should we use for this step?
Consider reply patterns, sequence position, and optimal timing principles."""

        # Create agent with structured output
        agent = self.create_agent(result_type=TimingRecommendation)

        try:
            # Run agent
            result = await agent.run(prompt)

            # Record usage
            cost = await self.record_usage(
                input_tokens=len(prompt.split()) * 2,
                output_tokens=len(str(result.data)) * 2,
            )

            return AgentResult.ok(
                data=result.data,
                reasoning=result.data.reasoning,
                confidence=result.data.confidence,
                tokens_used=(len(prompt.split()) + len(str(result.data))) * 2,
                cost_aud=cost,
            )

        except Exception as e:
            return AgentResult.fail(f"Timing recommendation failed: {str(e)}")

    # ============================================
    # Helper Methods
    # ============================================

    async def _get_tier_distribution(
        self,
        db: AsyncSession,
        campaign_id: UUID,
    ) -> dict[str, int]:
        """Get lead tier distribution for a campaign."""
        stmt = (
            select(Lead.als_tier, func.count(Lead.id))
            .where(
                and_(
                    Lead.campaign_id == campaign_id,
                    Lead.deleted_at.is_(None),
                )
            )
            .group_by(Lead.als_tier)
        )
        result = await db.execute(stmt)
        rows = result.all()

        distribution = {"hot": 0, "warm": 0, "cool": 0, "cold": 0, "dead": 0}
        for tier, count in rows:
            if tier:
                distribution[tier] = count

        return distribution


# Singleton instance
_cmo_agent: CMOAgent | None = None


def get_cmo_agent() -> CMOAgent:
    """Get or create CMO agent instance."""
    global _cmo_agent
    if _cmo_agent is None:
        _cmo_agent = CMOAgent()
    return _cmo_agent


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Singleton pattern with get_cmo_agent()
# [x] Extends BaseAgent from base_agent.py
# [x] Uses Pydantic AI for type-safe validation
# [x] System prompt defines CMO role and decision framework
# [x] Four key methods implemented:
#     - analyze_campaign: Campaign activation/pausing decisions
#     - recommend_channel_mix: Channel selection for leads
#     - prioritize_leads: Lead ranking for outreach
#     - suggest_sequence_timing: Timing optimization
# [x] Structured outputs with Pydantic models:
#     - CampaignAnalysis
#     - ChannelRecommendation
#     - LeadPrioritization
#     - TimingRecommendation
# [x] Rule 11: Session passed as argument (db: AsyncSession)
# [x] Rule 12: Imports from engines, integrations, models allowed
# [x] Rule 15: AI spend limiter via check_budget() and record_usage()
# [x] References tier distribution (hot/warm/cool/cold/dead)
# [x] References ALS scores for decision making
# [x] References campaign settings (allocation, schedule, etc)
# [x] Soft delete checks (deleted_at IS NULL)
# [x] All functions have type hints
# [x] All functions have docstrings
# [x] No hardcoded credentials
# [x] Australian market context in system prompt
