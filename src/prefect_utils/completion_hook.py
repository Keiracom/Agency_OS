from .callback_writer import write_flow_callback

# Usage: @flow(on_completion=[on_completion_hook])


def on_completion_hook(flow, flow_run, state) -> None:
    """Prefect 3.x on_completion hook — records completed flow run to Supabase."""
    flow_name = getattr(flow, "name", str(flow))
    flow_run_id = str(getattr(flow_run, "id", "unknown"))
    deployment_id = str(getattr(flow_run, "deployment_id", None) or "") or None

    try:
        result = state.result(raise_on_failure=False)
        result_summary = result if isinstance(result, dict) else {"result": str(result)}
    except Exception as exc:
        result_summary = {"error_extracting_result": str(exc)}

    write_flow_callback(
        flow_name=flow_name,
        flow_run_id=flow_run_id,
        deployment_id=deployment_id,
        status="completed",
        result_summary=result_summary,
    )
