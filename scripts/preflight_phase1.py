#!/usr/bin/env python3
"""scripts/preflight_phase1.py — Aiden-scope governance smoke tests.

GOV-PHASE1-COMPREHENSIVE-FIX-AIDEN-SCOPE — D6.

Standalone runner — invoke before any directive starts to verify the
Aiden-scope governance services are healthy:

  1. Coordinator       — read claims table for a synthetic key (no rows expected)
  2. Router            — heuristic classification on synthetic input (no live OpenAI)
  3. Mem0              — env presence + adapter init smoke (no add/search call)

Each result is appended to /home/elliotbot/clawd/logs/preflight.jsonl with
verbatim output. Exit 0 if ALL three PASS, non-zero with details if any
FAIL. Companion to ATLAS's preflight_governance_a.py.

Skips (logs SKIP, exit code stays 0) when env prerequisites are missing.
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

PREFLIGHT_LOG = "/home/elliotbot/clawd/logs/preflight.jsonl"


def _log(result: dict) -> None:
    """Append one preflight result row to the JSONL log. Best-effort."""
    try:
        os.makedirs(os.path.dirname(PREFLIGHT_LOG), exist_ok=True)
        with open(PREFLIGHT_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(result) + "\n")
    except Exception as exc:
        print(f"[preflight] log write failed: {exc}", file=sys.stderr)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def check_coordinator() -> dict:
    """Read coordinator_claims for a synthetic target_path. Verifies the
    read path is healthy without polluting state."""
    name = "coordinator_claims_read"
    if not (os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_KEY")):
        return {"name": name, "status": "SKIP",
                "reason": "SUPABASE_URL or SUPABASE_SERVICE_KEY missing"}
    try:
        from src.governance.coordinator import list_active_claims
        rows = list_active_claims(target_path="__preflight_synthetic_path__")
        return {"name": name, "status": "PASS",
                "detail": f"read returned {len(rows)} rows (expected 0)"}
    except Exception as exc:
        return {"name": name, "status": "FAIL",
                "detail": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc()}


def check_router() -> dict:
    """Classify a synthetic input via the heuristic-only path (no OpenAI)."""
    name = "router_heuristic_classify"
    try:
        from src.governance.router import _heuristic_fallback
        synthetic = "[CONCUR] preflight check"
        decision = _heuristic_fallback(synthetic)
        if decision.audience != "peer":
            return {"name": name, "status": "FAIL",
                    "detail": f"expected peer, got {decision.audience}"}
        return {"name": name, "status": "PASS",
                "detail": f"audience={decision.audience} force_tg={decision.force_tg}"}
    except Exception as exc:
        return {"name": name, "status": "FAIL",
                "detail": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc()}


def check_mem0() -> dict:
    """Verify MEM0_API_KEY env + that mem0_adapter module imports cleanly +
    Mem0Adapter() init succeeds. Does NOT make a live add/search call."""
    name = "mem0_env_presence"
    if not os.environ.get("MEM0_API_KEY"):
        return {"name": name, "status": "SKIP", "reason": "MEM0_API_KEY missing"}
    try:
        from src.governance import mem0_adapter  # noqa: F401
    except ImportError as exc:
        return {"name": name, "status": "FAIL",
                "detail": f"mem0_adapter import failed: {exc}"}
    try:
        from src.governance.mem0_adapter import Mem0Adapter
        Mem0Adapter()
        return {"name": name, "status": "PASS",
                "detail": "Mem0Adapter init succeeded"}
    except ImportError as exc:
        return {"name": name, "status": "SKIP",
                "reason": f"mem0ai package not installed: {exc}"}
    except Exception as exc:
        return {"name": name, "status": "FAIL",
                "detail": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc()}


def main() -> int:
    checks = [check_coordinator, check_router, check_mem0]
    results = []
    for fn in checks:
        result = fn()
        result["ts"] = _now_iso()
        result["scope"] = "phase1-aiden"
        results.append(result)
        _log(result)
        status = result["status"]
        detail = result.get("detail") or result.get("reason") or ""
        print(f"[preflight] {result['name']}: {status} — {detail}")

    fails = [r for r in results if r["status"] == "FAIL"]
    if fails:
        print(f"[preflight] FAIL: {len(fails)} of {len(results)} checks failed",
              file=sys.stderr)
        return 1
    print(f"[preflight] OK: {len(results)} checks ran (no FAIL)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
