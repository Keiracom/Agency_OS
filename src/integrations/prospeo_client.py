"""
Contract: src/integrations/prospeo_client.py
Purpose: Prospeo email finder and verifier client (Layer 2.5 in email waterfall)
Layer: 2 - integrations
Imports: models only
Consumers: email_waterfall.py
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

PROSPEO_BASE = "https://api.prospeo.io"
COST_FIND = 0.01  # USD per find_email call
COST_VERIFY = 0.01  # USD per verify call


@dataclass
class ProspeoResult:
    email: str | None
    verified: bool
    confidence: int
    status: str  # "valid" | "risky" | "unknown" | "invalid"
    cost_usd: float


class ProspeoClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def find_email(self, full_name: str, domain: str) -> ProspeoResult | None:
        """Find email for a person by name + domain."""
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    f"{PROSPEO_BASE}/email-finder",
                    json={"full_name": full_name, "domain": domain},
                    headers={"X-KEY": self.api_key, "Content-Type": "application/json"},
                )
                if r.status_code != 200:
                    logger.warning("prospeo find_email %d: %s", r.status_code, r.text[:200])
                    return None
                data = r.json().get("response", {})
                email = data.get("email")
                if not email:
                    return None
                return ProspeoResult(
                    email=email,
                    verified=data.get("email_status") == "valid",
                    confidence=data.get("confidence", 0),
                    status=data.get("email_status", "unknown"),
                    cost_usd=COST_FIND,
                )
        except Exception as e:
            logger.warning("prospeo find_email error: %s", e)
            return None

    async def verify_email(self, email: str) -> ProspeoResult | None:
        """Verify an email address."""
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    f"{PROSPEO_BASE}/email-verifier",
                    json={"email": email},
                    headers={"X-KEY": self.api_key, "Content-Type": "application/json"},
                )
                if r.status_code != 200:
                    logger.warning("prospeo verify_email %d: %s", r.status_code, r.text[:200])
                    return None
                data = r.json().get("response", {})
                return ProspeoResult(
                    email=email,
                    verified=data.get("email_status") == "valid",
                    confidence=90 if data.get("email_status") == "valid" else 30,
                    status=data.get("email_status", "unknown"),
                    cost_usd=COST_VERIFY,
                )
        except Exception as e:
            logger.warning("prospeo verify_email error: %s", e)
            return None
