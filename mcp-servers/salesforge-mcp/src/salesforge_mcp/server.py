"""
Salesforge MCP Server
Exposes Salesforge campaign management, WarmForge warmup status, and InfraForge domains.
"""
import os
import json
from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP("salesforge")

# API Configuration
SALESFORGE_API_URL = os.getenv("SALESFORGE_API_URL", "https://api.salesforge.ai/public/v2")
SALESFORGE_API_KEY = os.getenv("SALESFORGE_API_KEY", "")
WARMFORGE_API_URL = os.getenv("WARMFORGE_API_URL", "https://api.warmforge.ai/public/v1")
WARMFORGE_API_KEY = os.getenv("WARMFORGE_API_KEY", "")
INFRAFORGE_API_URL = os.getenv("INFRAFORGE_API_URL", "https://api.infraforge.ai/public")
INFRAFORGE_API_KEY = os.getenv("INFRAFORGE_API_KEY", "")


def get_salesforge_headers() -> dict:
    return {
        "Authorization": f"Bearer {SALESFORGE_API_KEY}",
        "Content-Type": "application/json",
    }


def get_warmforge_headers() -> dict:
    return {
        "Authorization": f"Bearer {WARMFORGE_API_KEY}",
        "Content-Type": "application/json",
    }


def get_infraforge_headers() -> dict:
    return {
        "Authorization": f"Bearer {INFRAFORGE_API_KEY}",
        "Content-Type": "application/json",
    }


async def api_request(
    method: str,
    url: str,
    headers: dict,
    json_data: dict | None = None,
    params: dict | None = None,
) -> dict[str, Any]:
    """Make an API request with error handling."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(
            method=method,
            url=url,
            headers=headers,
            json=json_data,
            params=params,
        )
        if response.status_code >= 400:
            return {
                "error": True,
                "status_code": response.status_code,
                "message": response.text,
            }
        try:
            return response.json()
        except json.JSONDecodeError:
            return {"raw_response": response.text}


@mcp.tool()
async def list_campaigns() -> dict[str, Any]:
    """
    List all Salesforge campaigns.
    Returns campaign IDs, names, status, and basic metrics.
    """
    return await api_request(
        "GET",
        f"{SALESFORGE_API_URL}/sequences",
        get_salesforge_headers(),
    )


@mcp.tool()
async def create_campaign(name: str, config: dict) -> dict[str, Any]:
    """
    Create a new Salesforge campaign.
    
    Args:
        name: Campaign name
        config: Campaign configuration including:
            - steps: List of email steps with subject, body, delay
            - settings: Send settings (daily limit, timezone, etc.)
            - tracking: Open/click tracking options
    """
    payload = {
        "name": name,
        **config,
    }
    return await api_request(
        "POST",
        f"{SALESFORGE_API_URL}/sequences",
        get_salesforge_headers(),
        json_data=payload,
    )


@mcp.tool()
async def get_campaign_stats(campaign_id: str) -> dict[str, Any]:
    """
    Get campaign statistics and metrics.
    
    Args:
        campaign_id: The campaign/sequence ID
        
    Returns:
        Metrics including sent, delivered, opened, clicked, replied, bounced counts.
    """
    return await api_request(
        "GET",
        f"{SALESFORGE_API_URL}/sequences/{campaign_id}/stats",
        get_salesforge_headers(),
    )


@mcp.tool()
async def add_leads(campaign_id: str, leads: list[dict]) -> dict[str, Any]:
    """
    Add leads to a Salesforge campaign.
    
    Args:
        campaign_id: The campaign/sequence ID
        leads: List of lead objects, each containing:
            - email: Lead email address (required)
            - firstName: First name
            - lastName: Last name
            - company: Company name
            - customFields: Dict of custom variables
    """
    payload = {"leads": leads}
    return await api_request(
        "POST",
        f"{SALESFORGE_API_URL}/sequences/{campaign_id}/leads",
        get_salesforge_headers(),
        json_data=payload,
    )


@mcp.tool()
async def pause_campaign(campaign_id: str) -> dict[str, Any]:
    """
    Pause a running campaign.
    
    Args:
        campaign_id: The campaign/sequence ID to pause
    """
    return await api_request(
        "POST",
        f"{SALESFORGE_API_URL}/sequences/{campaign_id}/pause",
        get_salesforge_headers(),
    )


@mcp.tool()
async def resume_campaign(campaign_id: str) -> dict[str, Any]:
    """
    Resume a paused campaign.
    
    Args:
        campaign_id: The campaign/sequence ID to resume
    """
    return await api_request(
        "POST",
        f"{SALESFORGE_API_URL}/sequences/{campaign_id}/resume",
        get_salesforge_headers(),
    )


@mcp.tool()
async def get_warmup_status() -> dict[str, Any]:
    """
    Get WarmForge email warmup status for all mailboxes.
    Returns warmup progress, reputation scores, and daily limits.
    """
    return await api_request(
        "GET",
        f"{WARMFORGE_API_URL}/mailboxes",
        get_warmforge_headers(),
    )


@mcp.tool()
async def list_domains() -> dict[str, Any]:
    """
    List all InfraForge domains and their configuration.
    Returns domain names, DNS status, and mailbox counts.
    """
    return await api_request(
        "GET",
        f"{INFRAFORGE_API_URL}/domains",
        get_infraforge_headers(),
    )


def main():
    """Run the MCP server."""
    import asyncio
    asyncio.run(mcp.run())


if __name__ == "__main__":
    main()
