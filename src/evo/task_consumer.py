"""task_consumer.py — Poll queue, execute, verify, write result."""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.evo.api_tracker import ApiTracker
from src.evo.auth_gate import request_authorisation
from src.evo.consumer_helpers import (
    claim_task,
    fail_task,
    fetch_pending,
    invoke_agent_local,
    update_queue_status,
    verify_output,
    write_result,
)
from src.evo.tg_notify import tg_send


def run_consumer_once() -> int:
    task = fetch_pending()
    if not task:
        return 0
    task_id = task["id"]
    if not claim_task(task_id):
        return 0
    try:
        agent_id, description = task.get("agent_id", ""), task.get("description", "")
        flow_run_id = task.get("flow_run_id", "")
        vcmd, expected = task.get("verification_cmd", "echo ok"), task.get("expected_output", "ok")
        estimated_cost = task.get("estimated_cost") or {}
        tracker = ApiTracker()
        tracker.track_call("api.anthropic.com")
        agent_result = invoke_agent_local(agent_id, description)
        verified, verify_out = verify_output(vcmd, expected)
        if not verified:
            tracker.track_call("api.anthropic.com")
            agent_result = invoke_agent_local(agent_id, description)
            verified, verify_out = verify_output(vcmd, expected)
        status = "completed" if verified else "failed"
        write_result(
            task_id,
            flow_run_id,
            agent_id,
            {
                "status": status,
                "agent_output": agent_result.get("text", ""),
                "verification_output": verify_out,
                "verified": verified,
            },
            tracker.get_counts(),
        )
        update_queue_status(task_id, status)
        if not tracker.check_budget(estimated_cost)["within_budget"]:
            request_authorisation(
                task_id,
                flow_run_id,
                reason="API >120% estimate",
                estimated=estimated_cost,
                actual=tracker.get_counts(),
            )
    except Exception as e:
        fail_task(task_id, str(e))
        tg_send(f"[EVO consumer] task {task_id} failed: {e}")
    return 1


if __name__ == "__main__":
    _consecutive_failures = 0
    _last_error = ""
    _CIRCUIT_BREAKER_LIMIT = 3
    while True:
        try:
            result = run_consumer_once()
            if result == 1:
                _consecutive_failures = 0
                _last_error = ""
        except Exception as e:
            _consecutive_failures += 1
            _last_error = str(e)
            if _consecutive_failures >= _CIRCUIT_BREAKER_LIMIT:
                tg_send(
                    f"🔴 Consumer paused: {_CIRCUIT_BREAKER_LIMIT} consecutive failures.\n"
                    f"Error: {_last_error}\nManual restart required."
                )
                break
        time.sleep(10)
