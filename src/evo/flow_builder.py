"""flow_builder.py — Task wrapping and dependency wiring helpers."""
from prefect import task
from src.evo.task_executor import execute_task


def make_prefect_task(t: dict):
    """Wrap a task graph entry as a Prefect @task(retries=1) callable."""
    tid, desc, agent = t["id"], t["description"], t["agent"]
    vcmd, vexp = t["verification"]["command"], t["verification"]["expected"]

    @task(retries=1, task_run_name=tid)
    def _task_fn():
        return execute_task(tid, desc, agent, vcmd, vexp)

    _task_fn.__name__ = f"task_{tid}"
    return _task_fn


def wire_tasks(tasks: list[dict]) -> dict:
    """
    Submit tasks respecting dependencies.
    Returns {task_id: PrefectFuture}.
    Raises ValueError on cycle or unknown dep.
    """
    task_map = {t["id"]: t for t in tasks}
    fns = {t["id"]: make_prefect_task(t) for t in tasks}
    futures: dict = {}
    remaining = list(task_map.keys())
    resolved: set = set()
    max_iter = len(remaining) ** 2 + 1
    i = 0
    while remaining:
        if i > max_iter:
            raise ValueError(f"Cycle detected: {remaining}")
        tid = remaining.pop(0)
        deps = task_map[tid]["dependencies"]
        if all(d in resolved for d in deps):
            upstream = [futures[d] for d in deps]
            futures[tid] = fns[tid].submit(wait_for=upstream) if upstream else fns[tid].submit()
            resolved.add(tid)
        else:
            remaining.append(tid)
        i += 1
    return futures
