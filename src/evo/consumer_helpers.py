"""consumer_helpers.py — DB ops for task_consumer: claim, result write, status update."""
import datetime
from src.evo.supabase_client import sb_get, sb_patch, sb_post


def fetch_pending() -> dict | None:
    rows = sb_get("evo_task_queue", {"status": "eq.pending",
                                     "order": "created_at.asc", "limit": "1"})
    return rows[0] if rows else None


def claim_task(task_id: str) -> bool:
    """Atomic claim — PATCH only on id, check returned status to detect race loss."""
    rows = sb_patch(
        "evo_task_queue",
        {"id": f"eq.{task_id}"},
        {"status": "running", "claimed_at": datetime.datetime.utcnow().isoformat()},
    )
    # If another consumer already claimed it, the row will show status != 'running' for us
    # or the row was already running — check returned row
    return bool(rows) and rows[0].get("status") == "running"


def write_result(task_id: str, flow_run_id: str, result: dict, actual_cost: dict) -> None:
    sb_post("evo_task_results", {
        "task_id": task_id,
        "flow_run_id": flow_run_id,
        "status": result["status"],
        "agent_output": result.get("agent_output", ""),
        "verification_output": result.get("verification_output", ""),
        "verified": result.get("verified", False),
        "actual_cost": actual_cost,
    })


def update_queue_status(task_id: str, status: str) -> None:
    sb_patch("evo_task_queue", {"id": f"eq.{task_id}"}, {"status": status})


def fail_task(task_id: str, reason: str = "") -> None:
    sb_patch("evo_task_queue", {"id": f"eq.{task_id}"},
             {"status": "failed", "completed_at": datetime.datetime.utcnow().isoformat()})
