"""
Telnyx MCP Server
Exposes Telnyx SMS, voice, and phone number management.
"""
import os
import json
from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP("telnyx")

# API Configuration
TELNYX_API_URL = os.getenv("TELNYX_API_URL", "https://api.telnyx.com/v2")
TELNYX_API_KEY = os.getenv("TELNYX_API_KEY", "")


def get_headers() -> dict:
    return {
        "Authorization": f"Bearer {TELNYX_API_KEY}",
        "Content-Type": "application/json",
    }


async def api_request(
    method: str,
    endpoint: str,
    json_data: dict | None = None,
    params: dict | None = None,
) -> dict[str, Any]:
    """Make an API request with error handling."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(
            method=method,
            url=f"{TELNYX_API_URL}{endpoint}",
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
async def send_sms(from_number: str, to_number: str, text: str) -> dict[str, Any]:
    """
    Send an SMS message via Telnyx.
    
    Args:
        from_number: Sender phone number (must be Telnyx number, E.164 format)
        to_number: Recipient phone number (E.164 format)
        text: Message content
    """
    payload = {
        "from": from_number,
        "to": to_number,
        "text": text,
    }
    return await api_request("POST", "/messages", json_data=payload)


@mcp.tool()
async def list_phone_numbers(page_size: int = 25) -> dict[str, Any]:
    """
    List all Telnyx phone numbers (DIDs).
    
    Args:
        page_size: Results per page (default 25)
    """
    return await api_request("GET", "/phone_numbers", params={"page[size]": page_size})


@mcp.tool()
async def search_available_numbers(
    country_code: str = "US",
    area_code: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """
    Search for available phone numbers to purchase.
    
    Args:
        country_code: ISO country code (default US)
        area_code: Filter by area code (optional)
        limit: Max results (default 10)
    """
    params = {
        "filter[country_code]": country_code,
        "filter[limit]": limit,
    }
    if area_code:
        params["filter[national_destination_code]"] = area_code
    
    return await api_request("GET", "/available_phone_numbers", params=params)


@mcp.tool()
async def buy_number(phone_number: str, connection_id: str | None = None) -> dict[str, Any]:
    """
    Purchase a phone number.
    
    Args:
        phone_number: The phone number to purchase (from search results)
        connection_id: Optional connection/app ID to assign
    """
    payload = {
        "phone_numbers": [{"phone_number": phone_number}],
    }
    if connection_id:
        payload["connection_id"] = connection_id
    
    return await api_request("POST", "/number_orders", json_data=payload)


@mcp.tool()
async def make_call(from_number: str, to_number: str, connection_id: str) -> dict[str, Any]:
    """
    Initiate an outbound voice call.
    
    Args:
        from_number: Caller ID (must be Telnyx number)
        to_number: Destination number (E.164 format)
        connection_id: Telnyx connection/app ID for call control
    """
    payload = {
        "from": from_number,
        "to": to_number,
        "connection_id": connection_id,
    }
    return await api_request("POST", "/calls", json_data=payload)


@mcp.tool()
async def list_calls(page_size: int = 25) -> dict[str, Any]:
    """
    List recent calls.
    
    Args:
        page_size: Results per page (default 25)
    """
    return await api_request("GET", "/calls", params={"page[size]": page_size})


@mcp.tool()
async def get_call(call_control_id: str) -> dict[str, Any]:
    """
    Get details of a specific call.
    
    Args:
        call_control_id: The call control ID
    """
    return await api_request("GET", f"/calls/{call_control_id}")


@mcp.tool()
async def get_usage(
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """
    Get account usage statistics.
    
    Args:
        start_date: Start date (YYYY-MM-DD format)
        end_date: End date (YYYY-MM-DD format)
    """
    params = {}
    if start_date:
        params["filter[start_date]"] = start_date
    if end_date:
        params["filter[end_date]"] = end_date
    
    return await api_request("GET", "/reports/ledger_billing_group_reports", params=params)


@mcp.tool()
async def get_message(message_id: str) -> dict[str, Any]:
    """
    Get details of a sent/received message.
    
    Args:
        message_id: The message ID
    """
    return await api_request("GET", f"/messages/{message_id}")


def main():
    """Run the MCP server."""
    import asyncio
    asyncio.run(mcp.run())


if __name__ == "__main__":
    main()
