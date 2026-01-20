"""
FILE: src/engines/content.py
PURPOSE: AI content generation engine with spend limiter
PHASE: 4 (Engines), updated Phase 24A (Lead Pool)
TASK: ENG-011, POOL-010
DEPENDENCIES:
  - src/engines/base.py
  - src/integrations/anthropic.py
  - src/models/lead.py
  - src/models/campaign.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 12: No imports from other engines
  - Rule 15: AI spend limiter (all Anthropic calls through spend limiter)
PHASE 24A CHANGES:
  - Added generate_email_for_pool for pool-first content
  - Added generate_sms_for_pool for pool SMS
  - Added generate_linkedin_for_pool for pool LinkedIn
  - Added generate_voice_for_pool for pool voice scripts
  - Pool methods work with dict data instead of Lead model
"""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from src.engines.base import BaseEngine, EngineResult
from src.engines.smart_prompts import (
    SMART_EMAIL_PROMPT,
    build_full_lead_context,
    build_full_pool_lead_context,
    build_client_proof_points,
    format_lead_context_for_prompt,
    format_proof_points_for_prompt,
)
from src.exceptions import AISpendLimitError, ValidationError
from src.integrations.anthropic import AnthropicClient, get_anthropic_client
from src.models.base import ChannelType

import logging

logger = logging.getLogger(__name__)


class ContentEngine(BaseEngine):
    """
    Content generation engine for personalized outreach.

    Uses Anthropic AI to generate personalized content for:
    - Email subject lines and bodies
    - SMS messages
    - LinkedIn messages
    - Voice call scripts

    All AI calls go through the spend limiter (Rule 15).
    """

    def __init__(self, anthropic_client: AnthropicClient | None = None):
        """
        Initialize Content engine with AI client.

        Args:
            anthropic_client: Optional Anthropic client (uses singleton if not provided)
        """
        self._anthropic = anthropic_client

    @property
    def name(self) -> str:
        return "content"

    @property
    def anthropic(self) -> AnthropicClient:
        if self._anthropic is None:
            self._anthropic = get_anthropic_client()
        return self._anthropic

    async def _get_client_intelligence(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> dict[str, Any] | None:
        """
        Fetch client intelligence data for SDK personalization.

        Args:
            db: Database session
            client_id: Client UUID

        Returns:
            Dict with proof points or None if not available
        """
        try:
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
                    google_review_count
                FROM client_intelligence
                WHERE client_id = :client_id
                AND deleted_at IS NULL
            """)

            result = await db.execute(query, {"client_id": str(client_id)})
            row = result.fetchone()

            if not row:
                return None

            return {
                "proof_metrics": row.proof_metrics or [],
                "proof_clients": row.proof_clients or [],
                "proof_industries": row.proof_industries or [],
                "common_pain_points": row.common_pain_points or [],
                "differentiators": row.differentiators or [],
                "testimonials": row.website_testimonials or [],
                "case_studies": row.website_case_studies or [],
                "ratings": {
                    "g2": {"rating": float(row.g2_rating) if row.g2_rating else None, "count": row.g2_review_count},
                    "capterra": {"rating": float(row.capterra_rating) if row.capterra_rating else None, "count": row.capterra_review_count},
                    "trustpilot": {"rating": float(row.trustpilot_rating) if row.trustpilot_rating else None, "count": row.trustpilot_review_count},
                    "google": {"rating": float(row.google_rating) if row.google_rating else None, "count": row.google_review_count},
                },
            }
        except Exception as e:
            logger.warning(f"Failed to fetch client intelligence: {e}")
            return None

    async def generate_email(
        self,
        db: AsyncSession,
        lead_id: UUID,
        campaign_id: UUID,
        template: str | None = None,
        tone: str = "professional",
        include_subject: bool = True,
    ) -> EngineResult[dict[str, Any]]:
        """
        Generate personalized email content for a lead using Smart Prompt system.

        Uses ALL available data from lead enrichment, SDK research, and client
        intelligence to generate highly personalized emails.

        Args:
            db: Database session (passed by caller)
            lead_id: Lead UUID
            campaign_id: Campaign UUID
            template: Optional email template with placeholders (overrides smart prompt)
            tone: Desired tone (professional, friendly, direct)
            include_subject: Whether to generate subject line

        Returns:
            EngineResult with email content (subject, body)

        Raises:
            NotFoundError: If lead or campaign not found
            AISpendLimitError: If daily spend limit exceeded
        """
        try:
            # Get campaign for context
            campaign = await self.get_campaign_by_id(db, campaign_id)

            # Build full lead context using Smart Prompt system
            lead_context = await build_full_lead_context(db, lead_id, include_engagement=True)

            if not lead_context:
                # Fallback to basic query if smart context fails
                lead = await self.get_lead_by_id(db, lead_id)
                if not lead.first_name or not lead.company:
                    raise ValidationError(
                        field="lead_data",
                        message="Lead must have at least first_name and company for personalization",
                    )
                lead_context = {
                    "person": {"first_name": lead.first_name, "full_name": lead.full_name, "title": lead.title},
                    "company": {"name": lead.company, "industry": lead.organization_industry},
                }

            # Get client proof points
            proof_points = {}
            if campaign.client_id:
                proof_points = await build_client_proof_points(db, campaign.client_id)

            # Format for prompt
            lead_context_str = format_lead_context_for_prompt(lead_context)
            proof_points_str = format_proof_points_for_prompt(proof_points)

            # Build campaign context
            campaign_context = f"""**Campaign:** {campaign.name}
**Tone:** {tone}
**Product/Service:** {getattr(campaign, 'product_name', campaign.name)}
{f"**Value Prop:** {getattr(campaign, 'value_proposition', '')}" if hasattr(campaign, 'value_proposition') and campaign.value_proposition else ""}
{f"**Template Guidance:** {template}" if template else ""}"""

            # Use Smart Email Prompt
            prompt = SMART_EMAIL_PROMPT.format(
                lead_context=lead_context_str,
                proof_points=proof_points_str,
                campaign_context=campaign_context,
            )

            # System prompt for email generation
            system = """You are an expert B2B sales copywriter. Generate cold emails that feel personal and human.
Never use generic phrases. Always reference something specific about the lead.
Return valid JSON only."""

            # Generate content via AI
            result = await self.anthropic.complete(
                prompt=prompt,
                system=system,
                max_tokens=800,
                temperature=0.7,
            )

            # Parse JSON from response
            import json
            try:
                content = result["content"]
                # Handle markdown code blocks
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                generated = json.loads(content.strip())

                return EngineResult.ok(
                    data={
                        "subject": generated.get("subject", ""),
                        "body": generated.get("body", ""),
                        "lead_id": str(lead_id),
                        "campaign_id": str(campaign_id),
                        "personalization_used": self._extract_personalization_fields(lead_context),
                    },
                    metadata={
                        "cost_aud": result["cost_aud"],
                        "input_tokens": result["input_tokens"],
                        "output_tokens": result["output_tokens"],
                        "tone": tone,
                        "smart_prompt": True,
                        "has_proof_points": proof_points.get("available", False),
                    },
                )
            except json.JSONDecodeError:
                # Fallback: use raw content as body
                return EngineResult.ok(
                    data={
                        "subject": "Personalized message",
                        "body": result["content"],
                        "lead_id": str(lead_id),
                        "campaign_id": str(campaign_id),
                    },
                    metadata={
                        "cost_aud": result["cost_aud"],
                        "tone": tone,
                        "fallback": True,
                    },
                )

        except AISpendLimitError as e:
            return EngineResult.fail(
                error=f"AI spend limit exceeded: {str(e)}",
                metadata={
                    "lead_id": str(lead_id),
                    "campaign_id": str(campaign_id),
                },
            )
        except Exception as e:
            return EngineResult.fail(
                error=str(e),
                metadata={
                    "lead_id": str(lead_id),
                    "campaign_id": str(campaign_id),
                },
            )

    def _extract_personalization_fields(self, context: dict[str, Any]) -> list[str]:
        """Extract which personalization fields were available in the context."""
        fields = []
        person = context.get("person", {})
        company = context.get("company", {})
        signals = context.get("signals", {})

        if person.get("title"):
            fields.append("title")
        if person.get("linkedin_headline"):
            fields.append("linkedin_headline")
        if person.get("tenure_months") and person["tenure_months"] > 0:
            fields.append("tenure")
        if company.get("industry"):
            fields.append("industry")
        if company.get("employee_count"):
            fields.append("company_size")
        if company.get("description"):
            fields.append("company_description")
        if signals.get("is_hiring"):
            fields.append("hiring_signal")
        if signals.get("recently_funded"):
            fields.append("funding_signal")
        if signals.get("technologies"):
            fields.append("tech_stack")
        if context.get("research") or context.get("sdk_research"):
            fields.append("deep_research")

        return fields

    # ============================================
    # DEPRECATED: generate_email_with_sdk
    # Now delegates to generate_email() - SDK removed
    # per architecture decision (2026-01-20)
    # ============================================

    async def generate_email_with_sdk(
        self,
        db: AsyncSession,
        lead_id: UUID,
        campaign_id: UUID,
        template: str | None = None,
        tone: str = "professional",
        include_subject: bool = True,
        sdk_enrichment: dict[str, Any] | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        Generate personalized email content for a lead.

        NOTE: SDK routing has been removed per architecture decision (2026-01-20).
        SDK is for reasoning (reply handling, meeting prep), not content generation.
        Email personalization now uses Smart Prompt with all DB data.

        This method now simply delegates to generate_email() for backwards
        compatibility with existing orchestration flows.

        Args:
            db: Database session (passed by caller)
            lead_id: Lead UUID
            campaign_id: Campaign UUID
            template: Optional email template with placeholders
            tone: Desired tone (professional, friendly, direct)
            include_subject: Whether to generate subject line
            sdk_enrichment: DEPRECATED - ignored

        Returns:
            EngineResult with email content (subject, body)
        """
        # Delegate to standard email generation
        return await self.generate_email(
            db=db,
            lead_id=lead_id,
            campaign_id=campaign_id,
            template=template,
            tone=tone,
            include_subject=include_subject,
        )

    async def generate_sdk_email_for_pool(
        self,
        db: AsyncSession,
        lead_pool_id: UUID,
        campaign_name: str,
        template: str | None = None,
        tone: str = "professional",
        sdk_enrichment: dict[str, Any] | None = None,
        client_id: UUID | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        Generate email for a pool lead.

        NOTE: SDK routing has been removed per architecture decision (2026-01-20).
        This method now simply delegates to generate_email_for_pool() for
        backwards compatibility with existing orchestration flows.

        Args:
            db: Database session
            lead_pool_id: Lead pool UUID
            campaign_name: Campaign name
            template: Optional template
            tone: Desired tone
            sdk_enrichment: DEPRECATED - ignored
            client_id: DEPRECATED - ignored

        Returns:
            EngineResult with email content
        """
        # Delegate to standard pool email generation
        return await self.generate_email_for_pool(
            db=db,
            lead_pool_id=lead_pool_id,
            campaign_name=campaign_name,
            template=template,
            tone=tone,
        )

    async def generate_sms(
        self,
        db: AsyncSession,
        lead_id: UUID,
        campaign_id: UUID,
        template: str | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        Generate personalized SMS content for a lead.

        SMS messages are limited to 160 characters.

        Args:
            db: Database session (passed by caller)
            lead_id: Lead UUID
            campaign_id: Campaign UUID
            template: Optional SMS template

        Returns:
            EngineResult with SMS content

        Raises:
            NotFoundError: If lead or campaign not found
            AISpendLimitError: If daily spend limit exceeded
        """
        try:
            # Get lead and campaign
            lead = await self.get_lead_by_id(db, lead_id)
            campaign = await self.get_campaign_by_id(db, campaign_id)

            # Validate lead has enough data
            if not lead.first_name:
                raise ValidationError(
                    field="lead_data",
                    message="Lead must have at least first_name for personalization",
                )

            # Build system prompt
            system = """You are an expert at writing concise, effective SMS messages.
SMS messages MUST be under 160 characters.
Be direct and personable.
Include a clear call to action."""

            # Build prompt
            if template:
                prompt = f"""Generate a personalized SMS based on this template:

Template:
{template}

Lead:
- Name: {lead.first_name}
- Company: {lead.company or "their company"}

Campaign: {campaign.name}

Return ONLY the SMS text (max 160 characters). No JSON, no formatting."""
            else:
                prompt = f"""Generate a personalized outreach SMS for:

- Name: {lead.first_name}
- Company: {lead.company or "their company"}

Campaign: {campaign.name}

Return ONLY the SMS text (max 160 characters). No JSON, no formatting."""

            # Generate content via AI
            result = await self.anthropic.complete(
                prompt=prompt,
                system=system,
                max_tokens=100,
                temperature=0.7,
            )

            message = result["content"].strip()

            # Ensure it's under 160 characters
            if len(message) > 160:
                message = message[:157] + "..."

            return EngineResult.ok(
                data={
                    "message": message,
                    "lead_id": str(lead_id),
                    "campaign_id": str(campaign_id),
                },
                metadata={
                    "cost_aud": result["cost_aud"],
                    "input_tokens": result["input_tokens"],
                    "output_tokens": result["output_tokens"],
                    "length": len(message),
                },
            )

        except AISpendLimitError as e:
            return EngineResult.fail(
                error=f"AI spend limit exceeded: {str(e)}",
                metadata={
                    "lead_id": str(lead_id),
                    "campaign_id": str(campaign_id),
                },
            )
        except Exception as e:
            return EngineResult.fail(
                error=str(e),
                metadata={
                    "lead_id": str(lead_id),
                    "campaign_id": str(campaign_id),
                },
            )

    async def generate_linkedin(
        self,
        db: AsyncSession,
        lead_id: UUID,
        campaign_id: UUID,
        template: str | None = None,
        message_type: str = "connection",
    ) -> EngineResult[dict[str, Any]]:
        """
        Generate personalized LinkedIn message for a lead.

        Args:
            db: Database session (passed by caller)
            lead_id: Lead UUID
            campaign_id: Campaign UUID
            template: Optional LinkedIn template
            message_type: Type of message (connection, inmail, follow_up)

        Returns:
            EngineResult with LinkedIn message content

        Raises:
            NotFoundError: If lead or campaign not found
            AISpendLimitError: If daily spend limit exceeded
        """
        try:
            # Get lead and campaign
            lead = await self.get_lead_by_id(db, lead_id)
            campaign = await self.get_campaign_by_id(db, campaign_id)

            # Validate lead has enough data
            if not lead.first_name:
                raise ValidationError(
                    field="lead_data",
                    message="Lead must have at least first_name for personalization",
                )

            # Build system prompt based on message type
            if message_type == "connection":
                system = """You are an expert at writing LinkedIn connection requests.
Connection requests are limited to 300 characters.
Be professional but personable.
Reference shared interests or mutual connections when possible."""
                max_length = 300
            else:
                system = """You are an expert at writing LinkedIn InMail messages.
Keep messages under 200 words.
Be professional and value-focused.
Include a clear call to action."""
                max_length = 1000

            # Build prompt
            if template:
                prompt = f"""Generate a personalized LinkedIn {message_type} message based on this template:

Template:
{template}

Lead:
- Name: {lead.first_name} {lead.last_name or ""}
- Title: {lead.title or ""}
- Company: {lead.company or ""}

Campaign: {campaign.name}

Return ONLY the message text. No JSON, no formatting."""
            else:
                prompt = f"""Generate a personalized LinkedIn {message_type} message for:

- Name: {lead.first_name} {lead.last_name or ""}
- Title: {lead.title or ""}
- Company: {lead.company or ""}

Campaign: {campaign.name}

Return ONLY the message text. No JSON, no formatting."""

            # Generate content via AI
            result = await self.anthropic.complete(
                prompt=prompt,
                system=system,
                max_tokens=400,
                temperature=0.7,
            )

            message = result["content"].strip()

            # Ensure it's under max length
            if len(message) > max_length:
                message = message[:max_length - 3] + "..."

            return EngineResult.ok(
                data={
                    "message": message,
                    "message_type": message_type,
                    "lead_id": str(lead_id),
                    "campaign_id": str(campaign_id),
                },
                metadata={
                    "cost_aud": result["cost_aud"],
                    "input_tokens": result["input_tokens"],
                    "output_tokens": result["output_tokens"],
                    "length": len(message),
                },
            )

        except AISpendLimitError as e:
            return EngineResult.fail(
                error=f"AI spend limit exceeded: {str(e)}",
                metadata={
                    "lead_id": str(lead_id),
                    "campaign_id": str(campaign_id),
                },
            )
        except Exception as e:
            return EngineResult.fail(
                error=str(e),
                metadata={
                    "lead_id": str(lead_id),
                    "campaign_id": str(campaign_id),
                },
            )

    async def generate_voice_script(
        self,
        db: AsyncSession,
        lead_id: UUID,
        campaign_id: UUID,
        template: str | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        Generate personalized voice call script for a lead.

        Args:
            db: Database session (passed by caller)
            lead_id: Lead UUID
            campaign_id: Campaign UUID
            template: Optional voice script template

        Returns:
            EngineResult with voice script

        Raises:
            NotFoundError: If lead or campaign not found
            AISpendLimitError: If daily spend limit exceeded
        """
        try:
            # Get lead and campaign
            lead = await self.get_lead_by_id(db, lead_id)
            campaign = await self.get_campaign_by_id(db, campaign_id)

            # Validate lead has enough data
            if not lead.first_name or not lead.company:
                raise ValidationError(
                    field="lead_data",
                    message="Lead must have at least first_name and company for personalization",
                )

            # Build system prompt
            system = """You are an expert at writing AI voice call scripts.
Write conversational, natural-sounding scripts.
Include:
- Opening greeting
- Value proposition
- Objection handling
- Call to action
Keep it under 200 words."""

            # Build prompt
            if template:
                prompt = f"""Generate a personalized voice call script based on this template:

Template:
{template}

Lead:
- Name: {lead.first_name} {lead.last_name or ""}
- Title: {lead.title or ""}
- Company: {lead.company}

Campaign: {campaign.name}

Return as JSON with: {{"opening": "...", "value_prop": "...", "cta": "..."}}"""
            else:
                prompt = f"""Generate a personalized voice call script for:

- Name: {lead.first_name} {lead.last_name or ""}
- Title: {lead.title or ""}
- Company: {lead.company}

Campaign: {campaign.name}

Return as JSON with: {{"opening": "...", "value_prop": "...", "cta": "..."}}"""

            # Generate content via AI
            result = await self.anthropic.complete(
                prompt=prompt,
                system=system,
                max_tokens=600,
                temperature=0.7,
            )

            # Parse JSON from response
            import json
            try:
                content = result["content"]
                # Handle markdown code blocks
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                script = json.loads(content.strip())

                return EngineResult.ok(
                    data={
                        "opening": script.get("opening", ""),
                        "value_prop": script.get("value_prop", ""),
                        "cta": script.get("cta", ""),
                        "lead_id": str(lead_id),
                        "campaign_id": str(campaign_id),
                    },
                    metadata={
                        "cost_aud": result["cost_aud"],
                        "input_tokens": result["input_tokens"],
                        "output_tokens": result["output_tokens"],
                    },
                )
            except json.JSONDecodeError:
                # Fallback: use raw content as script
                return EngineResult.ok(
                    data={
                        "opening": result["content"],
                        "value_prop": "",
                        "cta": "",
                        "lead_id": str(lead_id),
                        "campaign_id": str(campaign_id),
                    },
                    metadata={
                        "cost_aud": result["cost_aud"],
                        "fallback": True,
                    },
                )

        except AISpendLimitError as e:
            return EngineResult.fail(
                error=f"AI spend limit exceeded: {str(e)}",
                metadata={
                    "lead_id": str(lead_id),
                    "campaign_id": str(campaign_id),
                },
            )
        except Exception as e:
            return EngineResult.fail(
                error=str(e),
                metadata={
                    "lead_id": str(lead_id),
                    "campaign_id": str(campaign_id),
                },
            )

    async def get_spend_status(self) -> EngineResult[dict[str, Any]]:
        """
        Get current AI spend status.

        Returns:
            EngineResult with spend status (spent, remaining, percentage)
        """
        try:
            status = await self.anthropic.get_spend_status()
            return EngineResult.ok(
                data=status,
                metadata={"engine": self.name},
            )
        except Exception as e:
            return EngineResult.fail(
                error=str(e),
                metadata={"engine": self.name},
            )

    # ============================================
    # PHASE 24A: Pool Content Generation Methods
    # ============================================

    async def generate_email_for_pool(
        self,
        db: AsyncSession,
        lead_pool_id: UUID,
        campaign_name: str,
        template: str | None = None,
        tone: str = "professional",
        include_subject: bool = True,
        client_id: UUID | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        Generate personalized email for a pool lead using Smart Prompt system.

        Pool leads have richer data than legacy leads since they come directly
        from Apollo with full enrichment. This method leverages ALL that data.

        Args:
            db: Database session (passed by caller)
            lead_pool_id: Lead pool UUID
            campaign_name: Campaign name for context
            template: Optional email template
            tone: Desired tone
            include_subject: Whether to generate subject line
            client_id: Optional client ID for proof points

        Returns:
            EngineResult with email content
        """
        try:
            # Build full pool lead context using Smart Prompt system
            lead_context = await build_full_pool_lead_context(db, lead_pool_id, client_id)

            if not lead_context:
                return EngineResult.fail(
                    error="Lead not found in pool",
                    metadata={"lead_pool_id": str(lead_pool_id)},
                )

            # Validate minimum data
            person = lead_context.get("person", {})
            company = lead_context.get("company", {})
            if not person.get("first_name") or not company.get("name"):
                return EngineResult.fail(
                    error="Lead must have at least first_name and company for personalization",
                    metadata={"lead_pool_id": str(lead_pool_id)},
                )

            # Get client proof points if client_id provided
            proof_points = {}
            if client_id:
                proof_points = await build_client_proof_points(db, client_id)

            # Format for prompt
            lead_context_str = format_lead_context_for_prompt(lead_context)
            proof_points_str = format_proof_points_for_prompt(proof_points)

            # Build campaign context
            campaign_context = f"""**Campaign:** {campaign_name}
**Tone:** {tone}
{f"**Template Guidance:** {template}" if template else ""}"""

            # Use Smart Email Prompt
            prompt = SMART_EMAIL_PROMPT.format(
                lead_context=lead_context_str,
                proof_points=proof_points_str,
                campaign_context=campaign_context,
            )

            # System prompt
            system = """You are an expert B2B sales copywriter. Generate cold emails that feel personal and human.
Never use generic phrases. Always reference something specific about the lead.
Return valid JSON only."""

            # Generate content via AI
            result = await self.anthropic.complete(
                prompt=prompt,
                system=system,
                max_tokens=800,
                temperature=0.7,
            )

            # Parse JSON from response
            import json
            try:
                content = result["content"]
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                generated = json.loads(content.strip())

                return EngineResult.ok(
                    data={
                        "subject": generated.get("subject", ""),
                        "body": generated.get("body", ""),
                        "lead_pool_id": str(lead_pool_id),
                        "campaign_name": campaign_name,
                        "personalization_used": self._extract_personalization_fields(lead_context),
                    },
                    metadata={
                        "cost_aud": result["cost_aud"],
                        "input_tokens": result["input_tokens"],
                        "output_tokens": result["output_tokens"],
                        "tone": tone,
                        "source": "lead_pool",
                        "smart_prompt": True,
                        "has_proof_points": proof_points.get("available", False),
                    },
                )
            except json.JSONDecodeError:
                return EngineResult.ok(
                    data={
                        "subject": "Personalized message",
                        "body": result["content"],
                        "lead_pool_id": str(lead_pool_id),
                        "campaign_name": campaign_name,
                    },
                    metadata={
                        "cost_aud": result["cost_aud"],
                        "tone": tone,
                        "fallback": True,
                        "source": "lead_pool",
                    },
                )

        except AISpendLimitError as e:
            return EngineResult.fail(
                error=f"AI spend limit exceeded: {str(e)}",
                metadata={"lead_pool_id": str(lead_pool_id)},
            )
        except Exception as e:
            return EngineResult.fail(
                error=str(e),
                metadata={"lead_pool_id": str(lead_pool_id)},
            )

    async def generate_sms_for_pool(
        self,
        db: AsyncSession,
        lead_pool_id: UUID,
        campaign_name: str,
        template: str | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        Generate personalized SMS for a pool lead.

        Phase 24A: Works with pool lead data directly.

        Args:
            db: Database session (passed by caller)
            lead_pool_id: Lead pool UUID
            campaign_name: Campaign name for context
            template: Optional SMS template

        Returns:
            EngineResult with SMS content
        """
        try:
            pool_lead = await self._get_pool_lead(db, lead_pool_id)
            if not pool_lead:
                return EngineResult.fail(
                    error="Lead not found in pool",
                    metadata={"lead_pool_id": str(lead_pool_id)},
                )

            first_name = pool_lead.get("first_name")
            if not first_name:
                return EngineResult.fail(
                    error="Lead must have first_name for personalization",
                    metadata={"lead_pool_id": str(lead_pool_id)},
                )

            system = """You are an expert at writing concise, effective SMS messages.
SMS messages MUST be under 160 characters.
Be direct and personable.
Include a clear call to action."""

            prompt = f"""Generate a personalized SMS for:

- Name: {first_name}
- Company: {pool_lead.get("company_name", "their company")}

Campaign: {campaign_name}
{f"Template: {template}" if template else ""}

Return ONLY the SMS text (max 160 characters). No JSON, no formatting."""

            result = await self.anthropic.complete(
                prompt=prompt,
                system=system,
                max_tokens=100,
                temperature=0.7,
            )

            message = result["content"].strip()
            if len(message) > 160:
                message = message[:157] + "..."

            return EngineResult.ok(
                data={
                    "message": message,
                    "lead_pool_id": str(lead_pool_id),
                    "campaign_name": campaign_name,
                },
                metadata={
                    "cost_aud": result["cost_aud"],
                    "input_tokens": result["input_tokens"],
                    "output_tokens": result["output_tokens"],
                    "length": len(message),
                    "source": "lead_pool",
                },
            )

        except AISpendLimitError as e:
            return EngineResult.fail(
                error=f"AI spend limit exceeded: {str(e)}",
                metadata={"lead_pool_id": str(lead_pool_id)},
            )
        except Exception as e:
            return EngineResult.fail(
                error=str(e),
                metadata={"lead_pool_id": str(lead_pool_id)},
            )

    async def generate_linkedin_for_pool(
        self,
        db: AsyncSession,
        lead_pool_id: UUID,
        campaign_name: str,
        template: str | None = None,
        message_type: str = "connection",
    ) -> EngineResult[dict[str, Any]]:
        """
        Generate personalized LinkedIn message for a pool lead.

        Phase 24A: Works with pool lead data directly.

        Args:
            db: Database session (passed by caller)
            lead_pool_id: Lead pool UUID
            campaign_name: Campaign name for context
            template: Optional LinkedIn template
            message_type: Type (connection, inmail, follow_up)

        Returns:
            EngineResult with LinkedIn message
        """
        try:
            pool_lead = await self._get_pool_lead(db, lead_pool_id)
            if not pool_lead:
                return EngineResult.fail(
                    error="Lead not found in pool",
                    metadata={"lead_pool_id": str(lead_pool_id)},
                )

            first_name = pool_lead.get("first_name")
            if not first_name:
                return EngineResult.fail(
                    error="Lead must have first_name for personalization",
                    metadata={"lead_pool_id": str(lead_pool_id)},
                )

            if message_type == "connection":
                system = """You are an expert at writing LinkedIn connection requests.
Connection requests are limited to 300 characters.
Be professional but personable."""
                max_length = 300
            else:
                system = """You are an expert at writing LinkedIn InMail messages.
Keep messages under 200 words.
Be professional and value-focused."""
                max_length = 1000

            prompt = f"""Generate a personalized LinkedIn {message_type} message for:

- Name: {first_name} {pool_lead.get("last_name", "")}
- Title: {pool_lead.get("title", "")}
- Company: {pool_lead.get("company_name", "")}

Campaign: {campaign_name}
{f"Template: {template}" if template else ""}

Return ONLY the message text. No JSON, no formatting."""

            result = await self.anthropic.complete(
                prompt=prompt,
                system=system,
                max_tokens=400,
                temperature=0.7,
            )

            message = result["content"].strip()
            if len(message) > max_length:
                message = message[:max_length - 3] + "..."

            return EngineResult.ok(
                data={
                    "message": message,
                    "message_type": message_type,
                    "lead_pool_id": str(lead_pool_id),
                    "campaign_name": campaign_name,
                },
                metadata={
                    "cost_aud": result["cost_aud"],
                    "input_tokens": result["input_tokens"],
                    "output_tokens": result["output_tokens"],
                    "length": len(message),
                    "source": "lead_pool",
                },
            )

        except AISpendLimitError as e:
            return EngineResult.fail(
                error=f"AI spend limit exceeded: {str(e)}",
                metadata={"lead_pool_id": str(lead_pool_id)},
            )
        except Exception as e:
            return EngineResult.fail(
                error=str(e),
                metadata={"lead_pool_id": str(lead_pool_id)},
            )

    async def generate_voice_for_pool(
        self,
        db: AsyncSession,
        lead_pool_id: UUID,
        campaign_name: str,
        template: str | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        Generate personalized voice call script for a pool lead.

        Phase 24A: Works with pool lead data directly.

        Args:
            db: Database session (passed by caller)
            lead_pool_id: Lead pool UUID
            campaign_name: Campaign name for context
            template: Optional voice script template

        Returns:
            EngineResult with voice script
        """
        try:
            pool_lead = await self._get_pool_lead(db, lead_pool_id)
            if not pool_lead:
                return EngineResult.fail(
                    error="Lead not found in pool",
                    metadata={"lead_pool_id": str(lead_pool_id)},
                )

            first_name = pool_lead.get("first_name")
            company = pool_lead.get("company_name")
            if not first_name or not company:
                return EngineResult.fail(
                    error="Lead must have first_name and company for voice scripts",
                    metadata={"lead_pool_id": str(lead_pool_id)},
                )

            system = """You are an expert at writing AI voice call scripts.
Write conversational, natural-sounding scripts.
Include opening greeting, value proposition, and call to action.
Keep it under 200 words."""

            prompt = f"""Generate a personalized voice call script for:

- Name: {first_name} {pool_lead.get("last_name", "")}
- Title: {pool_lead.get("title", "")}
- Company: {company}

Campaign: {campaign_name}
{f"Template: {template}" if template else ""}

Return as JSON with: {{"opening": "...", "value_prop": "...", "cta": "..."}}"""

            result = await self.anthropic.complete(
                prompt=prompt,
                system=system,
                max_tokens=600,
                temperature=0.7,
            )

            import json
            try:
                content = result["content"]
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                script = json.loads(content.strip())

                return EngineResult.ok(
                    data={
                        "opening": script.get("opening", ""),
                        "value_prop": script.get("value_prop", ""),
                        "cta": script.get("cta", ""),
                        "lead_pool_id": str(lead_pool_id),
                        "campaign_name": campaign_name,
                    },
                    metadata={
                        "cost_aud": result["cost_aud"],
                        "input_tokens": result["input_tokens"],
                        "output_tokens": result["output_tokens"],
                        "source": "lead_pool",
                    },
                )
            except json.JSONDecodeError:
                return EngineResult.ok(
                    data={
                        "opening": result["content"],
                        "value_prop": "",
                        "cta": "",
                        "lead_pool_id": str(lead_pool_id),
                        "campaign_name": campaign_name,
                    },
                    metadata={
                        "cost_aud": result["cost_aud"],
                        "fallback": True,
                        "source": "lead_pool",
                    },
                )

        except AISpendLimitError as e:
            return EngineResult.fail(
                error=f"AI spend limit exceeded: {str(e)}",
                metadata={"lead_pool_id": str(lead_pool_id)},
            )
        except Exception as e:
            return EngineResult.fail(
                error=str(e),
                metadata={"lead_pool_id": str(lead_pool_id)},
            )

    async def _get_pool_lead(
        self,
        db: AsyncSession,
        lead_pool_id: UUID,
        include_als_score: bool = False,
    ) -> dict[str, Any] | None:
        """
        Get lead data from pool for content generation.

        Args:
            db: Database session
            lead_pool_id: Pool lead UUID
            include_als_score: If True, joins with lead_assignments for ALS score

        Returns:
            Pool lead data dict or None
        """
        from sqlalchemy import text

        if include_als_score:
            # Join with lead_assignments to get ALS score (for SDK routing)
            query = text("""
                SELECT lp.id, lp.first_name, lp.last_name, lp.title, lp.email,
                       lp.company_name, lp.company_industry, lp.company_employee_count,
                       lp.linkedin_url, lp.icebreaker_hook,
                       la.als_score, la.als_tier,
                       la.id as assignment_id
                FROM lead_pool lp
                LEFT JOIN lead_assignments la ON la.lead_pool_id = lp.id
                WHERE lp.id = :id
                ORDER BY la.scored_at DESC NULLS LAST
                LIMIT 1
            """)
        else:
            query = text("""
                SELECT id, first_name, last_name, title, email,
                       company_name, company_industry, company_employee_count,
                       linkedin_url, icebreaker_hook
                FROM lead_pool
                WHERE id = :id
            """)

        result = await db.execute(query, {"id": str(lead_pool_id)})
        row = result.fetchone()

        return dict(row._mapping) if row else None


# Singleton instance
_content_engine: ContentEngine | None = None


def get_content_engine() -> ContentEngine:
    """Get or create Content engine instance."""
    global _content_engine
    if _content_engine is None:
        _content_engine = ContentEngine()
    return _content_engine


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Session passed as argument (Rule 11)
# [x] No imports from other engines (Rule 12)
# [x] AI spend limiter via Anthropic client (Rule 15)
# [x] Generate email with subject and body
# [x] Generate SMS (160 char limit)
# [x] Generate LinkedIn messages (connection, inmail)
# [x] Generate voice call scripts
# [x] Template-based generation support
# [x] Lead data personalization
# [x] Spend status reporting
# [x] EngineResult wrapper for responses
# [x] All functions have type hints
# [x] All functions have docstrings
# ============================================
# PHASE 24A POOL ADDITIONS
# ============================================
# [x] generate_email_for_pool for pool leads
# [x] generate_sms_for_pool for pool leads
# [x] generate_linkedin_for_pool for pool leads
# [x] generate_voice_for_pool for pool leads
# [x] _get_pool_lead helper for pool data fetch
# [x] Icebreaker hook integration for personalization
# [x] All pool methods use campaign_name instead of campaign_id
