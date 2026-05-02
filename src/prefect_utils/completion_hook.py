from .callback_writer import write_flow_callback

# Usage: @flow(on_completion=[on_completion_hook])


def on_completion_hook(flow, flow_run, state) -> None:
    """Prefect 3.x on_completion hook — records completed flow run to Supabase."""
    flow_name = getattr(flow, "name", str(flow))
    flow_run_id = str(getattr(flow_run, "id", "unknown"))
    deployment_id = str(getattr(flow_run, "deployment_id", None) or "") or None

    import asyncio
    import inspect
    import json

    try:
        raw = state.result(raise_on_failure=False)
        # Prefect 3.x: state.result() returns a coroutine for async flows.
        # asyncio.run() and get_event_loop().run_until_complete() both raise
        # RuntimeError when called from inside Prefect's already-running loop.
        # Run the coroutine in a fresh thread with its own event loop instead.
        if inspect.isawaitable(raw):
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, raw)
                raw = future.result(timeout=30)

        # Recursively stringify anything not JSON-serializable
        def _safe(v):
            if isinstance(v, dict):
                return {k: _safe(val) for k, val in v.items()}
            if isinstance(v, (list, tuple)):
                return [_safe(i) for i in v]
            try:
                json.dumps(v)
                return v
            except (TypeError, ValueError):
                return str(v)

        result_summary = _safe(raw) if isinstance(raw, dict) else {"result": _safe(raw)}
    except Exception as exc:
        result_summary = {"error_extracting_result": str(exc)}

    write_flow_callback(
        flow_name=flow_name,
        flow_run_id=flow_run_id,
        deployment_id=deployment_id,
        status="completed",
        result_summary=result_summary,
    )
