#!/usr/bin/env bash
# /kill emergency stop script
# Kills local claude/codex agent processes + cancels active Prefect flow runs
# Called automatically when Dave types /kill in Telegram

set -euo pipefail

echo "🛑 KILL ALL initiated at $(date -u)"

# ── 1. Kill any running claude/codex subagent processes ────────────────────
echo "[1/3] Killing local agent processes..."
pkill -f "claude --permission-mode bypassPermissions" 2>/dev/null && echo "  ✓ Claude Code processes killed" || echo "  · No Claude Code processes found"
pkill -f "codex" 2>/dev/null && echo "  ✓ Codex processes killed" || echo "  · No Codex processes found"

# ── 2. Cancel active Prefect flow runs ─────────────────────────────────────
echo "[2/3] Cancelling active Prefect flow runs..."
source /home/elliotbot/.config/agency-os/.env 2>/dev/null || true

PREFECT_API="${PREFECT_API_URL:-https://prefect-server-production-f9b1.up.railway.app/api}"

# Fetch running/pending flow runs and cancel them
python3 - <<'PYEOF'
import httpx
import os
import sys
from dotenv import load_dotenv

load_dotenv("/home/elliotbot/.config/agency-os/.env")
api_url = os.environ.get("PREFECT_API_URL", "https://prefect-server-production-f9b1.up.railway.app/api")
api_key = os.environ.get("PREFECT_API_KEY", "")

headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

try:
    resp = httpx.post(
        f"{api_url}/flow_runs/filter",
        json={"flow_runs": {"state": {"type": {"any_": ["RUNNING", "PENDING", "SCHEDULED"]}}}},
        headers=headers,
        timeout=10,
    )
    runs = resp.json() if resp.status_code == 200 else []
    if not runs:
        print("  · No active Prefect flow runs found")
    else:
        for run in runs:
            run_id = run.get("id")
            run_name = run.get("name", run_id)
            cancel_resp = httpx.post(
                f"{api_url}/flow_runs/{run_id}/set_state",
                json={"state": {"type": "CANCELLED"}, "force": True},
                headers=headers,
                timeout=10,
            )
            if cancel_resp.status_code in (200, 201):
                print(f"  ✓ Cancelled: {run_name}")
            else:
                print(f"  ✗ Failed to cancel {run_name}: {cancel_resp.status_code}")
except Exception as e:
    print(f"  ✗ Prefect cancel failed: {e}")
PYEOF

# ── 3. Stop evo-consumer if running locally ─────────────────────────────────
echo "[3/3] Checking evo-consumer service..."
if systemctl is-active --quiet evo-consumer 2>/dev/null; then
    systemctl stop evo-consumer && echo "  ✓ evo-consumer stopped" || echo "  ✗ Failed to stop evo-consumer"
else
    echo "  · evo-consumer not running locally (likely on Railway)"
fi

echo ""
echo "✅ KILL ALL complete"
