"""
Task tracking system for spawned agents.

Provides functions to track, monitor, and retry spawned agent tasks.
Integrates with Supabase for persistence and Clawdbot sessions API for status checks.
"""

import subprocess
import json
import os
from datetime import datetime, timezone
from typing import Optional, Literal
from dataclasses import dataclass
from supabase import create_client, Client

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://jatzvazlbusedwsnqxzr.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")
CLAWDBOT_PATH = os.getenv("CLAWDBOT_PATH", "clawdbot")
STUCK_THRESHOLD_MS = 30 * 60 * 1000  # 30 minutes with no update = stuck

TaskStatus = Literal["running", "completed", "failed", "retry"]


@dataclass
class TaskInfo:
    """Information about a tracked task."""
    id: str
    label: str
    session_key: str
    task_description: str
    status: TaskStatus
    created_at: datetime
    completed_at: Optional[datetime]
    retry_count: int
    max_retries: int
    output_summary: Optional[str]
    parent_session_key: Optional[str]
    last_checked_at: Optional[datetime]


def get_supabase_client() -> Client:
    """Get Supabase client."""
    if not SUPABASE_KEY:
        raise ValueError("SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY required")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def track_task(
    label: str,
    session_key: str,
    description: str,
    max_retries: int = 2,
    parent_session_key: Optional[str] = None
) -> TaskInfo:
    """
    Track a newly spawned agent task.
    
    Call this immediately after spawning an agent.
    
    Args:
        label: Human-readable task label (e.g., "research-apollo")
        session_key: The spawned agent's session key
        description: What was requested
        max_retries: Maximum retry attempts (default: 2)
        parent_session_key: Session key of spawning agent (optional)
        
    Returns:
        TaskInfo for the tracked task
    """
    client = get_supabase_client()
    
    data = {
        "label": label,
        "session_key": session_key,
        "task_description": description,
        "status": "running",
        "max_retries": max_retries,
    }
    
    if parent_session_key:
        data["parent_session_key"] = parent_session_key
    
    result = client.table("elliot_tasks").insert(data).execute()
    
    if not result.data:
        raise RuntimeError(f"Failed to track task: {result}")
    
    row = result.data[0]
    return _row_to_task_info(row)


def get_session_status(session_key: str) -> dict:
    """
    Query Clawdbot sessions API for session status.
    
    Returns:
        dict with session info or empty dict if not found
    """
    try:
        result = subprocess.run(
            [CLAWDBOT_PATH, "sessions", "--json"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            return {"error": result.stderr.strip()}
        
        data = json.loads(result.stdout)
        sessions = data.get("sessions", [])
        
        for session in sessions:
            if session.get("key") == session_key:
                return session
        
        return {}  # Session not found (may have ended)
        
    except subprocess.TimeoutExpired:
        return {"error": "Timeout querying sessions"}
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {e}"}
    except Exception as e:
        return {"error": str(e)}


def check_task_status(session_key: str) -> dict:
    """
    Check the status of a tracked task.
    
    Queries both the database and Clawdbot sessions API.
    
    Args:
        session_key: The agent's session key
        
    Returns:
        dict with task_status, session_active, and details
    """
    client = get_supabase_client()
    
    # Get task from DB
    result = client.table("elliot_tasks").select("*").eq("session_key", session_key).execute()
    
    if not result.data:
        return {"error": "Task not found", "session_key": session_key}
    
    task = _row_to_task_info(result.data[0])
    
    # Get session status from Clawdbot
    session = get_session_status(session_key)
    
    # Update last_checked_at
    client.table("elliot_tasks").update({
        "last_checked_at": datetime.now(timezone.utc).isoformat()
    }).eq("session_key", session_key).execute()
    
    session_active = bool(session and "key" in session)
    age_ms = session.get("ageMs", 0) if session_active else None
    aborted = session.get("abortedLastRun", False) if session_active else None
    
    return {
        "task_status": task.status,
        "session_active": session_active,
        "session_age_ms": age_ms,
        "session_aborted": aborted,
        "retry_count": task.retry_count,
        "max_retries": task.max_retries,
        "task_id": task.id,
        "label": task.label,
    }


def mark_complete(session_key: str, summary: Optional[str] = None) -> TaskInfo:
    """
    Mark a task as completed.
    
    Args:
        session_key: The agent's session key
        summary: Optional summary of the output/result
        
    Returns:
        Updated TaskInfo
    """
    client = get_supabase_client()
    
    update_data = {
        "status": "completed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    
    if summary:
        update_data["output_summary"] = summary
    
    result = client.table("elliot_tasks").update(update_data).eq("session_key", session_key).execute()
    
    if not result.data:
        raise RuntimeError(f"Task not found: {session_key}")
    
    return _row_to_task_info(result.data[0])


def mark_failed(session_key: str, auto_retry: bool = True) -> dict:
    """
    Mark a task as failed. Auto-retries if under max_retries.
    
    Args:
        session_key: The agent's session key
        auto_retry: Whether to automatically retry (default: True)
        
    Returns:
        dict with status, retried flag, and new_session_key if retried
    """
    client = get_supabase_client()
    
    # Get current task
    result = client.table("elliot_tasks").select("*").eq("session_key", session_key).execute()
    
    if not result.data:
        return {"error": "Task not found", "session_key": session_key}
    
    task = _row_to_task_info(result.data[0])
    
    # Check if we should retry
    if auto_retry and task.retry_count < task.max_retries:
        # Mark as retry status and increment count
        client.table("elliot_tasks").update({
            "status": "retry",
            "retry_count": task.retry_count + 1,
        }).eq("session_key", session_key).execute()
        
        return {
            "status": "retry",
            "retried": True,
            "retry_count": task.retry_count + 1,
            "max_retries": task.max_retries,
            "task_description": task.task_description,
            "label": task.label,
            "message": f"Task marked for retry ({task.retry_count + 1}/{task.max_retries})"
        }
    else:
        # Mark as permanently failed
        client.table("elliot_tasks").update({
            "status": "failed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("session_key", session_key).execute()
        
        return {
            "status": "failed",
            "retried": False,
            "retry_count": task.retry_count,
            "max_retries": task.max_retries,
            "message": "Task permanently failed (max retries exceeded)"
        }


def get_pending_tasks() -> list[TaskInfo]:
    """Get all tasks with status 'running' or 'retry'."""
    client = get_supabase_client()
    
    result = client.table("elliot_tasks").select("*").in_("status", ["running", "retry"]).order("created_at").execute()
    
    return [_row_to_task_info(row) for row in result.data]


def get_stuck_tasks(threshold_ms: int = STUCK_THRESHOLD_MS) -> list[TaskInfo]:
    """
    Get tasks that appear stuck (running for too long with no session activity).
    
    Args:
        threshold_ms: Age threshold in milliseconds (default: 30 minutes)
        
    Returns:
        List of potentially stuck tasks
    """
    pending = get_pending_tasks()
    stuck = []
    
    for task in pending:
        session = get_session_status(task.session_key)
        
        # No session found or very old session = likely stuck
        if not session or "key" not in session:
            stuck.append(task)
        elif session.get("ageMs", 0) > threshold_ms:
            stuck.append(task)
        elif session.get("abortedLastRun", False):
            stuck.append(task)
    
    return stuck


def heartbeat_check() -> dict:
    """
    Heartbeat check: Review pending tasks, retry failures, alert on stuck.
    
    Call this periodically (e.g., every 5-10 minutes) to maintain task health.
    
    Returns:
        dict with summary of actions taken
    """
    results = {
        "pending_count": 0,
        "stuck_count": 0,
        "retried": [],
        "failed": [],
        "alerts": [],
    }
    
    pending = get_pending_tasks()
    results["pending_count"] = len(pending)
    
    for task in pending:
        status = check_task_status(task.session_key)
        
        # Session no longer active - check if completed or failed
        if not status.get("session_active"):
            # No session = likely completed or crashed
            # Mark as failed (will auto-retry if under max)
            fail_result = mark_failed(task.session_key)
            
            if fail_result.get("retried"):
                results["retried"].append({
                    "label": task.label,
                    "session_key": task.session_key,
                    "retry_count": fail_result["retry_count"],
                    "task_description": task.task_description,
                })
            else:
                results["failed"].append({
                    "label": task.label,
                    "session_key": task.session_key,
                    "task_description": task.task_description,
                })
                results["alerts"].append(
                    f"⚠️ Task '{task.label}' permanently failed after {task.max_retries} retries"
                )
        
        # Session still active but aborted
        elif status.get("session_aborted"):
            fail_result = mark_failed(task.session_key)
            
            if fail_result.get("retried"):
                results["retried"].append({
                    "label": task.label,
                    "session_key": task.session_key,
                    "retry_count": fail_result["retry_count"],
                })
            else:
                results["failed"].append({
                    "label": task.label,
                    "session_key": task.session_key,
                })
                results["alerts"].append(
                    f"⚠️ Task '{task.label}' aborted and max retries exceeded"
                )
    
    # Check for stuck tasks
    stuck = get_stuck_tasks()
    results["stuck_count"] = len(stuck)
    
    for task in stuck:
        if task.session_key not in [r["session_key"] for r in results["retried"] + results["failed"]]:
            results["alerts"].append(
                f"🕐 Task '{task.label}' appears stuck (session: {task.session_key[:20]}...)"
            )
    
    return results


def get_task_by_label(label: str) -> Optional[TaskInfo]:
    """Get the most recent task with a given label."""
    client = get_supabase_client()
    
    result = client.table("elliot_tasks").select("*").eq("label", label).order("created_at", desc=True).limit(1).execute()
    
    if result.data:
        return _row_to_task_info(result.data[0])
    return None


def get_tasks_summary() -> dict:
    """Get a summary of all tasks."""
    client = get_supabase_client()
    
    result = client.table("elliot_tasks").select("status").execute()
    
    summary = {"running": 0, "completed": 0, "failed": 0, "retry": 0, "total": 0}
    
    for row in result.data:
        status = row["status"]
        summary[status] = summary.get(status, 0) + 1
        summary["total"] += 1
    
    return summary


def _row_to_task_info(row: dict) -> TaskInfo:
    """Convert a database row to TaskInfo."""
    return TaskInfo(
        id=row["id"],
        label=row["label"],
        session_key=row["session_key"],
        task_description=row["task_description"],
        status=row["status"],
        created_at=_parse_datetime(row["created_at"]),
        completed_at=_parse_datetime(row.get("completed_at")),
        retry_count=row["retry_count"],
        max_retries=row["max_retries"],
        output_summary=row.get("output_summary"),
        parent_session_key=row.get("parent_session_key"),
        last_checked_at=_parse_datetime(row.get("last_checked_at")),
    )


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse ISO datetime string."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


# CLI interface for testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python task_tracker.py <command> [args]")
        print("Commands: track, check, complete, fail, pending, stuck, heartbeat, summary")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "track":
        if len(sys.argv) < 5:
            print("Usage: track <label> <session_key> <description>")
            sys.exit(1)
        task = track_task(sys.argv[2], sys.argv[3], sys.argv[4])
        print(f"Tracked: {task.id} - {task.label}")
    
    elif cmd == "check":
        if len(sys.argv) < 3:
            print("Usage: check <session_key>")
            sys.exit(1)
        result = check_task_status(sys.argv[2])
        print(json.dumps(result, indent=2))
    
    elif cmd == "complete":
        if len(sys.argv) < 3:
            print("Usage: complete <session_key> [summary]")
            sys.exit(1)
        summary = sys.argv[3] if len(sys.argv) > 3 else None
        task = mark_complete(sys.argv[2], summary)
        print(f"Completed: {task.label}")
    
    elif cmd == "fail":
        if len(sys.argv) < 3:
            print("Usage: fail <session_key>")
            sys.exit(1)
        result = mark_failed(sys.argv[2])
        print(json.dumps(result, indent=2))
    
    elif cmd == "pending":
        tasks = get_pending_tasks()
        for t in tasks:
            print(f"{t.status}: {t.label} ({t.session_key[:30]}...)")
    
    elif cmd == "stuck":
        tasks = get_stuck_tasks()
        for t in tasks:
            print(f"STUCK: {t.label} ({t.session_key[:30]}...)")
    
    elif cmd == "heartbeat":
        result = heartbeat_check()
        print(json.dumps(result, indent=2))
    
    elif cmd == "summary":
        result = get_tasks_summary()
        print(json.dumps(result, indent=2))
    
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
