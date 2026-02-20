#!/usr/bin/env python3

import asyncio
import os
from typing import Any, Dict, Optional, Union
import httpx
from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# Initialize the MCP server
app = Server("telegram-bot")

# Get bot token from environment variable
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
DEFAULT_CHAT_ID = -5151519377

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


async def make_telegram_request(method: str, **kwargs) -> Dict[str, Any]:
    """Make HTTP request to Telegram Bot API"""
    url = f"{BASE_URL}/{method}"
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=kwargs)
        response.raise_for_status()
        result = response.json()
        
        if not result.get("ok"):
            raise Exception(f"Telegram API error: {result.get('description', 'Unknown error')}")
            
        return result


@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools"""
    return [
        types.Tool(
            name="send_message",
            description="Send a message to a Telegram chat",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The message text to send"
                    },
                    "chat_id": {
                        "type": ["integer", "string"],
                        "description": "The chat ID to send the message to. Can be a chat ID number or username."
                    }
                },
                "required": ["text", "chat_id"]
            }
        ),
        types.Tool(
            name="get_messages",
            description="Get recent messages from a Telegram chat",
            inputSchema={
                "type": "object",
                "properties": {
                    "chat_id": {
                        "type": ["integer", "string"],
                        "description": "The chat ID to get messages from"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of recent messages to retrieve (default: 10)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100
                    }
                },
                "required": ["chat_id"]
            }
        ),
        types.Tool(
            name="get_chat_id",
            description="Get the default configured chat ID",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


@app.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent]:
    """Handle tool calls"""
    
    if name == "send_message":
        text = arguments.get("text")
        chat_id = arguments.get("chat_id")
        
        if not text or chat_id is None:
            raise ValueError("Both 'text' and 'chat_id' are required")
        
        try:
            result = await make_telegram_request(
                "sendMessage",
                chat_id=chat_id,
                text=text,
                parse_mode="HTML"
            )
            
            message_id = result["result"]["message_id"]
            return [
                types.TextContent(
                    type="text",
                    text=f"Message sent successfully! Message ID: {message_id}"
                )
            ]
            
        except Exception as e:
            return [
                types.TextContent(
                    type="text",
                    text=f"Error sending message: {str(e)}"
                )
            ]
    
    elif name == "get_messages":
        chat_id = arguments.get("chat_id")
        limit = arguments.get("limit", 10)
        
        if chat_id is None:
            raise ValueError("'chat_id' is required")
        
        try:
            # Get updates to find recent messages
            result = await make_telegram_request(
                "getUpdates",
                limit=limit,
                allowed_updates=["message"]
            )
            
            messages = []
            for update in result["result"]:
                if "message" in update:
                    msg = update["message"]
                    if msg.get("chat", {}).get("id") == int(chat_id):
                        messages.append({
                            "message_id": msg["message_id"],
                            "from": msg.get("from", {}).get("first_name", "Unknown"),
                            "text": msg.get("text", "[No text content]"),
                            "date": msg["date"]
                        })
            
            # Sort by date (newest first) and limit
            messages.sort(key=lambda x: x["date"], reverse=True)
            messages = messages[:limit]
            
            if not messages:
                return [
                    types.TextContent(
                        type="text",
                        text=f"No recent messages found in chat {chat_id}"
                    )
                ]
            
            output = f"Recent messages from chat {chat_id}:\n\n"
            for msg in messages:
                output += f"• [{msg['message_id']}] {msg['from']}: {msg['text']}\n"
            
            return [
                types.TextContent(
                    type="text",
                    text=output
                )
            ]
            
        except Exception as e:
            return [
                types.TextContent(
                    type="text",
                    text=f"Error getting messages: {str(e)}"
                )
            ]
    
    elif name == "get_chat_id":
        return [
            types.TextContent(
                type="text",
                text=f"Default chat ID: {DEFAULT_CHAT_ID}"
            )
        ]
    
    else:
        raise ValueError(f"Unknown tool: {name}")


async def main():
    # Run the server using stdio transport
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="telegram-bot",
                server_version="0.1.0",
                capabilities=app.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None,
                )
            )
        )


if __name__ == "__main__":
    asyncio.run(main())