"""task_executor.py — Execute a task via agent invoker + verification gate."""
import subprocess
from src.evo.agent_invoker import invoke_agent


def _verify(cmd: str, expected: str) -> str:
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    return proc.stdout


def execute_task(task_id: str, description: str, agent_id: str, verification_cmd: str, expected: str) -> dict:
    def attempt(frid: str) -> tuple[dict, str, bool]:
        r = invoke_agent(task_id, agent_id, description, flow_run_id=frid)
        if r.get("status") == "timeout":
            return r, "", False
        out = _verify(verification_cmd, expected)
        return r, out, expected in out

    result, verif_out, verified = attempt("standalone")
    attempts = 1

    if result.get("status") == "timeout":
        return {"task_id": task_id, "status": "failed", "agent_output": "",
                "verification_output": "", "verified": False, "attempts": attempts}

    if not verified:
        result, verif_out, verified = attempt("standalone-retry")
        attempts = 2

    return {
        "task_id": task_id,
        "status": "completed" if verified else "failed",
        "agent_output": str(result.get("output", result)),
        "verification_output": verif_out,
        "verified": verified,
        "attempts": attempts,
    }
