"""
Elliot Application Tracker
==========================
Enforces the "Added X, Applied to Y" contract.
Tracks knowledge application and generates session reports.
"""

import os
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass

from supabase import create_client, Client


# ============================================
# Configuration
# ============================================

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")


@dataclass
class KnowledgeItem:
    """Represents a knowledge item from the database."""
    id: str
    category: str
    content: str
    summary: Optional[str]
    source_type: Optional[str]
    learned_at: datetime
    decay_score: float
    days_old: int = 0
    applied: bool = False
    applied_context: Optional[str] = None


@dataclass
class SessionStats:
    """Session learning statistics."""
    total_knowledge: int
    applied_count: int
    unapplied_count: int
    recently_added: int
    recently_applied: int
    avg_decay_score: float
    at_risk_count: int


# ============================================
# Supabase Client
# ============================================

def get_supabase() -> Client:
    """Get authenticated Supabase client."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def _safe_get_supabase() -> Optional[Client]:
    """Get Supabase client or None if not configured."""
    try:
        return get_supabase()
    except ValueError:
        return None


# ============================================
# Core Functions
# ============================================

def get_unapplied_knowledge(limit: int = 5, min_decay_score: float = 0.3) -> list[KnowledgeItem]:
    """
    Fetch knowledge items that haven't been applied yet.
    
    Args:
        limit: Maximum number of items to return
        min_decay_score: Minimum decay score to include (default 0.3)
    
    Returns:
        List of KnowledgeItem objects to consider applying this session
    """
    supabase = _safe_get_supabase()
    if not supabase:
        print("[application_tracker] Supabase not configured, returning empty list")
        return []
    
    try:
        # Use the database function for efficient querying
        result = supabase.rpc(
            'get_unapplied_knowledge',
            {'max_items': limit, 'min_decay_score': min_decay_score}
        ).execute()
        
        items = []
        for row in result.data or []:
            items.append(KnowledgeItem(
                id=row['id'],
                category=row['category'],
                content=row['content'],
                summary=row.get('summary'),
                source_type=row.get('source_type'),
                learned_at=datetime.fromisoformat(row['learned_at'].replace('Z', '+00:00')),
                decay_score=row['relevance_decay'],
                days_old=row.get('days_old', 0)
            ))
        
        return items
    
    except Exception as e:
        print(f"[application_tracker] Error fetching unapplied knowledge: {e}")
        return []


def apply_knowledge(knowledge_id: str, context: str) -> Optional[KnowledgeItem]:
    """
    Mark knowledge as applied with context of how it was used.
    
    Args:
        knowledge_id: UUID of the knowledge item
        context: Description of how this knowledge was applied
    
    Returns:
        Updated KnowledgeItem or None if failed
    """
    supabase = _safe_get_supabase()
    if not supabase:
        print("[application_tracker] Supabase not configured")
        return None
    
    try:
        result = supabase.rpc(
            'mark_knowledge_applied',
            {'knowledge_id': knowledge_id, 'context': context}
        ).execute()
        
        if result.data and len(result.data) > 0:
            row = result.data[0]
            return KnowledgeItem(
                id=row['id'],
                category='',  # Not returned by function
                content=row['content'],
                summary=None,
                source_type=None,
                learned_at=datetime.now(timezone.utc),  # Not returned
                decay_score=row['relevance_decay'],
                applied=True,
                applied_context=row['applied_context']
            )
        return None
    
    except Exception as e:
        print(f"[application_tracker] Error applying knowledge: {e}")
        return None


def get_session_learning_report(hours_back: int = 24) -> dict:
    """
    Generate a summary of learning activity for the session.
    
    Args:
        hours_back: Hours to look back for "recent" activity
    
    Returns:
        Dict with stats, recent additions, and applied knowledge
    """
    supabase = _safe_get_supabase()
    if not supabase:
        return {
            "stats": None,
            "recently_added": [],
            "recently_applied": [],
            "pending_application": [],
            "error": "Supabase not configured"
        }
    
    try:
        # Get stats
        stats_result = supabase.rpc(
            'get_session_learning_stats',
            {'hours_back': hours_back}
        ).execute()
        
        stats = None
        if stats_result.data and len(stats_result.data) > 0:
            row = stats_result.data[0]
            stats = SessionStats(
                total_knowledge=row['total_knowledge'],
                applied_count=row['applied_count'],
                unapplied_count=row['unapplied_count'],
                recently_added=row['recently_added'],
                recently_applied=row['recently_applied'],
                avg_decay_score=row['avg_decay_score'],
                at_risk_count=row['at_risk_count']
            )
        
        # Get recently added
        from_time = datetime.now(timezone.utc).isoformat()
        recently_added = supabase.table('elliot_knowledge') \
            .select('id, category, content, summary, source_type, learned_at') \
            .is_('deleted_at', 'null') \
            .gte('learned_at', f"now() - interval '{hours_back} hours'") \
            .order('learned_at', desc=True) \
            .limit(10) \
            .execute()
        
        # Get recently applied
        recently_applied = supabase.table('elliot_knowledge') \
            .select('id, content, summary, applied_at, applied_context') \
            .is_('deleted_at', 'null') \
            .eq('applied', True) \
            .gte('applied_at', f"now() - interval '{hours_back} hours'") \
            .order('applied_at', desc=True) \
            .limit(10) \
            .execute()
        
        # Get pending application (unapplied, sorted by decay)
        pending = get_unapplied_knowledge(limit=10)
        
        return {
            "stats": stats,
            "recently_added": recently_added.data or [],
            "recently_applied": recently_applied.data or [],
            "pending_application": pending,
            "error": None
        }
    
    except Exception as e:
        return {
            "stats": None,
            "recently_added": [],
            "recently_applied": [],
            "pending_application": [],
            "error": str(e)
        }


def prune_stale_knowledge(min_score: float = 0.3) -> dict:
    """
    Delete low-score knowledge that was never applied.
    
    Args:
        min_score: Minimum decay score threshold (default 0.3)
    
    Returns:
        Dict with pruned_count and pruned_ids
    """
    supabase = _safe_get_supabase()
    if not supabase:
        return {"pruned_count": 0, "pruned_ids": [], "error": "Supabase not configured"}
    
    try:
        result = supabase.rpc(
            'prune_stale_knowledge',
            {'min_score': min_score}
        ).execute()
        
        if result.data and len(result.data) > 0:
            row = result.data[0]
            return {
                "pruned_count": row['pruned_count'],
                "pruned_ids": row['pruned_ids'] or [],
                "error": None
            }
        
        return {"pruned_count": 0, "pruned_ids": [], "error": None}
    
    except Exception as e:
        return {"pruned_count": 0, "pruned_ids": [], "error": str(e)}


def decay_all_knowledge() -> dict:
    """
    Apply decay to all unapplied knowledge (daily job).
    
    Returns:
        Dict with decayed_count, min_score_after, max_age_days
    """
    supabase = _safe_get_supabase()
    if not supabase:
        return {"decayed_count": 0, "error": "Supabase not configured"}
    
    try:
        result = supabase.rpc('decay_unused_knowledge').execute()
        
        if result.data and len(result.data) > 0:
            row = result.data[0]
            return {
                "decayed_count": row['decayed_count'],
                "min_score_after": row['min_score_after'],
                "max_age_days": row['max_age_days'],
                "error": None
            }
        
        return {"decayed_count": 0, "error": None}
    
    except Exception as e:
        return {"decayed_count": 0, "error": str(e)}


# ============================================
# Report Formatting
# ============================================

def format_session_report(report: dict) -> str:
    """
    Format the session learning report as markdown.
    
    Args:
        report: Output from get_session_learning_report()
    
    Returns:
        Formatted markdown string
    """
    lines = ["## Session Learning Report", ""]
    
    # Stats summary
    stats = report.get("stats")
    if stats:
        lines.extend([
            "### Summary",
            f"- **Total Knowledge:** {stats.total_knowledge}",
            f"- **Applied:** {stats.applied_count} | **Pending:** {stats.unapplied_count}",
            f"- **Recently Added (24h):** {stats.recently_added}",
            f"- **Recently Applied (24h):** {stats.recently_applied}",
            f"- **Avg Decay Score:** {stats.avg_decay_score:.2f}",
            f"- **At Risk (decay < 0.5):** {stats.at_risk_count}",
            ""
        ])
    
    # New knowledge added
    recently_added = report.get("recently_added", [])
    if recently_added:
        lines.extend(["### New Knowledge Added", ""])
        for item in recently_added[:5]:
            source = item.get('source_type', 'unknown')
            summary = item.get('summary') or item.get('content', '')[:60]
            category = item.get('category', '')
            lines.append(f"- [{source}] {summary} - *{category}*")
        lines.append("")
    
    # Applied this session
    recently_applied = report.get("recently_applied", [])
    if recently_applied:
        lines.extend(["### Knowledge Applied This Session", ""])
        for item in recently_applied[:5]:
            summary = item.get('summary') or item.get('content', '')[:40]
            context = item.get('applied_context', 'No context provided')
            lines.append(f"- {summary} → **Applied to:** {context}")
        lines.append("")
    
    # Pending application
    pending = report.get("pending_application", [])
    if pending:
        lines.extend(["### Pending Application (will decay if not used)", ""])
        for item in pending[:5]:
            summary = item.summary or item.content[:50]
            lines.append(f"- {summary} - decay: {item.decay_score:.1f} ({item.days_old}d old)")
        lines.append("")
    
    # Error handling
    if report.get("error"):
        lines.extend(["### ⚠️ Error", f"```{report['error']}```", ""])
    
    return "\n".join(lines)


# ============================================
# CLI / Testing
# ============================================

if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    
    # Load environment
    load_dotenv(os.path.expanduser("~/.config/agency-os/.env"))
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == "report":
            report = get_session_learning_report()
            print(format_session_report(report))
        
        elif cmd == "unapplied":
            items = get_unapplied_knowledge(limit=10)
            for item in items:
                print(f"[{item.decay_score:.1f}] {item.id[:8]}... | {item.content[:60]}")
        
        elif cmd == "apply" and len(sys.argv) >= 4:
            knowledge_id = sys.argv[2]
            context = " ".join(sys.argv[3:])
            result = apply_knowledge(knowledge_id, context)
            if result:
                print(f"✓ Applied: {result.content[:50]}...")
            else:
                print("✗ Failed to apply knowledge")
        
        elif cmd == "decay":
            result = decay_all_knowledge()
            print(f"Decayed {result['decayed_count']} items")
        
        elif cmd == "prune":
            result = prune_stale_knowledge()
            print(f"Pruned {result['pruned_count']} items")
        
        else:
            print("Usage: python application_tracker.py [report|unapplied|apply <id> <context>|decay|prune]")
    else:
        # Default: show report
        report = get_session_learning_report()
        print(format_session_report(report))
