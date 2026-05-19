#!/usr/bin/env python3
"""cognee_auto_ingest.py — re-ingest governance files into Cognee on change.

Two modes:
  --once  : ingest all canonical governance files once
  --watch : inotify-watch the governance dirs and ingest individual files on modify

Uses the Cognee HTTP API via cognee_http_client to avoid the SDK lock conflict.
Fail-open per file; logs successes + failures to stderr.
"""
from __future__ import annotations
import argparse
import logging
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, "/home/elliotbot/clawd/Agency_OS/scripts")
from cognee_http_client import ingest as cognee_ingest, health as cognee_health  # noqa: E402

REPO_ROOT = Path("/home/elliotbot/clawd/Agency_OS")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("cognee_auto_ingest")


def targets() -> list[Path]:
    out: list[Path] = []
    out.extend(sorted((REPO_ROOT / "personas").glob("*.md")))
    out.extend(sorted((REPO_ROOT / "docs/governance").glob("*.md")))
    for p in (REPO_ROOT / "DEFINITION_OF_DONE.md", REPO_ROOT / "ARCHITECTURE.md", REPO_ROOT / "CLAUDE.md"):
        if p.exists():
            out.append(p)
    out.extend(sorted((REPO_ROOT / ".claude/modules").glob("*.md")))
    out.extend(sorted(REPO_ROOT.glob("skills/*/SKILL.md")))
    seen: set[Path] = set()
    dedup: list[Path] = []
    for p in out:
        if p in seen:
            continue
        seen.add(p)
        dedup.append(p)
    return dedup


def ingest_one(path: Path) -> bool:
    try:
        text = path.read_text(errors="replace")
    except OSError as e:
        log.error("read fail %s: %s", path, e)
        return False
    rel = str(path.relative_to(REPO_ROOT))
    result = cognee_ingest(text, source_path=rel)
    if result is None:
        log.warning("ingest no-token %s", rel)
        return False
    if isinstance(result, dict) and result.get("error"):
        log.warning("ingest err %s: %s", rel, result.get("error"))
        return False
    log.info("ingested %s (%d chars)", rel, len(text))
    return True


def run_once() -> dict:
    h = cognee_health()
    if h.get("status") != "ready":
        log.error("cognee not ready: %s", h)
        return {"files": 0, "ok": 0, "errors": 1, "skipped_unhealthy": True}
    paths = targets()
    stats = {"files": len(paths), "ok": 0, "errors": 0}
    for p in paths:
        if ingest_one(p):
            stats["ok"] += 1
        else:
            stats["errors"] += 1
    log.info("once done: %s", stats)
    return stats


def watch_loop() -> None:
    dirs = [
        REPO_ROOT / "personas",
        REPO_ROOT / "docs/governance",
        REPO_ROOT / ".claude/modules",
    ]
    dirs = [d for d in dirs if d.exists()]
    if not dirs:
        log.error("no watchable dirs; exiting")
        return
    cmd = ["inotifywait", "-m", "-r", "-e", "modify,create,moved_to", "--format", "%w%f"] + [str(d) for d in dirs]
    log.info("watching %s", [str(d) for d in dirs])
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
    except FileNotFoundError:
        log.error("inotifywait not installed")
        return
    debounce: dict[str, float] = {}
    while True:
        try:
            line = proc.stdout.readline()
            if not line:
                time.sleep(1)
                continue
            fpath = line.strip()
            if not fpath.endswith(".md"):
                continue
            now = time.time()
            if now - debounce.get(fpath, 0) < 5:
                continue
            debounce[fpath] = now
            p = Path(fpath)
            if p.exists():
                log.info("change detected: %s", fpath)
                ingest_one(p)
        except KeyboardInterrupt:
            break
        except Exception as e:
            log.exception("watch loop err: %s", e)
            time.sleep(2)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--once", action="store_true")
    p.add_argument("--watch", action="store_true")
    args = p.parse_args()
    if args.once:
        run_once()
        return 0
    if args.watch:
        watch_loop()
        return 0
    p.error("--once or --watch required")


if __name__ == "__main__":
    sys.exit(main())
