"""
Telegram notification system for knowledge sign-off queue.

Uses Clawdbot message tool to send notifications with inline approve/reject buttons.
"""

import subprocess
import json
from typing import Optional
from dataclasses import dataclass
from enum import Enum


class ActionType(Enum):
    EVALUATE_TOOL = "evaluate_tool"
    BUILD_POC = "build_poc"
    RESEARCH = "research"
    AUDIT = "audit"
    ANALYZE = "analyze"


@dataclass
class SignoffRequest:
    """Represents a sign-off queue item."""
    id: str
    knowledge_id: str
    action_type: ActionType
    title: str
    summary: str


def get_action_emoji(action_type: ActionType) -> str:
    """Get emoji for action type."""
    return {
        ActionType.EVALUATE_TOOL: "🔧",
        ActionType.BUILD_POC: "🏗️",
        ActionType.RESEARCH: "🔍",
        ActionType.AUDIT: "📋",
        ActionType.ANALYZE: "📊",
    }.get(action_type, "📋")


def get_action_label(action_type: ActionType) -> str:
    """Get human-readable label for action type."""
    return {
        ActionType.EVALUATE_TOOL: "Tool Evaluation",
        ActionType.BUILD_POC: "Build PoC",
        ActionType.RESEARCH: "Research",
        ActionType.AUDIT: "Code Audit",
        ActionType.ANALYZE: "Competitive Analysis",
    }.get(action_type, "Action")


def format_signoff_message(request: SignoffRequest) -> str:
    """Format the notification message for Telegram."""
    emoji = get_action_emoji(request.action_type)
    label = get_action_label(request.action_type)
    
    return f"""{emoji} **Sign-off Required: {label}**

**{request.title}**

{request.summary}

---
`ID: {request.id[:8]}`"""


def send_signoff_notification(
    request: SignoffRequest,
    target: str = "dave",
    clawdbot_path: str = "clawdbot"
) -> dict:
    """
    Send a Telegram notification with inline approve/reject buttons.
    
    Args:
        request: The SignoffRequest to notify about
        target: Telegram target (user/chat ID or name)
        clawdbot_path: Path to clawdbot CLI
        
    Returns:
        dict with success status and message_id if successful
    """
    message = format_signoff_message(request)
    
    # Build inline keyboard with approve/reject buttons
    # Callback data format: signoff:{action}:{id}
    inline_keyboard = [
        [
            {"text": "✅ Approve", "callback_data": f"signoff:approve:{request.id}"},
            {"text": "❌ Reject", "callback_data": f"signoff:reject:{request.id}"}
        ]
    ]
    
    # Use clawdbot message tool
    cmd = [
        clawdbot_path, "message", "send",
        "--target", target,
        "--message", message,
        "--inline-keyboard", json.dumps(inline_keyboard)
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return {"success": True, "output": result.stdout.strip()}
        else:
            return {"success": False, "error": result.stderr.strip()}
            
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Timeout sending notification"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def send_batch_signoff_notifications(
    requests: list[SignoffRequest],
    target: str = "dave"
) -> list[dict]:
    """
    Send multiple sign-off notifications.
    
    Args:
        requests: List of SignoffRequest objects
        target: Telegram target
        
    Returns:
        List of result dicts for each notification
    """
    results = []
    for request in requests:
        result = send_signoff_notification(request, target)
        result["request_id"] = request.id
        results.append(result)
    return results


# Example usage and testing
if __name__ == "__main__":
    # Example request
    test_request = SignoffRequest(
        id="550e8400-e29b-41d4-a716-446655440000",
        knowledge_id="660e8400-e29b-41d4-a716-446655440001",
        action_type=ActionType.EVALUATE_TOOL,
        title="Apify Web Scraper",
        summary="New scraping tool discovered. Offers 1M free API calls/month. Could replace current BeautifulSoup setup for complex JS-rendered pages."
    )
    
    print("Formatted message:")
    print(format_signoff_message(test_request))
    print("\n---")
    print("Inline keyboard:", json.dumps([
        [
            {"text": "✅ Approve", "callback_data": f"signoff:approve:{test_request.id}"},
            {"text": "❌ Reject", "callback_data": f"signoff:reject:{test_request.id}"}
        ]
    ], indent=2))
