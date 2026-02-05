"""
Vapi MCP Server
Exposes Vapi voice AI assistant management and call control.
"""
import os
import json
from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP("vapi")

# API Configuration
VAPI_API_URL = os.getenv("VAPI_API_URL", "https://api.vapi.ai")
VAPI_API_KEY = os.getenv("VAPI_API_KEY", "")


def get_headers() -> dict:
    return {
        "Authorization": f"Bearer {VAPI_API_KEY}",
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
            url=f"{VAPI_API_URL}{endpoint}",
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
async def list_assistants() -> dict[str, Any]:
    """
    List all Vapi voice assistants.
    Returns assistant IDs, names, configurations.
    """
    return await api_request("GET", "/assistant")


@mcp.tool()
async def create_assistant(config: dict) -> dict[str, Any]:
    """
    Create a new Vapi voice assistant.
    
    Args:
        config: Assistant configuration including:
            - name: Assistant name
            - model: LLM config (provider, model, systemPrompt)
            - voice: Voice config (provider, voiceId)
            - firstMessage: Opening message
            - transcriber: STT config
    """
    return await api_request("POST", "/assistant", json_data=config)


@mcp.tool()
async def update_assistant(assistant_id: str, config: dict) -> dict[str, Any]:
    """
    Update an existing Vapi assistant.
    
    Args:
        assistant_id: The assistant ID to update
        config: Updated configuration (partial update supported)
    """
    return await api_request("PATCH", f"/assistant/{assistant_id}", json_data=config)


@mcp.tool()
async def get_assistant(assistant_id: str) -> dict[str, Any]:
    """
    Get details of a specific assistant.
    
    Args:
        assistant_id: The assistant ID
    """
    return await api_request("GET", f"/assistant/{assistant_id}")


@mcp.tool()
async def delete_assistant(assistant_id: str) -> dict[str, Any]:
    """
    Delete a Vapi assistant.
    
    Args:
        assistant_id: The assistant ID to delete
    """
    return await api_request("DELETE", f"/assistant/{assistant_id}")


@mcp.tool()
async def start_call(assistant_id: str, phone_number: str, phone_number_id: str | None = None) -> dict[str, Any]:
    """
    Initiate an outbound call using a Vapi assistant.
    
    Args:
        assistant_id: The assistant to use for the call
        phone_number: Destination phone number (E.164 format)
        phone_number_id: Optional Vapi phone number ID to call from
    """
    payload = {
        "assistantId": assistant_id,
        "customer": {
            "number": phone_number,
        },
    }
    if phone_number_id:
        payload["phoneNumberId"] = phone_number_id
    
    return await api_request("POST", "/call/phone", json_data=payload)


@mcp.tool()
async def get_call(call_id: str) -> dict[str, Any]:
    """
    Get call status and details.
    
    Args:
        call_id: The call ID
        
    Returns:
        Call status, duration, cost, and metadata.
    """
    return await api_request("GET", f"/call/{call_id}")


@mcp.tool()
async def list_calls(
    assistant_id: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """
    List call history with optional filters.
    
    Args:
        assistant_id: Filter by assistant (optional)
        limit: Max results (default 100)
    """
    params = {"limit": limit}
    if assistant_id:
        params["assistantId"] = assistant_id
    
    return await api_request("GET", "/call", params=params)


@mcp.tool()
async def get_transcript(call_id: str) -> dict[str, Any]:
    """
    Get the transcript for a completed call.
    
    Args:
        call_id: The call ID
        
    Returns:
        Full conversation transcript with timestamps.
    """
    call_data = await api_request("GET", f"/call/{call_id}")
    if "error" in call_data:
        return call_data
    
    # Transcript is embedded in call data
    return {
        "call_id": call_id,
        "transcript": call_data.get("transcript", []),
        "messages": call_data.get("messages", []),
        "summary": call_data.get("summary"),
    }


@mcp.tool()
async def list_phone_numbers() -> dict[str, Any]:
    """
    List all Vapi phone numbers.
    """
    return await api_request("GET", "/phone-number")


def main():
    """Run the MCP server."""
    import asyncio
    asyncio.run(mcp.run())


if __name__ == "__main__":
    main()
