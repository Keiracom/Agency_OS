# FILE: src/pipeline/stage5_email_enrichment.py
# PURPOSE: Stage 5 — Leadmagic email enrichment for business_universe DMs
# PIPELINE STAGE: 4 → 5
# DEPENDENCIES: src.integrations.leadmagic, asyncpg
# DIRECTIVE: #251

import logging
from decimal import Decimal

from src.integrations.leadmagic import (
    EmailStatus,
    LeadmagicClient,
    LeadmagicCreditExhaustedError,
    LeadmagicNoPlanError,
    LeadmagicRateLimitError,
)

logger = logging.getLogger(__name__)

# $0.015 AUD per email finder query (T3 cost, LAW II)
LEADMAGIC_EMAIL_COST_AUD = Decimal("0.01500")


class Stage5EmailEnrichment:
    """
    Stage 5: Email enrichment for decision-makers in business_universe.

    Processes rows at pipeline_stage=4, attempts to find DM email via Leadmagic,
    and advances them to pipeline_stage=5 with appropriate status.

    Path A: dm_linkedin_url present → parse dm_name + domain → find_email()
    Path B: domain only (no linkedin_url) → find_email() with domain fallback
    No path: mark email_no_path and advance

    Spend cap enforced per query. Pipeline stage advances regardless of outcome.
    """

    def __init__(self, leadmagic_client: LeadmagicClient, db) -> None:
        self.client = leadmagic_client
        self.db = db
        self._cost_accrued = Decimal("0")

    async def run(self, batch_size: int = 50, daily_spend_cap_aud: float = 15.0) -> dict:
        """
        For BU rows at pipeline_stage=4, attempt email enrichment.

        Returns:
            dict with keys: attempted, email_found, email_not_found,
                            skipped_no_path, cost_aud, errors
        """
        attempted = email_found = email_not_found = skipped_no_path = 0
        errors = []

        rows = await self.db.fetch(
            """
            SELECT id, display_name, domain, dm_linkedin_url, dm_source,
                   dm_name, propensity_score
            FROM business_universe
            WHERE pipeline_stage = 4
              AND pipeline_status IN ('dm_searched', 'dm_skipped_low_propensity', 'dm_found')
            LIMIT $1
            FOR UPDATE SKIP LOCKED
            """,
            batch_size,
        )

        for row in rows:
            # Spend cap check — advance stage but mark as skipped
            if self._cost_accrued + LEADMAGIC_EMAIL_COST_AUD > Decimal(str(daily_spend_cap_aud)):
                await self.db.execute(
                    """
                    UPDATE business_universe SET
                        pipeline_stage = 5,
                        pipeline_status = 'email_skipped_spend_cap',
                        last_enriched_at = NOW()
                    WHERE id = $1
                    """,
                    row["id"],
                )
                continue

            email_result = None
            source_override = None

            try:
                if row["dm_linkedin_url"]:
                    # Path A: have LinkedIn URL — use dm_name + domain to call find_email()
                    email_result = await self._find_email_by_linkedin(row)
                elif row["domain"]:
                    # Path B: domain only fallback
                    email_result = await self._find_email_by_domain(row)
                    source_override = "leadmagic_domain"
                else:
                    # No enrichment path available — advance without cost
                    await self.db.execute(
                        """
                        UPDATE business_universe SET
                            pipeline_stage = 5,
                            pipeline_status = 'email_no_path',
                            last_enriched_at = NOW()
                        WHERE id = $1
                        """,
                        row["id"],
                    )
                    skipped_no_path += 1
                    continue

                attempted += 1
                self._cost_accrued += LEADMAGIC_EMAIL_COST_AUD

                if email_result:
                    email = email_result.get("email")
                    verified = email_result.get("verified", False)
                    confidence = email_result.get("confidence")

                    # Build UPDATE — only set dm_source if it was null and we have an override
                    update_params = [
                        email,
                        verified,
                        confidence,
                        LEADMAGIC_EMAIL_COST_AUD,
                        row["id"],
                    ]
                    source_sql = ""
                    if source_override and not row["dm_source"]:
                        source_sql = ", dm_source = $6"
                        update_params.append(source_override)

                    await self.db.execute(
                        f"""
                        UPDATE business_universe SET
                            dm_email = $1,
                            dm_email_verified = $2,
                            dm_email_confidence = $3,
                            enrichment_cost_aud = COALESCE(enrichment_cost_aud, 0) + $4,
                            last_enriched_at = NOW(),
                            pipeline_stage = 5,
                            pipeline_status = 'email_found'{source_sql}
                        WHERE id = $5
                        """,
                        *update_params,
                    )
                    email_found += 1
                else:
                    await self.db.execute(
                        """
                        UPDATE business_universe SET
                            enrichment_cost_aud = COALESCE(enrichment_cost_aud, 0) + $1,
                            last_enriched_at = NOW(),
                            pipeline_stage = 5,
                            pipeline_status = 'email_not_found'
                        WHERE id = $2
                        """,
                        LEADMAGIC_EMAIL_COST_AUD,
                        row["id"],
                    )
                    email_not_found += 1

            except (LeadmagicRateLimitError, LeadmagicCreditExhaustedError, LeadmagicNoPlanError):
                # Re-raise fatal/billing errors — let caller decide
                raise
            except Exception as e:
                errors.append({"id": str(row["id"]), "error": str(e)})
                logger.warning(
                    f"[Stage5] Email enrichment error for id={row['id']}: {e}"
                )
                await self.db.execute(
                    """
                    UPDATE business_universe SET
                        pipeline_stage = 5,
                        pipeline_status = 'email_error',
                        last_enriched_at = NOW()
                    WHERE id = $1
                    """,
                    row["id"],
                )

        logger.info(
            f"[Stage5] Complete — attempted={attempted}, found={email_found}, "
            f"not_found={email_not_found}, no_path={skipped_no_path}, "
            f"cost=${float(self._cost_accrued):.4f} AUD, errors={len(errors)}"
        )

        return {
            "attempted": attempted,
            "email_found": email_found,
            "email_not_found": email_not_found,
            "skipped_no_path": skipped_no_path,
            "cost_aud": float(self._cost_accrued),
            "errors": errors,
        }

    async def _find_email_by_linkedin(self, row: dict) -> dict | None:
        """
        Path A: Use dm_name + domain to call find_email().

        find_email() signature (from src/integrations/leadmagic.py):
            find_email(first_name, last_name, domain, company=None) -> EmailFinderResult

        EmailFinderResult fields used: .found, .email, .confidence, .status
        EmailStatus.VALID maps to verified=True.
        """
        dm_name = (row.get("dm_name") or "").strip()
        domain = (row.get("domain") or "").strip()
        company = (row.get("display_name") or "").strip() or None

        # Parse first/last name — split on first space
        parts = dm_name.split(" ", 1)
        first_name = parts[0] if parts else ""
        last_name = parts[1] if len(parts) > 1 else ""

        # Need domain + both name parts to proceed
        if not domain or not first_name or not last_name:
            logger.debug(
                f"[Stage5] _find_email_by_linkedin: insufficient data "
                f"(dm_name={dm_name!r}, domain={domain!r}) — skipping"
            )
            return None

        result = await self.client.find_email(
            first_name=first_name,
            last_name=last_name,
            domain=domain,
            company=company,
        )

        if not result.found or not result.email:
            return None

        return {
            "email": result.email,
            "verified": result.status == EmailStatus.VALID,
            "confidence": result.confidence,
        }

    async def _find_email_by_domain(self, row: dict) -> dict | None:
        """
        Path B: Domain-only fallback — still calls find_email() with dm_name if available.

        find_email() signature (from src/integrations/leadmagic.py):
            find_email(first_name, last_name, domain, company=None) -> EmailFinderResult

        If dm_name is absent, we cannot call find_email (requires first+last names).
        Returns None in that case; caller will mark email_not_found.
        """
        dm_name = (row.get("dm_name") or "").strip()
        domain = (row.get("domain") or "").strip()
        company = (row.get("display_name") or "").strip() or None

        if not domain:
            return None

        # Parse first/last from dm_name if present
        parts = dm_name.split(" ", 1)
        first_name = parts[0] if parts else ""
        last_name = parts[1] if len(parts) > 1 else ""

        if not first_name or not last_name:
            # No name data — cannot call find_email(); treat as not found
            logger.debug(
                f"[Stage5] _find_email_by_domain: no dm_name for domain={domain!r} — cannot enrich"
            )
            return None

        result = await self.client.find_email(
            first_name=first_name,
            last_name=last_name,
            domain=domain,
            company=company,
        )

        if not result.found or not result.email:
            return None

        return {
            "email": result.email,
            "verified": result.status == EmailStatus.VALID,
            "confidence": result.confidence,
        }
