"""
Resend MCP Server
Exposes Resend transactional email delivery.
"""
import os
import json
from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP("resend")

# API Configuration
RESEND_API_URL = os.getenv("RESEND_API_URL", "https://api.resend.com")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")


def get_headers() -> dict:
    return {
        "Authorization": f"Bearer {RESEND_API_KEY}",
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
            url=f"{RESEND_API_URL}{endpoint}",
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
async def send_email(
    from_address: str,
    to: str | list[str],
    subject: str,
    html: str | None = None,
    text: str | None = None,
    reply_to: str | None = None,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    tags: list[dict] | None = None,
) -> dict[str, Any]:
    """
    Send an email via Resend.
    
    Args:
        from_address: Sender email (must be verified domain)
        to: Recipient email(s)
        subject: Email subject
        html: HTML body content
        text: Plain text body (alternative to HTML)
        reply_to: Reply-to address
        cc: CC recipients
        bcc: BCC recipients
        tags: List of tag objects for tracking [{"name": "tag", "value": "val"}]
    """
    payload = {
        "from": from_address,
        "to": to if isinstance(to, list) else [to],
        "subject": subject,
    }
    if html:
        payload["html"] = html
    if text:
        payload["text"] = text
    if reply_to:
        payload["reply_to"] = reply_to
    if cc:
        payload["cc"] = cc
    if bcc:
        payload["bcc"] = bcc
    if tags:
        payload["tags"] = tags
    
    return await api_request("POST", "/emails", json_data=payload)


@mcp.tool()
async def list_emails() -> dict[str, Any]:
    """
    List sent emails from Resend.
    Note: Returns recent emails from the account.
    """
    return await api_request("GET", "/emails")


@mcp.tool()
async def get_email(email_id: str) -> dict[str, Any]:
    """
    Get details and status of a sent email.
    
    Args:
        email_id: The email ID returned from send_email
        
    Returns:
        Email status, delivery info, timestamps.
    """
    return await api_request("GET", f"/emails/{email_id}")


@mcp.tool()
async def list_domains() -> dict[str, Any]:
    """
    List all configured sending domains.
    
    Returns:
        Domain names, verification status, DNS records needed.
    """
    return await api_request("GET", "/domains")


@mcp.tool()
async def get_domain(domain_id: str) -> dict[str, Any]:
    """
    Get details of a specific domain.
    
    Args:
        domain_id: The domain ID
    """
    return await api_request("GET", f"/domains/{domain_id}")


@mcp.tool()
async def add_domain(name: str, region: str = "us-east-1") -> dict[str, Any]:
    """
    Add a new sending domain.
    
    Args:
        name: Domain name (e.g., mail.example.com)
        region: AWS region for delivery (default us-east-1)
    """
    payload = {"name": name, "region": region}
    return await api_request("POST", "/domains", json_data=payload)


@mcp.tool()
async def verify_domain(domain_id: str) -> dict[str, Any]:
    """
    Trigger verification check for a domain.
    
    Args:
        domain_id: The domain ID to verify
    """
    return await api_request("POST", f"/domains/{domain_id}/verify")


@mcp.tool()
async def delete_domain(domain_id: str) -> dict[str, Any]:
    """
    Delete a sending domain.
    
    Args:
        domain_id: The domain ID to delete
    """
    return await api_request("DELETE", f"/domains/{domain_id}")


@mcp.tool()
async def list_api_keys() -> dict[str, Any]:
    """
    List API keys for the account.
    """
    return await api_request("GET", "/api-keys")


@mcp.tool()
async def send_batch(emails: list[dict]) -> dict[str, Any]:
    """
    Send multiple emails in a batch.
    
    Args:
        emails: List of email objects, each with:
            - from: Sender address
            - to: Recipient(s)
            - subject: Subject line
            - html or text: Content
    """
    return await api_request("POST", "/emails/batch", json_data=emails)


def main():
    """Run the MCP server."""
    import asyncio
    asyncio.run(mcp.run())


if __name__ == "__main__":
    main()
