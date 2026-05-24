#!/usr/bin/env python3
"""ingest_to_hindsight.py — wrap fleet data as Hindsight retain() calls.

Mapping (from spike item vi PR #1129 + dispatch):
- Decision   → type="world"      (facts about decisions made + by whom)
- Artifact   → type="experience" (events: PRs merged, commits)
- TaskContext → type="experience" (events: KEI dispatches, review chains)
- AntiPattern → type="experience" + entity_labels=["anti-pattern"]
  (per the "Anti-Pattern Graveyard as node type" idea in eleven_agreed_positions #11)

Uses the Hindsight HTTP API via the official OpenAPI surface. Single bank per
this smoke pilot ("keiracom_smoke"); the multi-tenant TenantExtension boundary
is verified in PR #1126 and not exercised here.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from urllib import error as urlerror
from urllib import request as urlrequest

BASE = "http://localhost:8888"
BANK = "keiracom_smoke"
TIMEOUT = 120

# MAL node-type → tags (Hindsight infers world/experience fact-type from content;
# tags carry our MAL classification + the AntiPattern Graveyard marker per
# eleven_agreed_positions #11 + PR #1129 mapping).
TAGS_MAP = {
    "decision": ["mal_node:decision"],
    "artifact": ["mal_node:artifact"],
    "taskcontext": ["mal_node:taskcontext"],
    "antipattern": ["mal_node:antipattern", "anti-pattern"],
}


def post(path: str, body: dict) -> tuple[int, dict | str]:
    data = json.dumps(body).encode()
    req = urlrequest.Request(
        f"{BASE}{path}",
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlrequest.urlopen(req, timeout=TIMEOUT) as resp:
            return (resp.status, json.loads(resp.read().decode()))
    except urlerror.HTTPError as e:
        return (e.code, {"error": e.read().decode()[:500]})
    except (urlerror.URLError, json.JSONDecodeError, TimeoutError) as e:
        return (0, {"error": str(e)})


def _stringify(meta: dict) -> dict:
    # Hindsight metadata API requires all values to be strings.
    return {
        k: (",".join(map(str, v)) if isinstance(v, list) else str(v))
        for k, v in meta.items()
        if v is not None
    }


def retain_one(record: dict) -> tuple[bool, float, dict]:
    node = record["type"]
    item = {
        "content": record["content"],
        "tags": TAGS_MAP[node] + [f"source:{record.get('source', '?')}"],
        "metadata": _stringify(
            {
                **record.get("metadata", {}),
                "mal_node_type": node,
                "external_id": record["id"],
            }
        ),
    }
    body = {"items": [item], "async": False}
    t0 = time.time()
    status, resp = post(f"/v1/default/banks/{BANK}/memories", body)
    return (200 <= status < 300, time.time() - t0, resp)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", type=Path, default=Path("/tmp/hindsight_smoke_data"))
    p.add_argument(
        "--per-node-limit", type=int, default=5, help="cap per node type for cost-bounded pilot"
    )
    p.add_argument("--out", type=Path, default=Path("/tmp/hindsight_smoke_ingest_log.jsonl"))
    args = p.parse_args()
    if args.out.exists():
        args.out.unlink()
    stats = {"by_node": {}, "total_ok": 0, "total_fail": 0, "total_seconds": 0.0}
    for node in TAGS_MAP:
        src = args.data_dir / f"{node}.jsonl"
        if not src.exists():
            print(f"[skip] no source for {node}", file=sys.stderr)
            continue
        records = [json.loads(line) for line in src.read_text().splitlines() if line.strip()][
            : args.per_node_limit
        ]
        ok = fail = 0
        ttotal = 0.0
        for rec in records:
            success, dt, resp = retain_one(rec)
            ttotal += dt
            if success:
                ok += 1
            else:
                fail += 1
            with args.out.open("a") as f:
                f.write(
                    json.dumps(
                        {
                            "node": node,
                            "id": rec["id"],
                            "ok": success,
                            "seconds": round(dt, 3),
                            "resp_preview": str(resp)[:200],
                        }
                    )
                    + "\n"
                )
            print(f"[{node}] {'OK' if success else 'FAIL'} {rec['id']} ({dt:.2f}s)", flush=True)
        stats["by_node"][node] = {"ok": ok, "fail": fail, "seconds": round(ttotal, 2)}
        stats["total_ok"] += ok
        stats["total_fail"] += fail
        stats["total_seconds"] += ttotal
    stats["total_seconds"] = round(stats["total_seconds"], 2)
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
