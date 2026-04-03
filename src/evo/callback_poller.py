import os, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
import httpx
from dotenv import load_dotenv
sys.path.insert(0, str(Path(__file__).parents[2]))
from src.evo.tg_notify import tg_send

load_dotenv(Path("/home/elliotbot/.config/agency-os/.env"))
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
_H = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
_URL = f"{SUPABASE_URL}/rest/v1/evo_flow_callbacks"


def _claim(row_id) -> bool:
    body = {"consumed_at": datetime.now(timezone.utc).isoformat(), "consumed_by": "elliottbot:poller"}
    params = {"id": f"eq.{row_id}", "consumed_at": "is.null", "select": "id"}
    r = httpx.patch(_URL, headers={**_H, "Prefer": "return=representation"}, params=params, json=body, timeout=10)
    return bool(r.json())


def _handle(row):
    fn, rid, created = row.get("flow_name", ""), row.get("flow_run_id", ""), row.get("created_at", "")
    status = row.get("status", "")
    try:
        age = datetime.now(timezone.utc) - datetime.fromisoformat(created.replace("Z", "+00:00"))
        if age > timedelta(hours=24):
            tg_send(f"⚠️ Stale callback\nFlow: {fn}\nRun: {rid}\nAge: >24h")
            httpx.patch(_URL, headers=_H, params={"id": f"eq.{row['id']}"}, json={"consumed_by": "elliottbot:stale-sweep"}, timeout=10)
            return
    except Exception:
        pass
    if status == "completed":
        tg_send(f"✅ Prefect flow completed\nFlow: {fn}\nRun: {rid}\nTime: {created}")
    elif status in ("failed", "crashed"):
        from src.prefect_utils.failure_alert import send_failure_alert
        send_failure_alert(fn, rid, str(row.get("result_summary", "")), created)


def poll_callbacks() -> int:
    params = {"consumed_at": "is.null", "order": "created_at.asc", "limit": "5", "select": "*"}
    rows = httpx.get(_URL, headers=_H, params=params, timeout=10).json()
    count = sum(_claim(row["id"]) and not _handle(row) for row in rows)
    return count


if __name__ == "__main__":
    print(f"Processed {poll_callbacks()} callback(s)")
