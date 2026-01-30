"""
Knowledge Action Engine
=======================
The brain that turns knowledge into action.

Watches for high-value knowledge items, routes them to appropriate actions,
creates sign-off requests, and spawns agents on approval.
"""

import os
import json
import subprocess
import uuid
from datetime import datetime, timezone
from typing import Optional, Literal
from dataclasses import dataclass, asdict
from enum import Enum

from supabase import create_client, Client

# Import from our existing infrastructure
from infrastructure.signoff_notify import (
    SignoffRequest as NotifySignoffRequest,
    ActionType as NotifyActionType,
    send_signoff_notification,
    get_action_emoji,
)
from infrastructure.task_tracker import (
    track_task,
    mark_complete,
    mark_failed,
    get_supabase_client,
)

# ============================================
# Configuration
# ============================================

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://jatzvazlbusedwsnqxzr.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")
CLAWDBOT_PATH = os.getenv("CLAWDBOT_PATH", "clawdbot")
RELEVANCE_THRESHOLD = 0.8
TELEGRAM_TARGET = os.getenv("TELEGRAM_NOTIFY_TARGET", "dave")


class ActionType(str, Enum):
    """Action types that can be routed from knowledge."""
    EVALUATE_TOOL = "evaluate_tool"
    RESEARCH = "research"
    AUDIT = "audit"
    ANALYZE = "analyze"


# Map knowledge categories to action types
CATEGORY_TO_ACTION = {
    "tool_discovery": ActionType.EVALUATE_TOOL,
    "tech_trend": ActionType.RESEARCH,
    "pattern_recognition": ActionType.AUDIT,
    "competitor_intel": ActionType.ANALYZE,
}

# Action type descriptions for sign-off messages
ACTION_DESCRIPTIONS = {
    ActionType.EVALUATE_TOOL: "Spawn agent to assess tool fit with our stack",
    ActionType.RESEARCH: "Spawn agent to deep-dive into this trend",
    ActionType.AUDIT: "Spawn agent to check if we follow this pattern",
    ActionType.ANALYZE: "Spawn agent to compare against our approach",
}

# Agent prompts for each action type
AGENT_PROMPTS = {
    ActionType.EVALUATE_TOOL: """
Evaluate this tool for our Agency OS stack:

**Tool:** {title}
**Source:** {source}

**Context:**
{content}

Your task:
1. Research the tool (official docs, GitHub, pricing)
2. Assess fit with our stack (FastAPI, Next.js, Supabase, Prefect, Railway)
3. Identify specific use cases for Agency OS
4. Compare to any current tools we use for similar purposes
5. Provide recommendation: Adopt / Monitor / Skip

Output a structured evaluation to MEMORY.md with your findings.
""",
    
    ActionType.RESEARCH: """
Deep-dive research on this tech trend:

**Topic:** {title}
**Source:** {source}

**Context:**
{content}

Your task:
1. Research current state and key players
2. Identify implications for Agency OS
3. Find practical applications we could implement
4. Note any risks or considerations
5. Recommend concrete next steps

Output your findings to MEMORY.md with actionable insights.
""",
    
    ActionType.AUDIT: """
Audit our codebase against this pattern/practice:

**Pattern:** {title}
**Source:** {source}

**Context:**
{content}

Your task:
1. Understand the pattern/practice described
2. Search our codebase for relevant implementations
3. Assess whether we follow this pattern
4. Identify gaps or improvements needed
5. Create specific action items if changes are needed

Output your audit findings to MEMORY.md with specific file references.
""",
    
    ActionType.ANALYZE: """
Competitive analysis based on this intelligence:

**Topic:** {title}
**Source:** {source}

**Context:**
{content}

Your task:
1. Research the competitor/approach mentioned
2. Compare their approach to ours
3. Identify any advantages they have
4. Find opportunities we could exploit
5. Recommend strategic adjustments

Output your analysis to MEMORY.md with competitive insights.
""",
}


@dataclass
class KnowledgeItem:
    """Represents a knowledge item from elliot_knowledge table."""
    id: str
    title: str  # Maps from 'content' column
    summary: str
    content: dict  # Maps from 'metadata' column
    category: str
    source: str  # Maps from 'source_type' column
    source_url: Optional[str]
    relevance_score: float
    applied: bool
    learned_at: str


@dataclass
class SignoffQueueItem:
    """Represents an item in elliot_signoff_queue."""
    id: str
    knowledge_id: str
    action_type: str
    title: str
    summary: str
    status: str
    created_at: str


# ============================================
# Database Operations
# ============================================

def get_client() -> Client:
    """Get Supabase client."""
    if not SUPABASE_KEY:
        raise ValueError("SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY required")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def get_high_value_knowledge(
    threshold: float = RELEVANCE_THRESHOLD,
    limit: int = 10
) -> list[KnowledgeItem]:
    """
    Query elliot_knowledge for high-value unapplied items.
    
    Args:
        threshold: Minimum relevance_score (default: 0.8)
        limit: Maximum items to return
        
    Returns:
        List of KnowledgeItem sorted by relevance_score desc, then learned_at desc
    """
    client = get_client()
    
    result = client.table("elliot_knowledge").select("*").filter(
        "relevance_score", "gte", threshold
    ).filter(
        "applied", "eq", False
    ).order(
        "relevance_score", desc=True
    ).order(
        "learned_at", desc=True
    ).limit(limit).execute()
    
    return [_row_to_knowledge(row) for row in result.data]


def get_knowledge_by_id(knowledge_id: str) -> Optional[KnowledgeItem]:
    """Get a specific knowledge item by ID."""
    client = get_client()
    
    result = client.table("elliot_knowledge").select("*").eq("id", knowledge_id).execute()
    
    if result.data:
        return _row_to_knowledge(result.data[0])
    return None


def mark_knowledge_applied(knowledge_id: str) -> bool:
    """Mark a knowledge item as applied."""
    client = get_client()
    
    result = client.table("elliot_knowledge").update({
        "applied": True,
        "applied_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", knowledge_id).execute()
    
    return len(result.data) > 0


def create_signoff_queue_item(
    knowledge_id: str,
    action_type: ActionType,
    title: str,
    summary: str,
) -> SignoffQueueItem:
    """
    Insert a new item into elliot_signoff_queue.
    
    Args:
        knowledge_id: ID of the knowledge item
        action_type: Type of action to take
        title: Title for the sign-off request
        summary: Summary of why this matters and what we'd do
        
    Returns:
        The created SignoffQueueItem
    """
    client = get_client()
    
    signoff_id = str(uuid.uuid4())
    
    data = {
        "id": signoff_id,
        "knowledge_id": knowledge_id,
        "action_type": action_type.value,
        "title": title,
        "summary": summary,
        "status": "pending",
    }
    
    result = client.table("elliot_signoff_queue").insert(data).execute()
    
    if not result.data:
        raise RuntimeError(f"Failed to create signoff queue item: {result}")
    
    return _row_to_signoff(result.data[0])


def get_signoff_by_id(signoff_id: str) -> Optional[SignoffQueueItem]:
    """Get a signoff queue item by ID."""
    client = get_client()
    
    result = client.table("elliot_signoff_queue").select("*").eq("id", signoff_id).execute()
    
    if result.data:
        return _row_to_signoff(result.data[0])
    return None


def update_signoff_status(signoff_id: str, status: str) -> bool:
    """Update the status of a signoff queue item."""
    client = get_client()
    
    update_data = {
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    
    result = client.table("elliot_signoff_queue").update(update_data).eq("id", signoff_id).execute()
    
    return len(result.data) > 0


def get_pending_signoffs() -> list[SignoffQueueItem]:
    """Get all pending signoff requests."""
    client = get_client()
    
    result = client.table("elliot_signoff_queue").select("*").eq(
        "status", "pending"
    ).order("created_at", desc=True).execute()
    
    return [_row_to_signoff(row) for row in result.data]


# ============================================
# Core Engine Functions
# ============================================

def route_to_action(knowledge: KnowledgeItem) -> Optional[ActionType]:
    """
    Determine the action type based on knowledge category.
    
    Args:
        knowledge: The knowledge item to route
        
    Returns:
        ActionType or None if category not mapped
    """
    return CATEGORY_TO_ACTION.get(knowledge.category)


def generate_summary(knowledge: KnowledgeItem, action_type: ActionType) -> str:
    """
    Generate a summary for the sign-off request.
    
    Args:
        knowledge: The knowledge item
        action_type: The determined action type
        
    Returns:
        Summary text explaining why this matters and what we'd do
    """
    action_desc = ACTION_DESCRIPTIONS.get(action_type, "Take action on this knowledge")
    
    # Extract key details from content
    content = knowledge.content or {}
    source_detail = f"Source: {knowledge.source}"
    if knowledge.source_url:
        source_detail += f" ({knowledge.source_url})"
    
    summary_parts = [
        f"**Relevance Score:** {knowledge.relevance_score:.2f}",
        "",
        knowledge.summary or "No summary available.",
        "",
        source_detail,
        "",
        f"**Proposed Action:** {action_desc}",
    ]
    
    return "\n".join(summary_parts)


def create_signoff_request(
    knowledge: KnowledgeItem,
    action_type: ActionType
) -> dict:
    """
    Create a sign-off request for a knowledge item.
    
    Args:
        knowledge: The knowledge item
        action_type: The action type to perform
        
    Returns:
        dict with signoff_id, notification_result
    """
    # Generate summary
    summary = generate_summary(knowledge, action_type)
    
    # Create queue item
    signoff = create_signoff_queue_item(
        knowledge_id=knowledge.id,
        action_type=action_type,
        title=knowledge.title,
        summary=summary,
    )
    
    # Map to notification ActionType (extend if needed)
    notify_action_map = {
        ActionType.EVALUATE_TOOL: NotifyActionType.EVALUATE_TOOL,
        ActionType.RESEARCH: NotifyActionType.RESEARCH,
        # Fallback for unmapped types
        ActionType.AUDIT: NotifyActionType.RESEARCH,
        ActionType.ANALYZE: NotifyActionType.RESEARCH,
    }
    
    # Send Telegram notification
    notify_request = NotifySignoffRequest(
        id=signoff.id,
        knowledge_id=knowledge.id,
        action_type=notify_action_map.get(action_type, NotifyActionType.RESEARCH),
        title=knowledge.title,
        summary=summary,
    )
    
    notification_result = send_signoff_notification(notify_request, target=TELEGRAM_TARGET)
    
    return {
        "signoff_id": signoff.id,
        "knowledge_id": knowledge.id,
        "action_type": action_type.value,
        "notification_result": notification_result,
    }


def spawn_action_agent(
    knowledge: KnowledgeItem,
    action_type: ActionType,
    signoff_id: str
) -> dict:
    """
    Spawn an agent to execute the action.
    
    Args:
        knowledge: The knowledge item to act on
        action_type: The type of action
        signoff_id: The signoff request ID for tracking
        
    Returns:
        dict with session_key, task_id, success status
    """
    # Get the prompt template
    prompt_template = AGENT_PROMPTS.get(action_type, AGENT_PROMPTS[ActionType.RESEARCH])
    
    # Format the prompt
    prompt = prompt_template.format(
        title=knowledge.title,
        source=knowledge.source,
        content=knowledge.summary or json.dumps(knowledge.content, indent=2),
    )
    
    # Generate label for tracking
    label = f"{action_type.value}-{knowledge.id[:8]}"
    
    # Spawn agent via clawdbot
    try:
        result = subprocess.run(
            [CLAWDBOT_PATH, "spawn", "-l", label, prompt],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": result.stderr.strip() or "Failed to spawn agent",
            }
        
        # Parse session key from output (format varies by clawdbot version)
        output = result.stdout.strip()
        session_key = output  # Assume output is session key
        
        # Track the task
        task_info = track_task(
            label=label,
            session_key=session_key,
            description=f"{action_type.value}: {knowledge.title}",
            max_retries=2,
        )
        
        # Update signoff status
        update_signoff_status(signoff_id, "executing")
        
        return {
            "success": True,
            "session_key": session_key,
            "task_id": task_info.id,
            "label": label,
        }
        
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Timeout spawning agent"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def handle_approval(signoff_id: str) -> dict:
    """
    Handle approval of a sign-off request.
    
    Spawns the appropriate agent and updates tracking.
    
    Args:
        signoff_id: The signoff request ID
        
    Returns:
        dict with spawn result and status
    """
    # Get signoff details
    signoff = get_signoff_by_id(signoff_id)
    if not signoff:
        return {"success": False, "error": f"Signoff not found: {signoff_id}"}
    
    if signoff.status != "pending":
        return {"success": False, "error": f"Signoff already processed: {signoff.status}"}
    
    # Get knowledge item
    knowledge = get_knowledge_by_id(signoff.knowledge_id)
    if not knowledge:
        return {"success": False, "error": f"Knowledge not found: {signoff.knowledge_id}"}
    
    # Parse action type
    try:
        action_type = ActionType(signoff.action_type)
    except ValueError:
        return {"success": False, "error": f"Invalid action type: {signoff.action_type}"}
    
    # Update status to approved
    update_signoff_status(signoff_id, "approved")
    
    # Spawn the agent
    spawn_result = spawn_action_agent(knowledge, action_type, signoff_id)
    
    if spawn_result.get("success"):
        return {
            "success": True,
            "action": "agent_spawned",
            "signoff_id": signoff_id,
            "knowledge_id": knowledge.id,
            "action_type": action_type.value,
            **spawn_result,
        }
    else:
        # Mark as failed if spawn failed
        update_signoff_status(signoff_id, "failed")
        return {
            "success": False,
            "action": "spawn_failed",
            "signoff_id": signoff_id,
            **spawn_result,
        }


def handle_rejection(signoff_id: str, reason: Optional[str] = None) -> dict:
    """
    Handle rejection of a sign-off request.
    
    Args:
        signoff_id: The signoff request ID
        reason: Optional rejection reason
        
    Returns:
        dict with status
    """
    # Get signoff details
    signoff = get_signoff_by_id(signoff_id)
    if not signoff:
        return {"success": False, "error": f"Signoff not found: {signoff_id}"}
    
    if signoff.status != "pending":
        return {"success": False, "error": f"Signoff already processed: {signoff.status}"}
    
    # Update status to rejected
    update_signoff_status(signoff_id, "rejected")
    
    return {
        "success": True,
        "action": "rejected",
        "signoff_id": signoff_id,
        "knowledge_id": signoff.knowledge_id,
        "reason": reason,
    }


def complete_action(signoff_id: str, session_key: str, summary: Optional[str] = None) -> dict:
    """
    Mark an action as complete after agent finishes.
    
    Args:
        signoff_id: The signoff request ID
        session_key: The agent's session key
        summary: Optional summary of results
        
    Returns:
        dict with status
    """
    # Get signoff details
    signoff = get_signoff_by_id(signoff_id)
    if not signoff:
        return {"success": False, "error": f"Signoff not found: {signoff_id}"}
    
    # Mark task complete
    try:
        mark_complete(session_key, summary)
    except Exception as e:
        # Task might already be marked or not found
        pass
    
    # Mark knowledge as applied
    mark_knowledge_applied(signoff.knowledge_id)
    
    # Update signoff status
    update_signoff_status(signoff_id, "completed")
    
    return {
        "success": True,
        "action": "completed",
        "signoff_id": signoff_id,
        "knowledge_id": signoff.knowledge_id,
    }


def process_new_knowledge() -> dict:
    """
    Main function: Process new high-value knowledge items.
    
    1. Query for high-value knowledge (score >= 0.8, not applied)
    2. Route each to an action type
    3. Create sign-off requests
    4. Send Telegram notifications
    
    Returns:
        dict with processing results
    """
    results = {
        "processed": 0,
        "signoffs_created": [],
        "skipped": [],
        "errors": [],
    }
    
    # Get high-value knowledge
    knowledge_items = get_high_value_knowledge()
    
    for knowledge in knowledge_items:
        # Check if already has pending signoff
        client = get_client()
        existing = client.table("elliot_signoff_queue").select("id").eq(
            "knowledge_id", knowledge.id
        ).in_("status", ["pending", "approved", "executing"]).execute()
        
        if existing.data:
            results["skipped"].append({
                "knowledge_id": knowledge.id,
                "title": knowledge.title,
                "reason": "Already has pending signoff",
            })
            continue
        
        # Route to action type
        action_type = route_to_action(knowledge)
        
        if not action_type:
            results["skipped"].append({
                "knowledge_id": knowledge.id,
                "title": knowledge.title,
                "reason": f"Unknown category: {knowledge.category}",
            })
            continue
        
        # Create signoff request
        try:
            signoff_result = create_signoff_request(knowledge, action_type)
            results["processed"] += 1
            results["signoffs_created"].append({
                "knowledge_id": knowledge.id,
                "title": knowledge.title,
                "action_type": action_type.value,
                "signoff_id": signoff_result["signoff_id"],
                "notification_sent": signoff_result["notification_result"].get("success", False),
            })
        except Exception as e:
            results["errors"].append({
                "knowledge_id": knowledge.id,
                "title": knowledge.title,
                "error": str(e),
            })
    
    return results


# ============================================
# Callback Handler (for Telegram button responses)
# ============================================

def handle_callback(callback_data: str) -> dict:
    """
    Handle Telegram callback from approve/reject buttons.
    
    Callback format: signoff:{action}:{id}
    
    Args:
        callback_data: The callback_data string from Telegram
        
    Returns:
        dict with result
    """
    parts = callback_data.split(":")
    
    if len(parts) != 3 or parts[0] != "signoff":
        return {"success": False, "error": f"Invalid callback format: {callback_data}"}
    
    action = parts[1]
    signoff_id = parts[2]
    
    if action == "approve":
        return handle_approval(signoff_id)
    elif action == "reject":
        return handle_rejection(signoff_id)
    else:
        return {"success": False, "error": f"Unknown action: {action}"}


# ============================================
# Helper Functions
# ============================================

def _row_to_knowledge(row: dict) -> KnowledgeItem:
    """Convert database row to KnowledgeItem."""
    return KnowledgeItem(
        id=row["id"],
        title=row.get("content", ""),  # 'content' column holds the title
        summary=row.get("summary", ""),
        content=row.get("metadata", {}),  # 'metadata' holds additional data
        category=row.get("category", ""),
        source=row.get("source_type", ""),  # 'source_type' column
        source_url=row.get("source_url"),
        relevance_score=row.get("relevance_score", 0.0),
        applied=row.get("applied", False),
        learned_at=row.get("learned_at", ""),
    )


def _row_to_signoff(row: dict) -> SignoffQueueItem:
    """Convert database row to SignoffQueueItem."""
    return SignoffQueueItem(
        id=row["id"],
        knowledge_id=row["knowledge_id"],
        action_type=row["action_type"],
        title=row.get("title", ""),
        summary=row.get("summary", ""),
        status=row.get("status", "pending"),
        created_at=row.get("created_at", ""),
    )


# ============================================
# CLI Interface
# ============================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python action_engine.py <command> [args]")
        print("Commands:")
        print("  process         - Process new high-value knowledge")
        print("  pending         - List pending signoff requests")
        print("  approve <id>    - Approve a signoff request")
        print("  reject <id>     - Reject a signoff request")
        print("  callback <data> - Handle callback (signoff:action:id)")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "process":
        result = process_new_knowledge()
        print(json.dumps(result, indent=2))
    
    elif cmd == "pending":
        signoffs = get_pending_signoffs()
        for s in signoffs:
            print(f"[{s.status}] {s.id[:8]}: {s.title} ({s.action_type})")
    
    elif cmd == "approve":
        if len(sys.argv) < 3:
            print("Usage: approve <signoff_id>")
            sys.exit(1)
        result = handle_approval(sys.argv[2])
        print(json.dumps(result, indent=2))
    
    elif cmd == "reject":
        if len(sys.argv) < 3:
            print("Usage: reject <signoff_id>")
            sys.exit(1)
        result = handle_rejection(sys.argv[2])
        print(json.dumps(result, indent=2))
    
    elif cmd == "callback":
        if len(sys.argv) < 3:
            print("Usage: callback <callback_data>")
            sys.exit(1)
        result = handle_callback(sys.argv[2])
        print(json.dumps(result, indent=2))
    
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
