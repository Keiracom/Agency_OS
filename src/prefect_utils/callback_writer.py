import logging
import os

import httpx
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

_ENV_PATH = "/home/elliotbot/.config/agency-os/.env"


def _ensure_env() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        load_dotenv(_ENV_PATH)
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    return url, key


def write_flow_callback(
    flow_name: str,
    flow_run_id: str,
    deployment_id: str | None,
    status: str,
    result_summary: dict,
) -> None:
    """Insert a row into evo_flow_callbacks via Supabase REST API."""
    url, key = _ensure_env()
    if not url or not key:
        logger.error("write_flow_callback: missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
        return

    endpoint = f"{url}/rest/v1/evo_flow_callbacks"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    payload = {
        "flow_name": flow_name,
        "flow_run_id": flow_run_id,
        "deployment_id": deployment_id,
        "status": status,
        "result_summary": result_summary,
    }

    try:
        resp = httpx.post(endpoint, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("write_flow_callback: inserted %s/%s status=%s", flow_name, flow_run_id, status)
    except Exception as exc:
        logger.error("write_flow_callback: failed to insert — %s", exc)
