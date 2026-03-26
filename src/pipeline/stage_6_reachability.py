"""
Stage 6 Reachability Validation — Architecture v5
Directive #264

Validates contact channels for S5-completed businesses and determines
which outreach channels are actually available.

Reads pipeline_stage=5, writes pipeline_stage=6.
Updates reachability_score and outreach_channels.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

import asyncpg

from src.enrichment.signal_config import SignalConfigRepository

logger = logging.getLogger(__name__)

PIPELINE_STAGE_S6 = 6

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
_AU_PHONE_RE = re.compile(r"^(\+61|0)(4|2|3|7|8)\d[\d\s\-\.]{6,12}$")
_LINKEDIN_PROFILE_RE = re.compile(r"^https?://(www\.)?linkedin\.com/in/[a-zA-Z0-9\-_%]+/?$")


def validate_email(email: str | None) -> bool:
    if not email:
        return False
    return bool(_EMAIL_RE.match(email.strip()))


def validate_au_phone(phone: str | None) -> bool:
    if not phone:
        return False
    return bool(_AU_PHONE_RE.match(phone.strip().replace(" ", "")))


def validate_linkedin_url(url: str | None) -> bool:
    if not url:
        return False
    return bool(_LINKEDIN_PROFILE_RE.match(url.strip()))


def calculate_reachability(channels: list[str]) -> int:
    """Reachability score from confirmed channels."""
    score = 0
    if "email" in channels:
        score += 30
    if "voice" in channels or "sms" in channels:
        score += 25
    if "linkedin" in channels:
        score += 20
    if "physical" in channels:
        score += 15
    if score > 0:
        score += 10  # base: business is contactable at all
    return min(score, 100)


class Stage6Reachability:
    """
    Validate contact channels and finalise reachability for S5-completed businesses.

    Usage:
        stage = Stage6Reachability(signal_repo, conn)
        result = await stage.run("marketing_agency", batch_size=100)
    """

    def __init__(
        self,
        signal_repo: SignalConfigRepository,
        conn: asyncpg.Connection,
    ) -> None:
        self.signal_repo = signal_repo
        self.conn = conn

    async def run(
        self,
        vertical_slug: str,
        batch_size: int = 100,
    ) -> dict[str, Any]:
        """
        Validate channels for S5-completed businesses.
        Returns {validated, channels_confirmed}
        """
        config = await self.signal_repo.get_config(vertical_slug)
        channel_config = config.channel_config  # e.g. {"email": True, "linkedin": True, "voice": True, "sms": False}

        rows = await self.conn.fetch(
            """
            SELECT id, dm_email, dm_phone, dm_linkedin_url,
                   address, state, suburb, gmb_place_id
            FROM business_universe
            WHERE pipeline_stage = 5
            ORDER BY pipeline_updated_at ASC
            LIMIT $1
            """,
            batch_size,
        )

        validated = 0
        channels_confirmed: dict[str, int] = {}

        for row in rows:
            channels = self._validate_channels(dict(row), channel_config)
            reachability = calculate_reachability(channels)
            now = datetime.now(timezone.utc)

            await self.conn.execute(
                """
                UPDATE business_universe SET
                    outreach_channels = $1,
                    reachability_score = $2,
                    pipeline_stage = $3,
                    pipeline_updated_at = $4
                WHERE id = $5
                """,
                channels,
                reachability,
                PIPELINE_STAGE_S6,
                now,
                row["id"],
            )
            validated += 1
            for ch in channels:
                channels_confirmed[ch] = channels_confirmed.get(ch, 0) + 1

        return {"validated": validated, "channels_confirmed": channels_confirmed}

    def _validate_channels(
        self,
        business: dict[str, Any],
        channel_config: dict[str, bool],
    ) -> list[str]:
        """Determine which channels are both validated and enabled in config."""
        confirmed = []
        if channel_config.get("email") and validate_email(business.get("dm_email")):
            confirmed.append("email")
        if channel_config.get("linkedin") and validate_linkedin_url(business.get("dm_linkedin_url")):
            confirmed.append("linkedin")
        if channel_config.get("voice") and validate_au_phone(business.get("dm_phone")):
            confirmed.append("voice")
        if channel_config.get("sms") and validate_au_phone(business.get("dm_phone")):
            confirmed.append("sms")
        has_address = any([business.get("address"), business.get("state"), business.get("gmb_place_id")])
        if has_address:
            confirmed.append("physical")
        return confirmed
