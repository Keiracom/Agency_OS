"""flow_generator.py — Dynamic Prefect flow from task_graph JSON."""

from datetime import UTC, datetime

import prefect.runtime.flow_run as _fr
from prefect import flow

from src.evo.flow_builder import wire_tasks
from src.prefect_utils.completion_hook import on_completion_hook
from src.prefect_utils.hooks import on_failure_hook

_captured_run_id: str = "unknown"


def _slug(objective: str) -> str:
    return objective.lower().replace(" ", "-")[:30]


def _flow_name(objective: str) -> str:
    ts = datetime.now(UTC).strftime("%Y%m%d")
    return f"evo-{_slug(objective)}-{ts}"


def generate_and_run_flow(task_graph: dict) -> str:
    """Parse task_graph, build a named Prefect flow, run it, return flow_run_id."""
    global _captured_run_id
    objective = task_graph["objective"]
    tasks = task_graph["tasks"]
    name = _flow_name(objective)

    @flow(
        name=name,
        on_completion=[on_completion_hook],
        on_failure=[on_failure_hook],
    )
    def dynamic_flow():
        global _captured_run_id
        _captured_run_id = str(_fr.id)
        return wire_tasks(tasks)

    dynamic_flow()
    return _captured_run_id
