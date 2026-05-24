#!/usr/bin/env python3
"""extract_fleet_data.py — pull fleet data + map to 4 MAL node types for Hindsight ingest.

Sources (read-only):
- discovery_log.jsonl       → AntiPattern (failed_path) + Decision (verified_path)
- bd closed issues          → TaskContext (KEI dispatch) + Decision (ratified outcomes)
- gh PR API                 → Artifact (PR) + Decision (reviewer ratifications) + TaskContext (review chain)
- (agent_memories deferred — Supabase query out of scope for this pilot pass)

Output: one JSONL file per node type with {id, type, content, source, metadata} records.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DISCOVERY_LOG = (
    Path.home() / ".claude/projects/-home-elliotbot-clawd-Agency-OS/memory/discovery_log.jsonl"
)

# S1192 — shared filenames extracted (each appeared 3-4× inline before).
DECISION_FILENAME = "decision.jsonl"
TASKCONTEXT_FILENAME = "taskcontext.jsonl"
ANTIPATTERN_FILENAME = "antipattern.jsonl"
ARTIFACT_FILENAME = "artifact.jsonl"

# S5443 — confined sub-dir (mode 0o700) instead of bare /tmp. Same pattern as
# PR #1119 weaviate_cutover._SNAPSHOT_DIR. Operators can override via --out-dir.
_DATA_DIR = Path("/tmp/hindsight_smoke_data")  # NOSONAR S5443 — created mode-0o700 below
_DATA_DIR.mkdir(mode=0o700, exist_ok=True)
DEFAULT_DATA_DIR = _DATA_DIR


def emit(out: Path, record: dict) -> None:
    with out.open("a") as f:
        f.write(json.dumps(record) + "\n")


def extract_discovery_log(out_dir: Path, limit: int) -> tuple[int, int]:
    if not DISCOVERY_LOG.exists():
        return (0, 0)
    rows = [json.loads(line) for line in DISCOVERY_LOG.read_text().splitlines() if line.strip()][
        :limit
    ]
    anti_count = dec_count = 0
    for r in rows:
        kei = r.get("kei", "?")
        agent = r.get("agent", "?")
        if r.get("failed_path"):
            emit(
                out_dir / ANTIPATTERN_FILENAME,
                {
                    "id": f"discovery:{kei}:antipattern",
                    "type": "antipattern",
                    "content": f"In {kei} ({r.get('context', '')}): failed_path = {r['failed_path']}. Finding: {r.get('finding', '')}",
                    "source": "discovery_log",
                    "metadata": {"kei": kei, "agent": agent, "tags": r.get("tags", [])},
                },
            )
            anti_count += 1
        if r.get("verified_path"):
            emit(
                out_dir / DECISION_FILENAME,
                {
                    "id": f"discovery:{kei}:decision",
                    "type": "decision",
                    "content": f"For {kei} ({r.get('context', '')}): verified_path = {r['verified_path']}. Finding: {r.get('finding', '')}",
                    "source": "discovery_log",
                    "metadata": {"kei": kei, "agent": agent, "tags": r.get("tags", [])},
                },
            )
            dec_count += 1
    return (anti_count, dec_count)


def extract_bd_issues(out_dir: Path, limit: int) -> tuple[int, int]:
    raw = subprocess.run(
        ["bd", "list", "--status=closed", "--limit", str(limit), "--format=json"],
        capture_output=True,
        text=True,
        check=False,
    )
    if raw.returncode != 0:
        # fallback: text scrape
        return _extract_bd_text(out_dir, limit)
    try:
        issues = json.loads(raw.stdout)
    except json.JSONDecodeError:
        return _extract_bd_text(out_dir, limit)
    tc_count = dec_count = 0
    for issue in issues[:limit]:
        bd_id = issue.get("id", "?")
        title = issue.get("title", "")
        desc = issue.get("description", "")[:1000]
        emit(
            out_dir / TASKCONTEXT_FILENAME,
            {
                "id": f"bd:{bd_id}:taskcontext",
                "type": "taskcontext",
                "content": f"KEI dispatch {bd_id}: {title}. Context: {desc}",
                "source": "bd",
                "metadata": {
                    "bd_id": bd_id,
                    "priority": issue.get("priority"),
                    "assignee": issue.get("assignee"),
                },
            },
        )
        tc_count += 1
        if issue.get("status") == "closed":
            emit(
                out_dir / DECISION_FILENAME,
                {
                    "id": f"bd:{bd_id}:decision",
                    "type": "decision",
                    "content": f"Decision: KEI {bd_id} closed — '{title}' delivered/resolved.",
                    "source": "bd",
                    "metadata": {"bd_id": bd_id, "status": "closed"},
                },
            )
            dec_count += 1
    return (tc_count, dec_count)


def _extract_bd_text(out_dir: Path, limit: int) -> tuple[int, int]:
    raw = subprocess.run(
        ["bd", "list", "--status=closed", "--limit", str(limit)],
        capture_output=True,
        text=True,
        check=False,
    )
    tc = dec = 0
    for line in raw.stdout.splitlines():
        line = line.strip()
        if not line.startswith(("✓", "○", "◐", "●", "❄")):
            continue
        parts = line.split(None, 4)
        if len(parts) < 4:
            continue
        bd_id = parts[1] if len(parts) > 1 else "?"
        title = " ".join(parts[3:])[:300]
        emit(
            out_dir / TASKCONTEXT_FILENAME,
            {
                "id": f"bd:{bd_id}:taskcontext",
                "type": "taskcontext",
                "content": f"KEI {bd_id}: {title}",
                "source": "bd",
                "metadata": {"bd_id": bd_id},
            },
        )
        tc += 1
        emit(
            out_dir / DECISION_FILENAME,
            {
                "id": f"bd:{bd_id}:decision",
                "type": "decision",
                "content": f"Closed: {bd_id} — {title}",
                "source": "bd",
                "metadata": {"bd_id": bd_id},
            },
        )
        dec += 1
    return (tc, dec)


def extract_prs(out_dir: Path, limit: int) -> tuple[int, int, int]:
    raw = subprocess.run(
        [
            "gh",
            "pr",
            "list",
            "--state=merged",
            "--limit",
            str(limit),
            "--json",
            "number,title,body,author,mergedAt,comments",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if raw.returncode != 0:
        return (0, 0, 0)
    prs = json.loads(raw.stdout)
    art = dec = tc = 0
    for pr in prs[:limit]:
        num = pr.get("number")
        title = pr.get("title", "")
        body = (pr.get("body") or "")[:1500]
        author = (pr.get("author") or {}).get("login", "?")
        emit(
            out_dir / ARTIFACT_FILENAME,
            {
                "id": f"pr:{num}:artifact",
                "type": "artifact",
                "content": f"PR #{num} '{title}' merged. Author: {author}. Summary: {body}",
                "source": "github",
                "metadata": {"pr_number": num, "author": author},
            },
        )
        art += 1
        # Reviewer ratifications → Decision per comment from non-author
        for comment in (pr.get("comments") or [])[:5]:
            cb = comment.get("body", "")
            ca = (comment.get("author") or {}).get("login", "?")
            if any(tok in cb for tok in ["[REVIEW:approve:", "[CONCUR:", "[FIXED:"]):
                emit(
                    out_dir / DECISION_FILENAME,
                    {
                        "id": f"pr:{num}:review:{comment.get('id', '?')}",
                        "type": "decision",
                        "content": f"PR #{num} review ratification by {ca}: {cb[:500]}",
                        "source": "github",
                        "metadata": {"pr_number": num, "reviewer": ca},
                    },
                )
                dec += 1
        # Whole PR is a TaskContext for the review chain
        emit(
            out_dir / TASKCONTEXT_FILENAME,
            {
                "id": f"pr:{num}:taskcontext",
                "type": "taskcontext",
                "content": f"PR #{num} review chain on '{title}'. Author {author} with {len(pr.get('comments') or [])} comments.",
                "source": "github",
                "metadata": {"pr_number": num},
            },
        )
        tc += 1
    return (art, dec, tc)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", type=Path, default=DEFAULT_DATA_DIR)
    p.add_argument("--per-source-limit", type=int, default=10, help="cap per source for pilot")
    args = p.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    # Wipe prior runs
    for f in args.out_dir.glob("*.jsonl"):
        f.unlink()
    counts = {}
    counts["discovery"] = extract_discovery_log(args.out_dir, args.per_source_limit)
    counts["bd"] = extract_bd_issues(args.out_dir, args.per_source_limit)
    counts["prs"] = extract_prs(args.out_dir, args.per_source_limit)
    # Tally per node type
    tallies = {}
    for f in args.out_dir.glob("*.jsonl"):
        tallies[f.stem] = sum(1 for _ in f.open())
    print(json.dumps({"per_source": counts, "per_node_type": tallies}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
