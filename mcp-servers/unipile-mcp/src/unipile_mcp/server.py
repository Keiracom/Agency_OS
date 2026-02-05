"""
Unipile MCP Server
Exposes LinkedIn automation via Unipile API.
"""
import os
import json
from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP("unipile")

# API Configuration - Unipile uses a custom DSN-based URL
UNIPILE_API_URL = os.getenv("UNIPILE_API_URL", "https://api22.unipile.com:15268")
UNIPILE_API_KEY = os.getenv("UNIPILE_API_KEY", "")


def get_headers() -> dict:
    return {
        "X-API-KEY": UNIPILE_API_KEY,
        "Content-Type": "application/json",
    }


async def api_request(
    method: str,
    endpoint: str,
    json_data: dict | None = None,
    params: dict | None = None,
) -> dict[str, Any]:
    """Make an API request with error handling."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.request(
            method=method,
            url=f"{UNIPILE_API_URL}/api/v1{endpoint}",
            headers=get_headers(),
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
async def search_profiles(
    query: str,
    limit: int = 25,
    connection_degree: str | None = None,
) -> dict[str, Any]:
    """
    Search LinkedIn profiles.
    
    Args:
        query: Search query (name, title, company, keywords)
        limit: Max results (default 25)
        connection_degree: Filter by connection (1st, 2nd, 3rd)
    """
    params = {
        "q": query,
        "limit": limit,
    }
    if connection_degree:
        params["connection_degree"] = connection_degree
    
    return await api_request("GET", "/linkedin/search/people", params=params)


@mcp.tool()
async def get_profile(profile_id: str) -> dict[str, Any]:
    """
    Get detailed LinkedIn profile information.
    
    Args:
        profile_id: LinkedIn profile ID or vanity URL
        
    Returns:
        Full profile including experience, education, skills.
    """
    return await api_request("GET", f"/linkedin/profile/{profile_id}")


@mcp.tool()
async def send_connection(
    profile_id: str,
    message: str | None = None,
) -> dict[str, Any]:
    """
    Send a LinkedIn connection request.
    
    Args:
        profile_id: LinkedIn profile ID to connect with
        message: Optional connection note (300 char limit)
    """
    payload = {"profile_id": profile_id}
    if message:
        payload["message"] = message[:300]  # LinkedIn limit
    
    return await api_request("POST", "/linkedin/invitation", json_data=payload)


@mcp.tool()
async def send_message(
    profile_id: str,
    message: str,
) -> dict[str, Any]:
    """
    Send a direct message to a LinkedIn connection.
    
    Args:
        profile_id: LinkedIn profile ID (must be connected)
        message: Message content
    """
    payload = {
        "profile_id": profile_id,
        "text": message,
    }
    return await api_request("POST", "/linkedin/message", json_data=payload)


@mcp.tool()
async def list_connections(
    limit: int = 50,
    cursor: str | None = None,
) -> dict[str, Any]:
    """
    List your LinkedIn connections.
    
    Args:
        limit: Results per page (default 50)
        cursor: Pagination cursor from previous response
    """
    params = {"limit": limit}
    if cursor:
        params["cursor"] = cursor
    
    return await api_request("GET", "/linkedin/connections", params=params)


@mcp.tool()
async def get_account_status() -> dict[str, Any]:
    """
    Get linked LinkedIn account health and status.
    
    Returns:
        Account status, connection count, daily limits, restrictions.
    """
    return await api_request("GET", "/accounts")


@mcp.tool()
async def list_conversations(limit: int = 25) -> dict[str, Any]:
    """
    List LinkedIn message conversations.
    
    Args:
        limit: Results per page (default 25)
    """
    return await api_request("GET", "/linkedin/conversations", params={"limit": limit})


@mcp.tool()
async def get_conversation(conversation_id: str) -> dict[str, Any]:
    """
    Get messages in a specific conversation.
    
    Args:
        conversation_id: The conversation ID
    """
    return await api_request("GET", f"/linkedin/conversations/{conversation_id}/messages")


@mcp.tool()
async def withdraw_invitation(invitation_id: str) -> dict[str, Any]:
    """
    Withdraw a pending connection request.
    
    Args:
        invitation_id: The invitation ID to withdraw
    """
    return await api_request("DELETE", f"/linkedin/invitation/{invitation_id}")


@mcp.tool()
async def list_pending_invitations(
    direction: str = "sent",
    limit: int = 25,
) -> dict[str, Any]:
    """
    List pending connection invitations.
    
    Args:
        direction: 'sent' or 'received'
        limit: Results per page (default 25)
    """
    return await api_request(
        "GET",
        "/linkedin/invitations",
        params={"direction": direction, "limit": limit},
    )


def main():
    """Run the MCP server."""
    import asyncio
    asyncio.run(mcp.run())


if __name__ == "__main__":
    main()
