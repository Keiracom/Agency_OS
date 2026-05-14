#!/usr/bin/env python3
"""write_agent_pairs_key.py — Write ceo:rule:orchestration_agent_pairs to ceo_memory.

Ratified by Dave ts ~1778739200. Run post-merge (or inline during build).
Uses SUPABASE_URL + SUPABASE_SERVICE_KEY from /home/elliotbot/.config/agency-os/.env.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path


def load_env(env_path: str) -> dict[str, str]:
    env: dict[str, str] = {}
    p = Path(env_path)
    if not p.exists():
        return env
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip()
    return env


def main() -> int:
    env = load_env("/home/elliotbot/.config/agency-os/.env")
    url = os.environ.get("SUPABASE_URL") or env.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or env.get("SUPABASE_SERVICE_KEY", "")

    if not url or not key:
        print("ERROR: SUPABASE_URL or SUPABASE_SERVICE_KEY missing", file=sys.stderr)
        return 1

    ratified_at = "2026-05-14T00:00:00+00:00"

    payload = {
        "key": "ceo:rule:orchestration_agent_pairs",
        "value": {
            "kei": "post-prime-pair-deliberation-ratify",
            "rule": (
                "Prime-clone pairing canonical map. Each prime owns one clone for "
                "synthesis-upward + private-channel coordination. Pairings: "
                "Elliot↔Atlas, Aiden↔Orion, Max↔Scout. Clones claim freely from "
                "global Supabase queue (pull-model unchanged) but report "
                "work-progress + escalation via private pair channel only. Scout's "
                "prior research-shared role is fully transferred to Max-CTO scope; "
                "research-task routing flows through Max."
            ),
            "ratified_by": "dave",
            "ratified_at": ratified_at,
            "session": "post-OOM-recovery-2026-05-13",
            "pairs": [
                {"prime": "elliot", "clone": "atlas"},
                {"prime": "aiden", "clone": "orion"},
                {"prime": "max", "clone": "scout"},
            ],
            "five_caveats": [
                "Max↔Scout = full-ownership re-assignment (Scout was prior research-shared)",
                "Read-only #execution access for clones (always-on, preserves peer-review + KEI-43 universal-recovery semantics)",
                "Emergency clone-to-#execution-read-only escalation if prime unreachable >15min",
                "Supabase audit-log persistence for pair-channel traffic + prime cites clone audit-log row when surfacing verbatim",
                "Pairings stored as this ceo_memory key (hot-swappable, no code change to revise)",
            ],
            "phase_2_streams": [
                "execution (primes RW + clones R-only)",
                "elliot-atlas",
                "aiden-orion",
                "max-scout",
                "broadcast (all RW for system events)",
            ],
            "linear_refs": ["deliberation #execution thread 2026-05-14"],
        },
        "updated_at": datetime.now(UTC).isoformat(),
    }

    endpoint = f"{url}/rest/v1/ceo_memory"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }

    body = json.dumps(payload).encode()
    req = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            body_out = resp.read().decode()
            print(f"HTTP {status}")
            print(body_out or "(empty body — upsert OK)")
            return 0
    except urllib.error.HTTPError as exc:
        body_out = exc.read().decode()
        print(f"HTTP {exc.code}: {body_out}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
