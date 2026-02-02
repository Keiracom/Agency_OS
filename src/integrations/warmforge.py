"""
WarmForge Integration - Domain Warmup Status Monitoring
API: https://api.warmforge.ai/public/v1 (NOT v2!)
Auth: Authorization header (plain key, no Bearer)
Required params: page, page_size for list endpoints

Purpose: Check domain warmup status to determine when domains are ready for production use.
Consumed by: warmup_monitor_flow
"""

import httpx
from src.config.settings import get_settings


class WarmForgeClient:
    """Client for WarmForge domain warmup API."""

    def __init__(self):
        settings = get_settings()
        self.api_url = settings.warmforge_api_url
        self.api_key = settings.warmforge_api_key
        self._client = httpx.AsyncClient(
            base_url=self.api_url,
            headers={"Authorization": self.api_key, "Content-Type": "application/json"},
            timeout=30.0,
        )

    async def list_mailboxes(self, page: int = 1, page_size: int = 100) -> dict:
        """
        List all mailboxes with warmup status.

        Args:
            page: Page number (1-indexed)
            page_size: Results per page

        Returns:
            Dict with 'data' list containing mailbox records
        """
        resp = await self._client.get(
            "/mailboxes",
            params={"page": page, "page_size": page_size}
        )
        resp.raise_for_status()
        return resp.json()

    async def get_mailbox(self, mailbox_id: str) -> dict:
        """
        Get single mailbox warmup status.

        Args:
            mailbox_id: WarmForge mailbox ID

        Returns:
            Mailbox record with warmup status
        """
        resp = await self._client.get(f"/mailboxes/{mailbox_id}")
        resp.raise_for_status()
        return resp.json()

    async def get_mailbox_by_email(self, email: str) -> dict | None:
        """
        Find mailbox by email address.

        Args:
            email: Email address to look up

        Returns:
            Mailbox record or None if not found
        """
        # WarmForge may require pagination to find specific email
        page = 1
        while True:
            result = await self.list_mailboxes(page=page, page_size=100)
            mailboxes = result.get("data", [])

            if not mailboxes:
                break

            for mailbox in mailboxes:
                if mailbox.get("email") == email:
                    return mailbox

            # Check if more pages exist
            total = result.get("total", 0)
            if page * 100 >= total:
                break
            page += 1

        return None

    async def get_domain_warmup_status(self, domain: str) -> dict:
        """
        Get aggregated warmup status for a domain.

        Checks all mailboxes for the domain and returns combined status.

        Args:
            domain: Domain name (e.g., 'example.com')

        Returns:
            Dict with:
                - warm: bool (all mailboxes warmed)
                - heat_score: int (average heat score)
                - mailbox_count: int
                - warmed_count: int
                - mailboxes: list of mailbox records
        """
        page = 1
        domain_mailboxes = []

        while True:
            result = await self.list_mailboxes(page=page, page_size=100)
            mailboxes = result.get("data", [])

            if not mailboxes:
                break

            for mailbox in mailboxes:
                email = mailbox.get("email", "")
                if email.endswith(f"@{domain}"):
                    domain_mailboxes.append(mailbox)

            # Check if more pages exist
            total = result.get("total", 0)
            if page * 100 >= total:
                break
            page += 1

        if not domain_mailboxes:
            return {
                "warm": False,
                "heat_score": 0,
                "mailbox_count": 0,
                "warmed_count": 0,
                "mailboxes": [],
            }

        # Calculate aggregate status
        heat_scores = []
        warmed_count = 0

        for mailbox in domain_mailboxes:
            heat_score = mailbox.get("heatScore", 0) or mailbox.get("heat_score", 0)
            heat_scores.append(heat_score)
            # Consider warmed if heat score >= 85
            if heat_score >= 85:
                warmed_count += 1

        avg_heat_score = sum(heat_scores) / len(heat_scores) if heat_scores else 0
        all_warmed = warmed_count == len(domain_mailboxes) and len(domain_mailboxes) > 0

        return {
            "warm": all_warmed,
            "heat_score": int(avg_heat_score),
            "mailbox_count": len(domain_mailboxes),
            "warmed_count": warmed_count,
            "mailboxes": domain_mailboxes,
        }

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()


# Module-level singleton
_client: WarmForgeClient | None = None


def get_warmforge_client() -> WarmForgeClient:
    """Get or create WarmForge client singleton."""
    global _client
    if _client is None:
        _client = WarmForgeClient()
    return _client


async def check_domain_warmup(domain: str) -> dict:
    """
    Convenience function to check domain warmup status.

    Args:
        domain: Domain name to check

    Returns:
        Warmup status dict
    """
    client = get_warmforge_client()
    return await client.get_domain_warmup_status(domain)
