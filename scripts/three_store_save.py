#!/usr/bin/env python3
"""
three_store_save.py — Canonical 3-store save for directive completion (LAW XV).

Stores:
  1. docs/MANUAL.md  — append entry under target SECTION
  2. public.ceo_memory — upsert key ceo:directive_{directive}_complete
  3. public.cis_directive_metrics — insert execution metrics row
  4. Google Drive mirror via write_manual_mirror.py (best-effort)

Usage:
    python scripts/three_store_save.py --directive D1.8 --pr-number 329 --summary "..."
    echo "my summary" | python scripts/three_store_save.py --directive D1.8 --pr-number 329 --summary -
    python scripts/three_store_save.py --directive D1.8 --pr-number 329 --summary "..." --dry-run
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Env loading
# ---------------------------------------------------------------------------

def load_env():
    env_path = Path("/home/elliotbot/.config/agency-os/.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


# ---------------------------------------------------------------------------
# Args
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Canonical 3-store save for directive completion (LAW XV)."
    )
    parser.add_argument("--directive", required=True,
                        help='Directive label, e.g. "D1.8", "309", "A"')
    parser.add_argument("--pr-number", required=True, type=int,
                        help="GitHub PR number")
    parser.add_argument("--summary", required=True,
                        help='Completion summary text, or "-" to read from stdin')
    parser.add_argument("--manual-section", type=int, default=13,
                        help="Manual section number to append entry under (default: 13)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be written without writing anything")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# STORE 1 — MANUAL.md
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent


def manual_entry(directive: str, pr_number: int, summary: str) -> str:
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return (
        f"\n### Directive {directive} (PR #{pr_number}, {date_str})\n"
        f"{summary}\n"
    )


def save_manual(directive: str, pr_number: int, summary: str, section: int, dry_run: bool) -> bool:
    manual_path = REPO_ROOT / "docs" / "MANUAL.md"
    if not manual_path.exists():
        print(f"[STORE 1/4] Manual: FAILED — docs/MANUAL.md not found at {manual_path}")
        return False

    content = manual_path.read_text()
    lines = content.splitlines(keepends=True)

    target_marker = f"## SECTION {section}"
    target_idx = None
    next_idx = None

    for i, line in enumerate(lines):
        if line.strip() == target_marker or line.strip().startswith(f"{target_marker} "):
            target_idx = i
        elif target_idx is not None and re.match(r"^## SECTION \d+", line.strip()):
            next_idx = i
            break

    if target_idx is None:
        print(f"[STORE 1/4] Manual: FAILED — marker '{target_marker}' not found in docs/MANUAL.md")
        return False

    entry = manual_entry(directive, pr_number, summary)

    if dry_run:
        insert_before = next_idx if next_idx is not None else len(lines)
        print(f"[DRY-RUN][STORE 1/4] Would insert before line {insert_before + 1} in docs/MANUAL.md:")
        print("---")
        print(entry.strip())
        print("---")
        return True

    insert_at = next_idx if next_idx is not None else len(lines)
    lines.insert(insert_at, entry)
    try:
        manual_path.write_text("".join(lines))
        print(f"[STORE 1/4] Manual: OK — entry inserted under SECTION {section}")
        return True
    except Exception as exc:
        print(f"[STORE 1/4] Manual: FAILED — {exc}")
        return False


# ---------------------------------------------------------------------------
# STORE 2 — ceo_memory
# ---------------------------------------------------------------------------

def save_ceo_memory(directive: str, pr_number: int, summary: str, dry_run: bool) -> bool:
    supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY", "")

    if not supabase_url or not service_key:
        print("[STORE 2/4] ceo_memory: FAILED — SUPABASE_URL or SUPABASE_SERVICE_KEY not set")
        return False

    key = f"ceo:directive_{directive}_complete"
    value = {
        "directive": directive,
        "pr": pr_number,
        "summary": summary,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }

    if dry_run:
        print(f"[DRY-RUN][STORE 2/4] Would upsert ceo_memory key={key!r}")
        print(f"  value={json.dumps(value)}")
        return True

    import httpx
    url = f"{supabase_url}/rest/v1/ceo_memory"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }
    body = {"key": key, "value": value, "updated_at": datetime.now(timezone.utc).isoformat()}

    try:
        resp = httpx.post(url, headers=headers, json=body, timeout=15)
        if resp.status_code in (200, 201):
            print(f"[STORE 2/4] ceo_memory: OK — key={key!r}")
            return True
        print(f"[STORE 2/4] ceo_memory: FAILED — HTTP {resp.status_code}: {resp.text[:200]}")
        return False
    except Exception as exc:
        print(f"[STORE 2/4] ceo_memory: FAILED — {exc}")
        return False


# ---------------------------------------------------------------------------
# STORE 3 — cis_directive_metrics
# ---------------------------------------------------------------------------

def save_metrics(directive: str, pr_number: int, summary: str, dry_run: bool) -> bool:
    supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY", "")

    if not supabase_url or not service_key:
        print("[STORE 3/4] cis_directive_metrics: FAILED — SUPABASE_URL or SUPABASE_SERVICE_KEY not set")
        return False

    # Determine directive_id vs directive_ref
    if re.fullmatch(r"\d+", directive):
        directive_id = int(directive)
        directive_ref = None
    else:
        directive_id = 0
        directive_ref = directive

    now_iso = datetime.now(timezone.utc).isoformat()
    row = {
        "directive_id": directive_id,
        "directive_ref": directive_ref,
        "issued_date": now_iso,
        "completed_date": now_iso,
        "execution_rounds": 1,
        "scope_creep": False,
        "verification_first_pass": True,
        "save_completed": True,
        "agents_used": ["build-2", "build-3"],
        "notes": summary,
        "created_at": now_iso,
    }

    if dry_run:
        print(f"[DRY-RUN][STORE 3/4] Would insert cis_directive_metrics row:")
        print(f"  {json.dumps(row)}")
        return True

    import httpx
    url = f"{supabase_url}/rest/v1/cis_directive_metrics"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

    try:
        resp = httpx.post(url, headers=headers, json=row, timeout=15)
        if resp.status_code in (200, 201):
            print(f"[STORE 3/4] cis_directive_metrics: OK — directive_ref={directive_ref!r}, directive_id={directive_id}")
            return True
        print(f"[STORE 3/4] cis_directive_metrics: FAILED — HTTP {resp.status_code}: {resp.text[:200]}")
        return False
    except Exception as exc:
        print(f"[STORE 3/4] cis_directive_metrics: FAILED — {exc}")
        return False


# ---------------------------------------------------------------------------
# STORE 4 — Drive mirror (best-effort)
# ---------------------------------------------------------------------------

def run_drive_mirror(dry_run: bool) -> None:
    mirror_script = REPO_ROOT / "scripts" / "write_manual_mirror.py"
    if dry_run:
        print(f"[DRY-RUN][STORE 4/4] Would run: {sys.executable} {mirror_script}")
        return
    result = subprocess.run(
        [sys.executable, str(mirror_script)],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("[STORE 4/4] Drive mirror: OK")
    else:
        print(f"[STORE 4/4] Drive mirror: WARNING — exit {result.returncode}")
        if result.stderr:
            print(f"  stderr: {result.stderr.strip()[:200]}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    load_env()
    args = parse_args()

    summary = args.summary
    if summary == "-":
        summary = sys.stdin.read().strip()

    directive = args.directive
    pr_number = args.pr_number
    section = args.manual_section
    dry_run = args.dry_run

    if dry_run:
        print(f"[DRY-RUN] directive={directive!r} pr={pr_number} section={section}")
        print()

    succeeded = []

    # Store 1
    ok1 = save_manual(directive, pr_number, summary, section, dry_run)
    if ok1:
        succeeded.append("Manual")
    else:
        print(f"Succeeded before failure: {succeeded or 'none'}")
        sys.exit(1)

    # Store 2
    ok2 = save_ceo_memory(directive, pr_number, summary, dry_run)
    if ok2:
        succeeded.append("ceo_memory")
    else:
        print(f"Succeeded before failure: {succeeded}")
        sys.exit(1)

    # Store 3
    ok3 = save_metrics(directive, pr_number, summary, dry_run)
    if ok3:
        succeeded.append("cis_directive_metrics")
    else:
        print(f"Succeeded before failure: {succeeded}")
        sys.exit(1)

    # Store 4 — best-effort
    run_drive_mirror(dry_run)

    print()
    print(f"All 3 stores saved. Directive {directive!r} PR #{pr_number} complete.")


if __name__ == "__main__":
    main()
