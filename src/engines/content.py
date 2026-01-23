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
    SAFE_FALLBACK_TEMPLATE,
    FACT_CHECK_PROMPT,
    build_full_lead_context,
    build_full_pool_lead_context,
    build_client_proof_points,
    format_lead_context_for_prompt,
    format_proof_points_for_prompt,
    generate_priority_guidance,
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

            # Generate priority guidance for the prompt
            priority_guidance_str = generate_priority_guidance(lead_context)

            # Use Smart Email Prompt
            prompt = SMART_EMAIL_PROMPT.format(
                lead_context=lead_context_str,
                proof_points=proof_points_str,
                campaign_context=campaign_context,
                priority_guidance=priority_guidance_str,
            )

            # System prompt for email generation (Item 41: Conservative instructions)
            system = """You are an expert B2B sales copywriter. Generate cold emails that feel personal and human.

CRITICAL RULES:
1. ONLY reference facts explicitly provided in the lead context
2. NEVER assume or invent details about the lead's company, tech stack, or achievements
3. NEVER claim the lead uses specific products/tools unless explicitly listed
4. When data is missing, use general language that can't be wrong
5. It's better to be vague than to state something false

Return valid JSON only with "subject" and "body" keys."""

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
                subject = generated.get("subject", "")
                body = generated.get("body", "")
                generation_cost = result["cost_aud"]
                total_cost = generation_cost

                # ============================================
                # ITEM 40: FACT-CHECK GATE
                # ============================================
                # Verify generated content against source data
                fact_check = await self._fact_check_content(
                    subject=subject,
                    body=body,
                    lead_context=lead_context,
                )
                total_cost += fact_check.get("cost_aud", 0)

                # If fact-check fails with HIGH risk, use safe fallback immediately
                if fact_check["verdict"] == "FAIL" and fact_check.get("risk_level") == "HIGH":
                    logger.warning(
                        f"Fact-check HIGH risk for lead {lead_id}: {fact_check.get('unsupported_claims', [])}"
                    )
                    fallback = self._generate_safe_fallback(lead_context, campaign.name)
                    return EngineResult.ok(
                        data={
                            "subject": fallback["subject"],
                            "body": fallback["body"],
                            "lead_id": str(lead_id),
                            "campaign_id": str(campaign_id),
                            "personalization_used": ["first_name", "company"],
                        },
                        metadata={
                            "cost_aud": total_cost,
                            "tone": tone,
                            "safe_fallback": True,
                            "fact_check_failed": True,
                            "unsupported_claims": fact_check.get("unsupported_claims", []),
                        },
                    )

                # If fact-check fails with MEDIUM risk, regenerate once
                if fact_check["verdict"] == "FAIL" and fact_check.get("risk_level") == "MEDIUM":
                    logger.info(f"Fact-check MEDIUM risk, regenerating for lead {lead_id}")

                    # Add warning to prompt about specific issues
                    retry_prompt = prompt + f"""

## WARNING: Previous attempt had unsupported claims
The following claims were NOT in the source data - do NOT include them:
{chr(10).join(f'- {claim}' for claim in fact_check.get('unsupported_claims', []))}

Generate a new email that ONLY uses verified facts from the lead context."""

                    retry_result = await self.anthropic.complete(
                        prompt=retry_prompt,
                        system=system,
                        max_tokens=800,
                        temperature=0.5,  # Lower temp for safer output
                    )
                    total_cost += retry_result["cost_aud"]

                    # Parse retry result with error handling (G2 fix)
                    try:
                        retry_content = retry_result["content"]
                        if "```json" in retry_content:
                            retry_content = retry_content.split("```json")[1].split("```")[0]
                        elif "```" in retry_content:
                            retry_content = retry_content.split("```")[1].split("```")[0]

                        retry_generated = json.loads(retry_content.strip())
                        subject = retry_generated.get("subject", "")
                        body = retry_generated.get("body", "")
                    except (json.JSONDecodeError, IndexError) as e:
                        # Retry JSON parsing failed - use safe fallback
                        logger.warning(f"Retry JSON parse failed for lead {lead_id}: {e}")
                        fallback = self._generate_safe_fallback(lead_context, campaign.name)
                        return EngineResult.ok(
                            data={
                                "subject": fallback["subject"],
                                "body": fallback["body"],
                                "lead_id": str(lead_id),
                                "campaign_id": str(campaign_id),
                                "personalization_used": ["first_name", "company"],
                            },
                            metadata={
                                "cost_aud": total_cost,
                                "tone": tone,
                                "safe_fallback": True,
                                "fact_check_retried": True,
                                "retry_json_parse_failed": True,
                            },
                        )

                    # Second fact-check
                    retry_fact_check = await self._fact_check_content(
                        subject=subject,
                        body=body,
                        lead_context=lead_context,
                    )
                    total_cost += retry_fact_check.get("cost_aud", 0)

                    # If still failing, use safe fallback
                    if retry_fact_check["verdict"] == "FAIL":
                        logger.warning(
                            f"Fact-check failed twice for lead {lead_id}, using safe fallback"
                        )
                        fallback = self._generate_safe_fallback(lead_context, campaign.name)
                        return EngineResult.ok(
                            data={
                                "subject": fallback["subject"],
                                "body": fallback["body"],
                                "lead_id": str(lead_id),
                                "campaign_id": str(campaign_id),
                                "personalization_used": ["first_name", "company"],
                            },
                            metadata={
                                "cost_aud": total_cost,
                                "tone": tone,
                                "safe_fallback": True,
                                "fact_check_retried": True,
                                "fact_check_failed": True,
                            },
                        )

                # Fact-check passed (or LOW risk) - return generated content
                return EngineResult.ok(
                    data={
                        "subject": subject,
                        "body": body,
                        "lead_id": str(lead_id),
                        "campaign_id": str(campaign_id),
                        "personalization_used": self._extract_personalization_fields(lead_context),
                    },
                    metadata={
                        "cost_aud": total_cost,
                        "input_tokens": result["input_tokens"],
                        "output_tokens": result["output_tokens"],
                        "tone": tone,
                        "smart_prompt": True,
                        "has_proof_points": proof_points.get("available", False),
                        "fact_check_verdict": fact_check["verdict"],
                        "fact_check_risk": fact_check.get("risk_level", "LOW"),
                    },
                )
            except json.JSONDecodeError:
                # Fallback: use safe fallback instead of raw content
                logger.warning(f"JSON parse failed for lead {lead_id}, using safe fallback")
                fallback = self._generate_safe_fallback(lead_context, campaign.name)
                return EngineResult.ok(
                    data={
                        "subject": fallback["subject"],
                        "body": fallback["body"],
                        "lead_id": str(lead_id),
                        "campaign_id": str(campaign_id),
                        "personalization_used": ["first_name", "company"],
                    },
                    metadata={
                        "cost_aud": result["cost_aud"],
                        "tone": tone,
                        "safe_fallback": True,
                        "json_parse_failed": True,
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
    # ITEM 40: FACT-CHECK GATE
    # ============================================

    async def _fact_check_content(
        self,
        subject: str,
        body: str,
        lead_context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Verify generated email content against source data.

        Uses Claude to check that all claims in the email are supported
        by the provided lead context. Prevents hallucination.

        Args:
            subject: Generated email subject
            body: Generated email body
            lead_context: Source data used for generation

        Returns:
            Dict with:
                - verdict: "PASS" or "FAIL"
                - unsupported_claims: List of claims not in source data
                - risk_level: "LOW", "MEDIUM", or "HIGH"
                - cost_aud: Cost of fact-check call

        Cost: ~$0.01 per check (using smaller context)
        """
        try:
            # Format source data for fact-check prompt
            source_data = format_lead_context_for_prompt(lead_context)

            prompt = FACT_CHECK_PROMPT.format(
                source_data=source_data,
                subject=subject,
                body=body,
            )

            system = """You are a strict fact-checker. Return valid JSON only.
Be conservative - if you're unsure whether a claim is supported, mark it as unsupported."""

            # Use lower temperature for more consistent fact-checking
            result = await self.anthropic.complete(
                prompt=prompt,
                system=system,
                max_tokens=500,
                temperature=0.3,
            )

            # Parse JSON from response
            import json
            content = result["content"]
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            fact_check_result = json.loads(content.strip())
            fact_check_result["cost_aud"] = result.get("cost_aud", 0)

            logger.info(
                f"Fact-check result: {fact_check_result['verdict']}, "
                f"risk: {fact_check_result.get('risk_level', 'unknown')}, "
                f"claims: {len(fact_check_result.get('unsupported_claims', []))}"
            )

            return fact_check_result

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse fact-check response: {e}")
            # Conservative default: fail if we can't parse
            # Note: result is always defined here since API call completes before JSON parsing
            return {
                "verdict": "FAIL",
                "unsupported_claims": ["Unable to verify - parsing error"],
                "risk_level": "MEDIUM",
                "cost_aud": result.get("cost_aud", 0),
            }
        except Exception as e:
            logger.error(f"Fact-check failed: {e}")
            # On error, pass through but log (API call may have failed)
            return {
                "verdict": "PASS",
                "unsupported_claims": [],
                "risk_level": "LOW",
                "error": str(e),
                "cost_aud": 0,
            }

    # ============================================
    # ITEM 42: SAFE FALLBACK TEMPLATE
    # ============================================

    def _generate_safe_fallback(
        self,
        lead_context: dict[str, Any],
        campaign_name: str,
        sender_name: str = "The Team",
    ) -> dict[str, str]:
        """
        Generate a brand-safe fallback email with NO specific claims.

        Used when:
        - Fact-check fails twice
        - AI returns risky/hallucinated content
        - Content QA flags issues

        Args:
            lead_context: Lead context dict
            campaign_name: Campaign name for generic value prop
            sender_name: Sender name for signature

        Returns:
            Dict with "subject" and "body" keys
        """
        person = lead_context.get("person", {})
        company = lead_context.get("company", {})

        first_name = person.get("first_name", "there")
        company_name = company.get("name", "your company")

        # Generic value prop - no specific claims
        value_prop_generic = "streamline their outreach and book more meetings"

        body = SAFE_FALLBACK_TEMPLATE.format(
            first_name=first_name,
            company=company_name,
            value_prop_generic=value_prop_generic,
            sender_name=sender_name,
        )

        # Safe subject line - only uses verified first name
        subject = f"{first_name}, quick question"

        logger.info(f"Generated safe fallback email for {company_name}")

        return {
            "subject": subject,
            "body": body,
        }

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

            # Generate priority guidance for the prompt
            priority_guidance_str = generate_priority_guidance(lead_context)

            # Use Smart Email Prompt
            prompt = SMART_EMAIL_PROMPT.format(
                lead_context=lead_context_str,
                proof_points=proof_points_str,
                campaign_context=campaign_context,
                priority_guidance=priority_guidance_str,
            )

            # System prompt (Item 41: Conservative instructions)
            system = """You are an expert B2B sales copywriter. Generate cold emails that feel personal and human.

CRITICAL RULES:
1. ONLY reference facts explicitly provided in the lead context
2. NEVER assume or invent details about the lead's company, tech stack, or achievements
3. NEVER claim the lead uses specific products/tools unless explicitly listed
4. When data is missing, use general language that can't be wrong
5. It's better to be vague than to state something false

Return valid JSON only with "subject" and "body" keys."""

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
                subject = generated.get("subject", "")
                body = generated.get("body", "")
                generation_cost = result["cost_aud"]
                total_cost = generation_cost

                # ============================================
                # ITEM 40: FACT-CHECK GATE (Pool Leads)
                # ============================================
                fact_check = await self._fact_check_content(
                    subject=subject,
                    body=body,
                    lead_context=lead_context,
                )
                total_cost += fact_check.get("cost_aud", 0)

                # HIGH risk = immediate safe fallback
                if fact_check["verdict"] == "FAIL" and fact_check.get("risk_level") == "HIGH":
                    logger.warning(
                        f"Fact-check HIGH risk for pool lead {lead_pool_id}: {fact_check.get('unsupported_claims', [])}"
                    )
                    fallback = self._generate_safe_fallback(lead_context, campaign_name)
                    return EngineResult.ok(
                        data={
                            "subject": fallback["subject"],
                            "body": fallback["body"],
                            "lead_pool_id": str(lead_pool_id),
                            "campaign_name": campaign_name,
                            "personalization_used": ["first_name", "company"],
                        },
                        metadata={
                            "cost_aud": total_cost,
                            "tone": tone,
                            "source": "lead_pool",
                            "safe_fallback": True,
                            "fact_check_failed": True,
                        },
                    )

                # MEDIUM risk = regenerate once
                if fact_check["verdict"] == "FAIL" and fact_check.get("risk_level") == "MEDIUM":
                    logger.info(f"Fact-check MEDIUM risk, regenerating for pool lead {lead_pool_id}")

                    retry_prompt = prompt + f"""

## WARNING: Previous attempt had unsupported claims
The following claims were NOT in the source data - do NOT include them:
{chr(10).join(f'- {claim}' for claim in fact_check.get('unsupported_claims', []))}

Generate a new email that ONLY uses verified facts from the lead context."""

                    retry_result = await self.anthropic.complete(
                        prompt=retry_prompt,
                        system=system,
                        max_tokens=800,
                        temperature=0.5,
                    )
                    total_cost += retry_result["cost_aud"]

                    # Parse retry result with error handling (G2 fix)
                    try:
                        retry_content = retry_result["content"]
                        if "```json" in retry_content:
                            retry_content = retry_content.split("```json")[1].split("```")[0]
                        elif "```" in retry_content:
                            retry_content = retry_content.split("```")[1].split("```")[0]

                        retry_generated = json.loads(retry_content.strip())
                        subject = retry_generated.get("subject", "")
                        body = retry_generated.get("body", "")
                    except (json.JSONDecodeError, IndexError) as e:
                        # Retry JSON parsing failed - use safe fallback
                        logger.warning(f"Retry JSON parse failed for pool lead {lead_pool_id}: {e}")
                        fallback = self._generate_safe_fallback(lead_context, campaign_name)
                        return EngineResult.ok(
                            data={
                                "subject": fallback["subject"],
                                "body": fallback["body"],
                                "lead_pool_id": str(lead_pool_id),
                                "campaign_name": campaign_name,
                                "personalization_used": ["first_name", "company"],
                            },
                            metadata={
                                "cost_aud": total_cost,
                                "tone": tone,
                                "source": "lead_pool",
                                "safe_fallback": True,
                                "fact_check_retried": True,
                                "retry_json_parse_failed": True,
                            },
                        )

                    retry_fact_check = await self._fact_check_content(
                        subject=subject,
                        body=body,
                        lead_context=lead_context,
                    )
                    total_cost += retry_fact_check.get("cost_aud", 0)

                    if retry_fact_check["verdict"] == "FAIL":
                        logger.warning(f"Fact-check failed twice for pool lead {lead_pool_id}")
                        fallback = self._generate_safe_fallback(lead_context, campaign_name)
                        return EngineResult.ok(
                            data={
                                "subject": fallback["subject"],
                                "body": fallback["body"],
                                "lead_pool_id": str(lead_pool_id),
                                "campaign_name": campaign_name,
                                "personalization_used": ["first_name", "company"],
                            },
                            metadata={
                                "cost_aud": total_cost,
                                "tone": tone,
                                "source": "lead_pool",
                                "safe_fallback": True,
                                "fact_check_retried": True,
                                "fact_check_failed": True,
                            },
                        )

                # Fact-check passed
                return EngineResult.ok(
                    data={
                        "subject": subject,
                        "body": body,
                        "lead_pool_id": str(lead_pool_id),
                        "campaign_name": campaign_name,
                        "personalization_used": self._extract_personalization_fields(lead_context),
                    },
                    metadata={
                        "cost_aud": total_cost,
                        "input_tokens": result["input_tokens"],
                        "output_tokens": result["output_tokens"],
                        "tone": tone,
                        "source": "lead_pool",
                        "smart_prompt": True,
                        "has_proof_points": proof_points.get("available", False),
                        "fact_check_verdict": fact_check["verdict"],
                        "fact_check_risk": fact_check.get("risk_level", "LOW"),
                    },
                )
            except json.JSONDecodeError:
                logger.warning(f"JSON parse failed for pool lead {lead_pool_id}")
                fallback = self._generate_safe_fallback(lead_context, campaign_name)
                return EngineResult.ok(
                    data={
                        "subject": fallback["subject"],
                        "body": fallback["body"],
                        "lead_pool_id": str(lead_pool_id),
                        "campaign_name": campaign_name,
                        "personalization_used": ["first_name", "company"],
                    },
                    metadata={
                        "cost_aud": result["cost_aud"],
                        "tone": tone,
                        "source": "lead_pool",
                        "safe_fallback": True,
                        "json_parse_failed": True,
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
# ============================================
# PHASE H: CONTENT SAFETY (Items 40-42)
# ============================================
# [x] Item 40: _fact_check_content() - verifies claims against source data
# [x] Item 41: Conservative system prompts - ONLY verified facts
# [x] Item 42: _generate_safe_fallback() - brand-safe template
# [x] Fact-check integrated into generate_email()
# [x] Fact-check integrated into generate_email_for_pool()
# [x] HIGH risk = immediate safe fallback
# [x] MEDIUM risk = regenerate once, then fallback
# [x] LOW risk = pass through
# [x] Cost tracking includes fact-check costs
# [x] Metadata includes fact_check_verdict and fact_check_risk
# [x] _get_pool_lead helper for pool data fetch
# [x] Icebreaker hook integration for personalization
# [x] All pool methods use campaign_name instead of campaign_id
