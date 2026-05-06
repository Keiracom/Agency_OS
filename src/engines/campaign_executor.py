"""src/engines/campaign_executor.py — Campaign execution loop.

Connects BU prospects → sequence steps → email send → tracking.
Designed to be called from a Prefect flow or CLI script.

Usage:
    from src.engines.campaign_executor import CampaignExecutor

    executor = CampaignExecutor(
        sequence_path="campaigns/dental_sequence_v1.json",
        step=1,
        dry_run=True,
    )
    results = await executor.run()
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ProspectRecord:
    """A BU row eligible for outreach."""

    id: str
    domain: str
    dm_email: str
    dm_name: str | None = None
    company_name: str | None = None
    industry: str | None = None


@dataclass
class SendResult:
    """Result of a single send attempt."""

    prospect_id: str
    email: str
    status: str  # "sent", "skipped", "suppressed", "dry_run", "error"
    message_id: str | None = None
    error: str | None = None


@dataclass
class SequenceStep:
    """One step in a campaign sequence."""

    step_number: int
    subject_template: str
    body_template: str
    delay_days: int = 0
    channel: str = "email"


class CampaignExecutor:
    """Execute a campaign sequence against BU prospects.

    Queries business_universe for eligible prospects (verified email,
    not suppressed, not already sent this step), renders merge tags,
    sends via Resend, and tracks results.
    """

    def __init__(
        self,
        *,
        sequence_path: str | None = None,
        sequence_steps: list[dict] | None = None,
        step: int = 1,
        daily_limit: int = 50,
        dry_run: bool = True,
        from_address: str | None = None,
        filter_industry: str | None = None,
        min_confidence: int = 70,
    ):
        self.step = step
        self.daily_limit = daily_limit
        self.dry_run = dry_run
        self.from_address = from_address or os.environ.get(
            "RESEND_DEFAULT_FROM",
            "noreply@keiracom.com",
        )
        self.filter_industry = filter_industry
        self.min_confidence = min_confidence
        self._results: list[SendResult] = []

        # Load sequence
        if sequence_steps:
            self.steps = [SequenceStep(**self._normalize_step(s)) for s in sequence_steps]
        elif sequence_path:
            self.steps = self._load_sequence(sequence_path)
        else:
            raise ValueError("Either sequence_path or sequence_steps required")

    @staticmethod
    def _normalize_step(raw: dict) -> dict:
        """Normalize step dict to SequenceStep fields.

        Handles both schemas:
        - Ours: {"step_number": 1, "subject_template": "...", "body_template": "..."}
        - Aiden's: {"step": 1, "subject": "...", "body_text": "...", "body_html": "..."}
        """
        out = dict(raw)
        # step → step_number
        if "step" in out and "step_number" not in out:
            out["step_number"] = out.pop("step")
        # subject → subject_template
        if "subject" in out and "subject_template" not in out:
            out["subject_template"] = out.pop("subject")
        # body_text or body_html → body_template
        if "body_template" not in out:
            out["body_template"] = out.pop("body_text", None) or out.pop("body_html", "")
        # Drop extra keys that SequenceStep doesn't accept
        valid = {"step_number", "subject_template", "body_template", "delay_days", "channel"}
        return {k: v for k, v in out.items() if k in valid}

    @staticmethod
    def _load_sequence(path: str) -> list[SequenceStep]:
        """Load sequence steps from a JSON file.

        Accepts both schema variants:
        - {"steps": [...]} (CampaignExecutor native)
        - {"emails": [...]} (campaign_sender.py / Aiden's format)
        """
        data = json.loads(Path(path).read_text())
        steps_data = data.get("steps") or data.get("emails") or data
        if isinstance(steps_data, list):
            return [SequenceStep(**CampaignExecutor._normalize_step(s)) for s in steps_data]
        raise ValueError(f"Invalid sequence format in {path}")

    def _render_template(self, template: str, prospect: ProspectRecord) -> str:
        """Replace merge tags in a template string."""
        first_name = ""
        if prospect.dm_name:
            parts = prospect.dm_name.strip().split()
            first_name = parts[0] if parts else ""

        replacements = {
            "{{first_name}}": first_name or "there",
            "{{company_name}}": prospect.company_name or "your practice",
            "{{domain}}": prospect.domain or "",
            "{{industry}}": prospect.industry or "",
            "{{email}}": prospect.dm_email or "",
        }
        result = template
        for tag, value in replacements.items():
            result = result.replace(tag, value)
        return result

    async def _fetch_prospects(self) -> list[ProspectRecord]:
        """Query BU for eligible prospects."""
        import asyncpg

        dsn = os.environ.get("DATABASE_URL_MIGRATIONS") or os.environ.get("DATABASE_URL", "")
        if dsn.startswith("postgresql+asyncpg://"):
            dsn = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)

        where_clauses = [
            "dm_email IS NOT NULL",
            "dm_email_verified = true",
            f"COALESCE(dm_email_confidence, 0) >= {self.min_confidence}",
            "NOT EXISTS (SELECT 1 FROM public.global_suppression gs WHERE LOWER(gs.email) = LOWER(bu.dm_email))",
        ]
        if self.filter_industry:
            where_clauses.append(f"industry ILIKE '%{self.filter_industry}%'")

        sql = (
            "SELECT id::text, domain, dm_email, dm_name, company_name, industry "
            "FROM public.business_universe bu "
            f"WHERE {' AND '.join(where_clauses)} "
            f"ORDER BY COALESCE(dm_email_confidence, 0) DESC "
            f"LIMIT {self.daily_limit}"
        )

        conn = await asyncpg.connect(dsn)
        try:
            rows = await conn.fetch(sql)
            return [
                ProspectRecord(
                    id=r["id"],
                    domain=r["domain"] or "",
                    dm_email=r["dm_email"],
                    dm_name=r.get("dm_name"),
                    company_name=r.get("company_name"),
                    industry=r.get("industry"),
                )
                for r in rows
            ]
        finally:
            await conn.close()

    async def _send_one(self, prospect: ProspectRecord, step: SequenceStep) -> SendResult:
        """Send one email to a prospect for a given sequence step."""
        subject = self._render_template(step.subject_template, prospect)
        body = self._render_template(step.body_template, prospect)

        if self.dry_run:
            logger.info(
                "[campaign] DRY RUN: to=%s subject=%s",
                prospect.dm_email,
                subject,
            )
            return SendResult(
                prospect_id=prospect.id,
                email=prospect.dm_email,
                status="dry_run",
            )

        try:
            from src.integrations.resend_client import send_email

            result = send_email(
                to=prospect.dm_email,
                subject=subject,
                body_text=body,
                from_address=self.from_address,
            )
            message_id = result.get("id", "")
            logger.info(
                "[campaign] sent: to=%s message_id=%s",
                prospect.dm_email,
                message_id,
            )
            return SendResult(
                prospect_id=prospect.id,
                email=prospect.dm_email,
                status="sent",
                message_id=message_id,
            )
        except Exception as exc:
            logger.error(
                "[campaign] send failed: to=%s error=%s",
                prospect.dm_email,
                exc,
            )
            return SendResult(
                prospect_id=prospect.id,
                email=prospect.dm_email,
                status="error",
                error=str(exc),
            )

    async def run(self) -> list[SendResult]:
        """Execute the campaign step against eligible prospects."""
        # Find the step
        current_step = None
        for s in self.steps:
            if s.step_number == self.step:
                current_step = s
                break
        if not current_step:
            raise ValueError(f"Step {self.step} not found in sequence")

        # Fetch prospects
        prospects = await self._fetch_prospects()
        logger.info(
            "[campaign] found %d eligible prospects (step=%d, dry_run=%s)",
            len(prospects),
            self.step,
            self.dry_run,
        )

        if not prospects:
            return []

        # Send to each prospect
        results = []
        for i, prospect in enumerate(prospects, 1):
            result = await self._send_one(prospect, current_step)
            results.append(result)
            logger.info(
                "[campaign] [%d/%d] %s → %s",
                i,
                len(prospects),
                prospect.dm_email,
                result.status,
            )

        # Summary
        sent = sum(1 for r in results if r.status == "sent")
        dry = sum(1 for r in results if r.status == "dry_run")
        errors = sum(1 for r in results if r.status == "error")
        logger.info(
            "[campaign] complete: sent=%d dry_run=%d errors=%d total=%d",
            sent,
            dry,
            errors,
            len(results),
        )

        self._results = results
        return results

    def summary(self) -> dict[str, Any]:
        """Return a summary of the last run."""
        return {
            "step": self.step,
            "dry_run": self.dry_run,
            "total": len(self._results),
            "sent": sum(1 for r in self._results if r.status == "sent"),
            "dry_run_count": sum(1 for r in self._results if r.status == "dry_run"),
            "errors": sum(1 for r in self._results if r.status == "error"),
            "suppressed": sum(1 for r in self._results if r.status == "suppressed"),
        }
