from datetime import UTC, datetime

from .callback_writer import write_flow_callback
from .failure_alert import send_failure_alert


# Add to any flow with: @flow(on_failure=[on_failure_hook])
def on_failure_hook(flow, flow_run, state) -> None:
    """Prefect 3.x on_failure hook — sends a Telegram alert on flow failure."""
    flow_name = getattr(flow, "name", str(flow))
    flow_run_id = str(getattr(flow_run, "id", "unknown"))
    deployment_id = str(getattr(flow_run, "deployment_id", None) or "") or None

    try:
        # In Prefect 3.x, state.result() is async — use message attribute instead
        error_message = getattr(state, "message", None) or str(state)
    except Exception as exc:
        error_message = str(exc)

    timestamp = datetime.now(UTC).isoformat()
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
