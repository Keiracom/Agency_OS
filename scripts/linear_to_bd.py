#!/usr/bin/env python3
"""linear_to_bd.py — Linear-event → Beads CRUD subprocess wrapper.

Read from PR-1 of the Linear↔Beads sync automation. Stdin: JSON envelope from
src/api/webhooks/linear.py with the minimal canonical shape:

  {"op": "create",  "identifier": "KEI-99", "title": "...", "priority": 0..4, "url": "..."}
  {"op": "status",  "identifier": "KEI-99", "bd_status": "active"|"closed", "url": "..."}

Idempotency:
  - create: skip if `bd list --json` already has an issue with matching
    external-ref URL (Linear is the join key).
  - status: skip if the existing bd issue's status already matches.

Always exits 0 — operator-script discipline. Errors logged to stderr.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger("linear_to_bd")
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

_BD_BIN_DEFAULT = os.path.expanduser("~/.local/bin/bd")


def _bd_bin() -> str:
    return os.environ.get("AGENCY_OS_BD_BIN", _BD_BIN_DEFAULT)


def _run_bd(args: list[str], stdin: str | None = None, timeout: int = 15) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(  # noqa: S603 — controlled args, no shell
            [_bd_bin(), *args],
            input=stdin,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        logger.warning("bd %s failed: %s", args, exc)
        return -1, "", str(exc)
    return proc.returncode, proc.stdout, proc.stderr


def find_existing_by_url(url: str) -> dict | None:
    """Return the bd issue whose external-ref matches `url`, else None."""
    if not url:
        return None
    rc, out, _ = _run_bd(["list", "--json"])
    if rc != 0:
        return None
    try:
        issues = json.loads(out or "[]")
    except json.JSONDecodeError:
        return None
    for issue in issues:
        # Beads stores external-ref under different shapes across versions —
        # check both `external_ref` and `metadata.external_ref`.
        ref = issue.get("external_ref") or (issue.get("metadata") or {}).get("external_ref")
        if ref == url:
            return issue
    return None


def handle_create(event: dict) -> int:
    """Idempotent create: skip if external-ref already mapped."""
    url = event.get("url", "")
    existing = find_existing_by_url(url)
    if existing:
        logger.info("create idempotent skip: %s already mapped to bd %s", url, existing.get("id"))
        return 0
    title = event["title"]
    priority = int(event.get("priority", 2))
    args = [
        "create",
        "--title", title,
        "--description", f"Synced from Linear: {url}",
        "--type", "task",
        "--priority", str(priority),
        "--external-ref", url,
    ]
    rc, _out, err = _run_bd(args)
    if rc != 0:
        logger.warning("bd create failed: %s", err[:200])
    return 0


def handle_status(event: dict) -> int:
    """Idempotent status update: skip if bd status already matches."""
    url = event.get("url", "")
    existing = find_existing_by_url(url)
    if not existing:
        logger.info("status: no bd issue mapped to %s; skip", url)
        return 0
    bd_id = existing.get("id")
    desired = event["bd_status"]
    current = (existing.get("status") or "").lower()
    if desired == current or (desired == "closed" and current in {"closed", "done"}):
        logger.info("status idempotent skip: %s already at %s", bd_id, current)
        return 0
    if desired == "closed":
        _run_bd(["close", bd_id])
    else:
        _run_bd(["update", bd_id, "--status", desired])
    return 0


_HANDLERS = {"create": handle_create, "status": handle_status}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Read event JSON from stdin")
    parser.add_argument("--event-file", type=Path, default=None, help="Read event JSON from file")
    args = parser.parse_args(argv)

    raw = ""
    try:
        if args.event_file is not None and args.event_file.exists():
            raw = args.event_file.read_text()
        elif args.json or not sys.stdin.isatty():
            raw = sys.stdin.read()
    except OSError as exc:
        logger.warning("read event failed: %s", exc)
        return 0

    if not raw.strip():
        return 0
    try:
        event = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("event JSON parse failed: %s", exc)
        return 0

    op = event.get("op")
    handler = _HANDLERS.get(op)
    if not handler:
        logger.warning("unknown op: %r", op)
        return 0
    return handler(event)


if __name__ == "__main__":
    sys.exit(main())
