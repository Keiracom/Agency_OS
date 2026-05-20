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
WORKTREE_PARENT = REPO_ROOT.parent  # /home/elliotbot/clawd
WORKTREES: list[Path] = [
    WORKTREE_PARENT / name
    for name in (
        "Agency_OS",
        "Agency_OS-aiden",
        "Agency_OS-atlas",
        "Agency_OS-max",
        "Agency_OS-nova",
        "Agency_OS-orion",
        "Agency_OS-scout",
    )
]
WORKTREES = [w for w in WORKTREES if w.exists()]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("cognee_auto_ingest")


def canonical_rel(path: Path) -> str:
    """Repo-relative path, regardless of which worktree the file lives in.

    Multiple worktrees share the same logical files (e.g. personas/elliot.md
    exists in every worktree). Cognee should see one logical document per
    canonical path so re-ingest from any worktree updates the same entry.
    """
    for root in WORKTREES:
        try:
            return str(path.relative_to(root))
        except ValueError:
            continue
    return str(path)


def _files_in(root: Path) -> list[Path]:
    out: list[Path] = []
    out.extend(sorted((root / "personas").glob("*.md")))
    out.extend(sorted((root / "docs/governance").glob("*.md")))
    for p in (root / "DEFINITION_OF_DONE.md", root / "ARCHITECTURE.md", root / "CLAUDE.md"):
        if p.exists():
            out.append(p)
    out.extend(sorted((root / ".claude/modules").glob("*.md")))
    out.extend(sorted(root.glob("skills/*/SKILL.md")))
    return out


def targets() -> list[Path]:
    """Collect governance files across every worktree, dedup by canonical path.

    When the same canonical path exists in multiple worktrees the elliot
    (primary) copy is preferred so the dominant content is what reaches Cognee.
    """
    primary_first = sorted(WORKTREES, key=lambda w: 0 if w == REPO_ROOT else 1)
    seen_rel: set[str] = set()
    dedup: list[Path] = []
    for root in primary_first:
        for p in _files_in(root):
            rel = canonical_rel(p)
            if rel in seen_rel:
                continue
            seen_rel.add(rel)
            dedup.append(p)
    return dedup


def ingest_one(path: Path) -> bool:
    try:
        text = path.read_text(errors="replace")
    except OSError as e:
        log.error("read fail %s: %s", path, e)
        return False
    rel = canonical_rel(path)
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
    dirs: list[Path] = []
    for root in WORKTREES:
        for sub in ("personas", "docs/governance", ".claude/modules"):
            d = root / sub
            if d.exists():
                dirs.append(d)
    if not dirs:
        log.error("no watchable dirs; exiting")
        return
    cmd = ["inotifywait", "-m", "-r", "-e", "modify,create,moved_to", "--format", "%w%f"] + [str(d) for d in dirs]
    log.info("watching %d dirs across %d worktrees", len(dirs), len(WORKTREES))
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
