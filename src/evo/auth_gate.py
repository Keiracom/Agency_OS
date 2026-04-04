"""auth_gate.py — Write evo_auth_requests row, notify Telegram, poll for response."""
import time
import httpx
from src.evo.tg_notify import tg_send
from src.evo.supabase_client import sb_post, sb_get

POLL_INTERVAL = 15
TIMEOUT_SECS = 1800  # 30 minutes


def request_authorisation(
    task_id: str, flow_run_id: str, reason: str, estimated: dict, actual: dict
) -> str:
    payload = {
        "task_id": task_id, "flow_run_id": flow_run_id, "reason": reason,
        "request_type": "budget_exceeded", "estimated": estimated,
        "actual": actual, "status": "pending",
    }
    row = sb_post("evo_auth_requests", payload)
    row_id = row[0]["id"]

    tg_send(
        f"⚠️ Budget exceeded\nTask: {task_id}\nReason: {reason}\n"
        f"Estimated: {estimated}\nActual: {actual}\nReply GO or STOP"
    )

    deadline = time.time() + TIMEOUT_SECS
    while time.time() < deadline:
        time.sleep(POLL_INTERVAL)
        rows = sb_get("evo_auth_requests", {"id": f"eq.{row_id}", "select": "status"})
        if rows and rows[0]["status"] != "pending":
            return "go" if rows[0]["status"] == "approved" else "stop"

    return "timeout"
