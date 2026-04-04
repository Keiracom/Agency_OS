"""task_consumer.py — Poll evo_task_queue, execute tasks, enforce budget guardrails."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.evo.task_executor import execute_task
from src.evo.auth_gate import request_authorisation
from src.evo.consumer_helpers import fetch_pending, claim_task, write_result, update_queue_status

try:  # api_tracker added in T4; stub until then
    from src.evo.api_tracker import check_budget
except ImportError:
    def check_budget(task_id: str, estimated: dict) -> tuple[bool, dict]:
        return False, {}


def run_consumer_once() -> int:
    task = fetch_pending()
    if not task:
        return 0

    task_id = task["id"]
    if not claim_task(task_id):
        return 0

    flow_run_id = task.get("flow_run_id", "")
    estimated_cost = task.get("estimated_cost") or {}

    result = execute_task(
        task_id=task_id,
        description=task.get("description", ""),
        agent_id=task.get("agent_id", ""),
        verification_cmd=task.get("verification_cmd", "echo ok"),
        expected=task.get("expected_output", "ok"),
    )

    over_budget, actual_cost = check_budget(task_id, estimated_cost)
    if over_budget:
        decision = request_authorisation(task_id, flow_run_id,
            reason="API usage exceeded 120% of estimate",
            estimated=estimated_cost, actual=actual_cost)
        if decision in ("stop", "timeout"):
            result["status"] = "failed"
    write_result(task_id, flow_run_id, task.get("agent_id", ""), result, actual_cost)
    update_queue_status(task_id, result["status"])
    return 1


if __name__ == "__main__":
    while True:
        run_consumer_once()
        time.sleep(10)
