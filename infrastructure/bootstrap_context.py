"""
Elliot Bootstrap Context
========================
Retrieves relevant knowledge and state for session initialization.

This module combines:
1. Recent knowledge from Supabase (elliot_knowledge)
2. Session state from Redis (current task, todos, last session)
3. Optional semantic search for context-relevant knowledge

Usage:
    from infrastructure.bootstrap_context import get_bootstrap_context
    
    context = get_bootstrap_context()
    # or with semantic search:
    context = get_bootstrap_context(query="current project priorities")
"""

import os
from datetime import datetime, timezone
from typing import Optional

from supabase import create_client, Client

# Import sibling module
# Handle relative imports for both package and direct execution
try:
    from infrastructure.state.state_manager import ElliotStateManager, get_bootstrap_state as get_redis_state
except ImportError:
    from state.state_manager import ElliotStateManager, get_bootstrap_state as get_redis_state

# ============================================
# Configuration
# ============================================

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

DEFAULT_MAX_KNOWLEDGE = 20
DEFAULT_MAX_AGE_HOURS = 168  # 1 week


def get_supabase() -> Client:
    """Get authenticated Supabase client."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# ============================================
# Knowledge Retrieval
# ============================================

def get_recent_knowledge(
    max_items: int = DEFAULT_MAX_KNOWLEDGE,
    max_age_hours: int = DEFAULT_MAX_AGE_HOURS,
    categories: Optional[list[str]] = None,
    min_confidence: float = 0.6
) -> list[dict]:
    """
    Retrieve recent high-confidence knowledge from Supabase.
    
    Args:
        max_items: Maximum number of items to return
        max_age_hours: Only include knowledge from the last N hours
        categories: Filter by specific categories (None = all)
        min_confidence: Minimum confidence score threshold
    
    Returns:
        List of knowledge items with category, content, summary, source info
    """
    supabase = get_supabase()
    
    # Use the stored function if available, otherwise direct query
    try:
        # Try using the SQL function
        result = supabase.rpc(
            "get_bootstrap_context",
            {"max_items": max_items, "max_age_hours": max_age_hours}
        ).execute()
        
        if result.data:
            return result.data
    except Exception:
        pass  # Fall back to direct query
    
    # Direct query fallback
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    
    query = supabase.table("elliot_knowledge").select(
        "category, content, summary, source_type, confidence_score, learned_at, source_url"
    ).is_("deleted_at", "null").gte(
        "learned_at", cutoff.isoformat()
    ).gte(
        "confidence_score", min_confidence
    ).order(
        "confidence_score", desc=True
    ).order(
        "learned_at", desc=True
    ).limit(max_items)
    
    if categories:
        query = query.in_("category", categories)
    
    result = query.execute()
    return result.data or []


def search_knowledge_semantic(
    query_text: str,
    max_results: int = 10,
    min_similarity: float = 0.7,
    categories: Optional[list[str]] = None
) -> list[dict]:
    """
    Search knowledge base using semantic similarity.
    
    Requires:
    - OpenAI API key for embeddings
    - Populated embedding column in elliot_knowledge
    
    Args:
        query_text: Text to search for
        max_results: Maximum number of results
        min_similarity: Minimum cosine similarity threshold
        categories: Filter by specific categories
    
    Returns:
        List of matching knowledge items with similarity scores
    """
    # Check if we have OpenAI for embeddings
    openai_key = os.environ.get("OPENAI_API_KEY")
    if not openai_key:
        # Fall back to keyword search
        return search_knowledge_keyword(query_text, max_results, categories)
    
    try:
        import openai
        
        # Generate embedding for query
        client = openai.OpenAI(api_key=openai_key)
        response = client.embeddings.create(
            model="text-embedding-ada-002",
            input=query_text
        )
        query_embedding = response.data[0].embedding
        
        # Search using Supabase vector function
        supabase = get_supabase()
        result = supabase.rpc(
            "search_knowledge_by_embedding",
            {
                "query_embedding": query_embedding,
                "match_threshold": min_similarity,
                "match_count": max_results,
                "filter_categories": categories
            }
        ).execute()
        
        return result.data or []
        
    except Exception as e:
        print(f"Semantic search failed: {e}, falling back to keyword")
        return search_knowledge_keyword(query_text, max_results, categories)


def search_knowledge_keyword(
    query_text: str,
    max_results: int = 10,
    categories: Optional[list[str]] = None
) -> list[dict]:
    """
    Simple keyword-based knowledge search (fallback when no embeddings).
    
    Args:
        query_text: Text to search for
        max_results: Maximum number of results
        categories: Filter by specific categories
    
    Returns:
        List of matching knowledge items
    """
    supabase = get_supabase()
    
    # Use Postgres full-text search
    query = supabase.table("elliot_knowledge").select(
        "category, content, summary, source_type, confidence_score, learned_at, source_url"
    ).is_("deleted_at", "null").or_(
        f"content.ilike.%{query_text}%,summary.ilike.%{query_text}%"
    ).order(
        "confidence_score", desc=True
    ).limit(max_results)
    
    if categories:
        query = query.in_("category", categories)
    
    result = query.execute()
    return result.data or []


# ============================================
# Combined Bootstrap Context
# ============================================

def get_bootstrap_context(
    query: Optional[str] = None,
    max_knowledge: int = DEFAULT_MAX_KNOWLEDGE,
    max_age_hours: int = DEFAULT_MAX_AGE_HOURS,
    include_redis: bool = True,
    categories: Optional[list[str]] = None
) -> dict:
    """
    Get complete bootstrap context for session initialization.
    
    This is the main entry point for session startup.
    
    Args:
        query: Optional search query for semantic knowledge retrieval
        max_knowledge: Maximum knowledge items to include
        max_age_hours: Maximum age of knowledge to include
        include_redis: Whether to include Redis session state
        categories: Filter knowledge by specific categories
    
    Returns:
        Complete context dict with:
        - knowledge: Recent/relevant knowledge items
        - session_state: Current task, todos, last session (if include_redis)
        - stats: Summary statistics
        - retrieved_at: Timestamp
    """
    context = {
        "knowledge": [],
        "session_state": None,
        "stats": {},
        "retrieved_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Get knowledge (semantic search if query provided, otherwise recent)
    try:
        if query:
            context["knowledge"] = search_knowledge_semantic(
                query, max_knowledge, categories=categories
            )
            context["stats"]["knowledge_source"] = "semantic_search"
            context["stats"]["search_query"] = query
        else:
            context["knowledge"] = get_recent_knowledge(
                max_knowledge, max_age_hours, categories=categories
            )
            context["stats"]["knowledge_source"] = "recent"
    except Exception as e:
        context["stats"]["knowledge_error"] = str(e)
    
    context["stats"]["knowledge_count"] = len(context["knowledge"])
    
    # Get Redis session state
    if include_redis:
        try:
            context["session_state"] = get_redis_state()
        except Exception as e:
            context["stats"]["redis_error"] = str(e)
    
    return context


def format_context_for_injection(context: dict, max_chars: int = 4000) -> str:
    """
    Format bootstrap context as a string for prompt injection.
    
    Args:
        context: Context dict from get_bootstrap_context()
        max_chars: Maximum characters in output
    
    Returns:
        Formatted string suitable for system prompt injection
    """
    lines = ["## Session Bootstrap Context", ""]
    
    # Session state
    if context.get("session_state"):
        state = context["session_state"]
        
        # Current task
        current = state.get("current_task", {})
        if current.get("task"):
            lines.append(f"**Active Task:** {current['task']}")
            if current.get("started_at"):
                lines.append(f"  Started: {current['started_at']}")
            lines.append("")
        
        # Last session
        last = state.get("last_session", {})
        if last.get("summary"):
            lines.append(f"**Previous Session:** {last['summary']}")
            if last.get("unfinished_work"):
                lines.append("  Unfinished:")
                for work in last["unfinished_work"][:3]:
                    lines.append(f"  - {work}")
            lines.append("")
        
        # Pending todos
        todos = state.get("pending_todos", [])
        if todos:
            lines.append(f"**Pending Todos ({len(todos)}):**")
            for todo in sorted(todos, key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x.get("priority", "medium"), 1))[:5]:
                priority = todo.get("priority", "medium")
                marker = "🔴" if priority == "high" else "🟡" if priority == "medium" else "⚪"
                lines.append(f"  {marker} [{todo.get('id', '?')}] {todo.get('task', 'Unknown')}")
            lines.append("")
    
    # Knowledge
    knowledge = context.get("knowledge", [])
    if knowledge:
        lines.append(f"**Recent Knowledge ({len(knowledge)} items):**")
        
        # Group by category
        by_category = {}
        for item in knowledge:
            cat = item.get("category", "general")
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(item)
        
        for category, items in by_category.items():
            lines.append(f"\n  *{category.replace('_', ' ').title()}*")
            for item in items[:3]:  # Max 3 per category
                summary = item.get("summary") or item.get("content", "")[:100]
                lines.append(f"  - {summary}")
    
    # Join and truncate
    result = "\n".join(lines)
    if len(result) > max_chars:
        result = result[:max_chars - 20] + "\n\n[truncated...]"
    
    return result


# ============================================
# CLI
# ============================================

if __name__ == "__main__":
    import json
    import sys
    
    # Load env
    from dotenv import load_dotenv
    load_dotenv(os.path.expanduser("~/.config/agency-os/.env"))
    
    query = sys.argv[1] if len(sys.argv) > 1 else None
    
    print("Fetching bootstrap context...")
    context = get_bootstrap_context(query=query)
    
    print("\n" + "=" * 50)
    print("RAW CONTEXT:")
    print("=" * 50)
    print(json.dumps(context, indent=2, default=str))
    
    print("\n" + "=" * 50)
    print("FORMATTED FOR INJECTION:")
    print("=" * 50)
    print(format_context_for_injection(context))
