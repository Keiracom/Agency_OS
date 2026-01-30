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
RELEVANCE_THRESHOLD = 0.6
TELEGRAM_TARGET = os.getenv("TELEGRAM_NOTIFY_TARGET", "dave")


class ActionType(str, Enum):
    """Action types that can be routed from knowledge."""
    EVALUATE_TOOL = "evaluate_tool"
    RESEARCH = "research"
    ABSORB = "absorb"
    COMPETITIVE_INTEL = "competitive_intel"
    AUDIT = "audit"
    ANALYZE = "analyze"


# Map knowledge categories to action types
CATEGORY_TO_ACTION = {
    "tool_discovery": ActionType.EVALUATE_TOOL,
    "tech_trend": ActionType.RESEARCH,
    "pattern_recognition": ActionType.ABSORB,
    "best_practice": ActionType.ABSORB,
    "technique": ActionType.ABSORB,
    "competitor_intel": ActionType.COMPETITIVE_INTEL,
    "market_intel": ActionType.COMPETITIVE_INTEL,
    "audit": ActionType.AUDIT,
    "analysis": ActionType.ANALYZE,
}

# Action type descriptions for sign-off messages (legacy, used as fallback)
ACTION_DESCRIPTIONS = {
    ActionType.EVALUATE_TOOL: "Spawn agent to assess tool fit with our stack",
    ActionType.RESEARCH: "Spawn agent to deep-dive into this trend",
    ActionType.ABSORB: "Extract pattern/technique and add to knowledge base",
    ActionType.COMPETITIVE_INTEL: "Analyze competitor and add to competitive tracking",
    ActionType.AUDIT: "Spawn agent to check if we follow this pattern",
    ActionType.ANALYZE: "Spawn agent to compare against our approach",
}

# Emojis for each action type
ACTION_EMOJIS = {
    ActionType.EVALUATE_TOOL: "📦",
    ActionType.RESEARCH: "🔬",
    ActionType.ABSORB: "🧠",
    ActionType.COMPETITIVE_INTEL: "🎯",
    ActionType.AUDIT: "📋",
    ActionType.ANALYZE: "📊",
}

# Headers for each action type
ACTION_HEADERS = {
    ActionType.EVALUATE_TOOL: "TOOL EVALUATION",
    ActionType.RESEARCH: "RESEARCH REQUEST",
    ActionType.ABSORB: "KNOWLEDGE TO ABSORB",
    ActionType.COMPETITIVE_INTEL: "COMPETITOR INTELLIGENCE",
    ActionType.AUDIT: "CODE AUDIT",
    ActionType.ANALYZE: "ANALYSIS REQUEST",
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
    
    ActionType.ABSORB: """
Extract and absorb this knowledge into our systems:

**Topic:** {title}
**Source:** {source}

**Context:**
{content}

Your task:
1. Understand the core pattern/technique/insight
2. Identify how it applies to Elliot or Agency OS
3. Extract actionable takeaways
4. Determine where to store (MEMORY.md patterns, SOUL.md behaviors, or knowledge/)
5. Add the distilled knowledge to the appropriate location

Output confirmation of what was absorbed and where.
""",
    
    ActionType.COMPETITIVE_INTEL: """
Analyze this competitive intelligence:

**Subject:** {title}
**Source:** {source}

**Context:**
{content}

Your task:
1. Research the competitor/product mentioned
2. Understand what they announced or changed
3. Assess impact on Agency OS competitive position
4. Identify threats and opportunities
5. Recommend strategic response if needed

Output your analysis to MEMORY.md competitive tracking section.
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


def _extract_metadata_field(content: dict, *keys: str, default: str = "") -> str:
    """Extract a field from content dict, trying multiple key names."""
    for key in keys:
        if key in content and content[key]:
            return str(content[key])
    return default


def _format_engagement(content: dict) -> str:
    """Format engagement metrics from content metadata."""
    parts = []
    
    stars = _extract_metadata_field(content, "stars", "github_stars", "stargazers_count")
    if stars:
        parts.append(f"⭐ {stars}")
    
    points = _extract_metadata_field(content, "points", "score", "upvotes")
    if points:
        parts.append(f"{points} points")
    
    comments = _extract_metadata_field(content, "comments", "comment_count", "num_comments")
    if comments:
        parts.append(f"{comments} comments")
    
    return " | ".join(parts) if parts else ""


def _truncate_text(text: str, max_chars: int = 200) -> str:
    """Truncate text to max chars, adding ellipsis if needed."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 3].rsplit(" ", 1)[0] + "..."


def generate_description(knowledge: KnowledgeItem, action_type: ActionType) -> str:
    """
    Generate a detailed, plain-English description for sign-off.
    
    Creates human-readable descriptions that explain:
    - What the item is
    - Why it matters to Dave/Agency OS
    - What happens if approved
    
    Args:
        knowledge: The knowledge item
        action_type: The determined action type
        
    Returns:
        Rich description string formatted for Telegram
    """
    content = knowledge.content or {}
    emoji = ACTION_EMOJIS.get(action_type, "📋")
    header = ACTION_HEADERS.get(action_type, "ACTION REQUEST")
    
    # Extract common metadata
    engagement = _format_engagement(content)
    source_display = knowledge.source or "Unknown"
    
    # Build the description based on action type
    if action_type == ActionType.EVALUATE_TOOL:
        return _generate_tool_description(knowledge, content, emoji, header, engagement, source_display)
    elif action_type == ActionType.RESEARCH:
        return _generate_research_description(knowledge, content, emoji, header, engagement, source_display)
    elif action_type == ActionType.ABSORB:
        return _generate_absorb_description(knowledge, content, emoji, header, source_display)
    elif action_type == ActionType.COMPETITIVE_INTEL:
        return _generate_competitive_description(knowledge, content, emoji, header, source_display)
    else:
        # Fallback for AUDIT, ANALYZE, etc.
        return _generate_generic_description(knowledge, content, emoji, header, source_display)


def _generate_tool_description(
    knowledge: KnowledgeItem, 
    content: dict, 
    emoji: str, 
    header: str, 
    engagement: str,
    source_display: str
) -> str:
    """Generate description for tool evaluation."""
    # Extract tool-specific info
    tool_name = knowledge.title or "Unknown Tool"
    description = _extract_metadata_field(content, "description", "summary", "about")
    
    # Build what it does section
    what_it_does = knowledge.summary or description
    if not what_it_does:
        what_it_does = f"A tool discovered via {source_display}. Needs evaluation to understand capabilities."
    what_it_does = _truncate_text(what_it_does, 250)
    
    # Build why it matters - translate to business value
    why_matters = _extract_metadata_field(content, "relevance_reason", "why_relevant")
    if not why_matters:
        # Generate generic but useful why
        why_matters = "Could streamline development, reduce costs, or add new capabilities to our stack."
    
    # Build the stats line
    stats_line = f"Source: {source_display}"
    if engagement:
        stats_line = f"{engagement} | {stats_line}"
    
    return f"""{emoji} **{header}**

**{tool_name}**
{stats_line}

**WHAT IT DOES:**
{what_it_does}

**WHY IT MATTERS:**
{why_matters}

**IF APPROVED:**
I'll evaluate integration complexity, pricing, and fit with our stack. Recommend adopt/skip with reasoning."""


def _generate_research_description(
    knowledge: KnowledgeItem,
    content: dict,
    emoji: str,
    header: str,
    engagement: str,
    source_display: str
) -> str:
    """Generate description for research request."""
    topic = knowledge.title or "Research Topic"
    
    # What it's about
    about = knowledge.summary
    if not about:
        about = _extract_metadata_field(content, "description", "text", "content")
    if not about:
        about = f"A topic that surfaced from {source_display} worth deeper investigation."
    about = _truncate_text(about, 250)
    
    # Why research this
    why_research = _extract_metadata_field(content, "relevance_reason", "why_relevant")
    if not why_research:
        why_research = "Understanding this could inform our technical decisions or reveal opportunities."
    
    # Build stats line
    stats_line = f"Source: {source_display}"
    if engagement:
        stats_line = f"{stats_line} | {engagement}"
    
    return f"""{emoji} **{header}**

**{topic}**
{stats_line}

**WHAT IT'S ABOUT:**
{about}

**WHY RESEARCH THIS:**
{why_research}

**IF APPROVED:**
I'll deep dive, extract key insights, and add findings to knowledge base."""


def _generate_absorb_description(
    knowledge: KnowledgeItem,
    content: dict,
    emoji: str,
    header: str,
    source_display: str
) -> str:
    """Generate description for knowledge absorption."""
    title = knowledge.title or "Knowledge Item"
    
    # The insight - what it teaches
    insight = knowledge.summary
    if not insight:
        insight = _extract_metadata_field(content, "description", "content", "text")
    if not insight:
        insight = "A pattern or technique that could enhance our systems."
    insight = _truncate_text(insight, 250)
    
    # How it helps
    how_helps = _extract_metadata_field(content, "relevance_reason", "why_relevant", "application")
    if not how_helps:
        how_helps = "Could improve Elliot's capabilities or Agency OS architecture."
    
    return f"""{emoji} **{header}**

**{title}**
Source: {source_display}

**THE INSIGHT:**
{insight}

**HOW IT HELPS:**
{how_helps}

**IF APPROVED:**
I'll extract the pattern/technique and add to MEMORY.md or SOUL.md."""


def _generate_competitive_description(
    knowledge: KnowledgeItem,
    content: dict,
    emoji: str,
    header: str,
    source_display: str
) -> str:
    """Generate description for competitive intelligence."""
    subject = knowledge.title or "Competitor Update"
    
    # What happened
    what_happened = knowledge.summary
    if not what_happened:
        what_happened = _extract_metadata_field(content, "description", "news", "update")
    if not what_happened:
        what_happened = f"Competitive movement detected via {source_display}."
    what_happened = _truncate_text(what_happened, 250)
    
    # Why it matters to competitive position
    why_matters = _extract_metadata_field(content, "relevance_reason", "impact", "why_relevant")
    if not why_matters:
        why_matters = "May affect our market position or reveal strategic opportunities."
    
    return f"""{emoji} **{header}**

**{subject}**
Source: {source_display}

**WHAT HAPPENED:**
{what_happened}

**WHY IT MATTERS:**
{why_matters}

**IF APPROVED:**
I'll analyze and add to competitive tracking."""


def _generate_generic_description(
    knowledge: KnowledgeItem,
    content: dict,
    emoji: str,
    header: str,
    source_display: str
) -> str:
    """Generate generic description for unmapped action types."""
    title = knowledge.title or "Action Item"
    
    summary = knowledge.summary or "Item requires review and action."
    summary = _truncate_text(summary, 250)
    
    return f"""{emoji} **{header}**

**{title}**
Source: {source_display}

**SUMMARY:**
{summary}

**IF APPROVED:**
I'll analyze this item and take appropriate action."""


def generate_summary(knowledge: KnowledgeItem, action_type: ActionType) -> str:
    """
    Generate a detailed summary for the sign-off request.
    
    Uses generate_description() to create rich, human-readable descriptions
    that help Dave understand what he's approving.
    
    Args:
        knowledge: The knowledge item
        action_type: The determined action type
        
    Returns:
        Rich description text formatted for Telegram
    """
    return generate_description(knowledge, action_type)


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
    
    # Map to notification ActionType
    notify_action_map = {
        ActionType.EVALUATE_TOOL: NotifyActionType.EVALUATE_TOOL,
        ActionType.RESEARCH: NotifyActionType.RESEARCH,
        ActionType.ABSORB: NotifyActionType.ABSORB,
        ActionType.COMPETITIVE_INTEL: NotifyActionType.COMPETITIVE_INTEL,
        ActionType.AUDIT: NotifyActionType.AUDIT,
        ActionType.ANALYZE: NotifyActionType.ANALYZE,
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
