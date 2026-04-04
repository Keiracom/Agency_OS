"""agent_invoker.py — Write task to evo_task_queue, poll evo_task_results."""
import time
import httpx
from dotenv import load_dotenv
import os

load_dotenv("/home/elliotbot/.config/agency-os/.env")

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}


def invoke_agent(task_id: str, agent_id: str, description: str, flow_run_id: str) -> dict:
    payload = {
        "task_id": task_id,
        "agent_id": agent_id,
        "description": description,
        "flow_run_id": flow_run_id,
        "status": "pending",
    }
    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{SUPABASE_URL}/rest/v1/evo_task_queue",
            headers=HEADERS,
            json=payload,
        )
        resp.raise_for_status()

    deadline = time.time() + 300
    while time.time() < deadline:
        time.sleep(5)
        with httpx.Client(timeout=30) as client:
            r = client.get(
                f"{SUPABASE_URL}/rest/v1/evo_task_results",
                headers=HEADERS,
                params={"task_id": f"eq.{task_id}", "flow_run_id": f"eq.{flow_run_id}"},
            )
            r.raise_for_status()
            rows = r.json()
        if rows:
            return rows[0]

    return {"status": "timeout", "task_id": task_id}
