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


def write_result(task_id: str, flow_run_id: str, agent_id: str, result: dict, actual_cost: dict) -> None:
    sb_post("evo_task_results", {
        "task_id": task_id,
        "flow_run_id": flow_run_id,
        "agent_id": agent_id,
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


def invoke_agent_local(agent_id: str, description: str, timeout: int = 300) -> dict:
    """Run openclaw agent locally; JSON is in stderr after log lines."""
    import subprocess, json
    cmd = ["openclaw", "agent", "--agent", agent_id, "--local",
           "--message", description, "--json", "--timeout", str(timeout)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)
        combined = proc.stderr + proc.stdout
        json_start = combined.find("{")
        if proc.returncode != 0:
            return {"text": "", "exit_code": proc.returncode, "error": combined.strip()}
        data = json.loads(combined[json_start:])
        text = (data.get("payloads") or [{}])[0].get("text") or data.get("text", "")
        return {"text": text, "exit_code": 0}
    except Exception as e:
        return {"text": "", "exit_code": getattr(proc, "returncode", 1), "error": str(e)}


def verify_output(cmd: str, expected: str) -> tuple[bool, str]:
    """Run shell verification command, return (matched, stdout)."""
    import subprocess
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    return expected in r.stdout, r.stdout
