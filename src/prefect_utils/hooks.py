from datetime import datetime, timezone
from .failure_alert import send_failure_alert
from .callback_writer import write_flow_callback


# Add to any flow with: @flow(on_failure=[on_failure_hook])
def on_failure_hook(flow, flow_run, state) -> None:
    """Prefect 3.x on_failure hook — sends a Telegram alert on flow failure."""
    flow_name = getattr(flow, "name", str(flow))
    flow_run_id = str(getattr(flow_run, "id", "unknown"))
    deployment_id = str(getattr(flow_run, "deployment_id", None) or "") or None

    try:
        result = state.result(raise_on_failure=False)
        error_message = str(result) if result is not None else "Unknown error"
    except Exception as exc:
        error_message = str(exc)

    timestamp = datetime.now(timezone.utc).isoformat()
    send_failure_alert(
        flow_name=flow_name,
        flow_run_id=flow_run_id,
        error_message=error_message,
        timestamp=timestamp,
    )

    write_flow_callback(
        flow_name=flow_name,
        flow_run_id=flow_run_id,
        deployment_id=deployment_id,
        status="failed",
        result_summary={"error_message": error_message, "timestamp": timestamp},
    )
