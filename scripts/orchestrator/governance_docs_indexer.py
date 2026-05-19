#!/usr/bin/env python3
"""governance_docs_indexer.py — governance + persona + canonical markdown → Weaviate Decisions.

Closes the aiden-surfaced coverage gap (2026-05-19 session 1a5502e8 turn 197):
`docs/governance/*.md` and `personas/*.md` were not indexed, so agent
semantic search for governance content hit only commit messages, not the
source docs themselves. This indexer walks the canonical doc set, chunks
each file at heading boundaries, and upserts to the Decisions collection
with a stable per-file UUID + per-chunk index for re-runs.

Targets (Decisions collection has text2vec-openai vectorizer):
  - personas/*.md
  - docs/governance/*.md
  - DEFINITION_OF_DONE.md
  - ARCHITECTURE.md
  - CLAUDE.md (root)
  - .claude/modules/*.md
  - skills/*/SKILL.md (canonical skill specs only)

Modes:
    --once        : one-shot sync of all targets then exit
    --daemon N    : poll every N seconds (mtime cursor skips unchanged files)

Idempotent: deterministic UUID per (file_path, chunk_index). Re-runs are PUT
upserts so content edits propagate without dups.
"""
from __future__ import annotations
import argparse
import json
import logging
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib import error as urlerror
from urllib import request as urlrequest

WEAVIATE_BASE = f"http://{os.environ.get('WEAVIATE_HOST','127.0.0.1')}:{os.environ.get('WEAVIATE_PORT','8090')}"
REPO_ROOT = Path("/home/elliotbot/clawd/Agency_OS")
CURSOR_PATH = Path("/home/elliotbot/clawd/Agency_OS/.governance_docs_indexer.cursor")
NS = uuid.UUID("9b5b5d51-2a32-4b71-9c5f-7b6c1e3a4d11")
CHUNK_CHARS = 3500
MIN_CHUNK_CHARS = 50

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("governance_docs_indexer")


def discover_targets() -> list[Path]:
    """Return all canonical markdown files to index, ordered + deduped."""
    candidates: list[Path] = []
    candidates.extend(sorted((REPO_ROOT / "personas").glob("*.md")))
    candidates.extend(sorted((REPO_ROOT / "docs/governance").glob("*.md")))
    candidates.append(REPO_ROOT / "DEFINITION_OF_DONE.md")
    candidates.append(REPO_ROOT / "ARCHITECTURE.md")
    candidates.append(REPO_ROOT / "CLAUDE.md")
    candidates.extend(sorted((REPO_ROOT / ".claude/modules").glob("*.md")))
    candidates.extend(sorted(REPO_ROOT.glob("skills/*/SKILL.md")))
    seen: set[Path] = set()
    out: list[Path] = []
    for p in candidates:
        if p.exists() and p not in seen:
            seen.add(p)
            out.append(p)
    return out


def chunk_markdown(text: str, max_chars: int = CHUNK_CHARS) -> list[str]:
    """Chunk markdown at heading boundaries when possible, otherwise at paragraph."""
    if len(text) <= max_chars:
        return [text]
    # split at top-level headings (## or higher)
    sections = re.split(r"\n(?=#{1,3} )", text)
    chunks = []
    current = ""
    for sect in sections:
        if not sect.strip():
            continue
        if len(current) + len(sect) + 1 <= max_chars:
            current = (current + "\n" + sect) if current else sect
        else:
            if current.strip():
                chunks.append(current.strip())
            if len(sect) <= max_chars:
                current = sect
            else:
                # paragraph-level fallback for oversized sections
                for para in sect.split("\n\n"):
                    if len(current) + len(para) + 2 <= max_chars:
                        current = (current + "\n\n" + para) if current else para
                    else:
                        if current.strip():
                            chunks.append(current.strip())
                        current = para
    if current.strip():
        chunks.append(current.strip())
    return [c for c in chunks if len(c) >= MIN_CHUNK_CHARS]


def stable_uuid(file_rel: str, chunk_idx: int) -> str:
    return str(uuid.uuid5(NS, f"governance_docs:{file_rel}:c{chunk_idx}"))


def classify_category(rel: str) -> str:
    if rel.startswith("personas/"):
        return "persona"
    if rel.startswith("docs/governance/"):
        return "governance"
    if rel.startswith(".claude/modules/"):
        return "module"
    if rel.startswith("skills/"):
        return "skill"
    if rel.endswith("DEFINITION_OF_DONE.md"):
        return "definition_of_done"
    if rel.endswith("ARCHITECTURE.md"):
        return "architecture"
    if rel.endswith("CLAUDE.md"):
        return "claude_md"
    return "other"


def upsert(obj_id: str, props: dict) -> str:
    payload = {"class": "Decisions", "id": obj_id, "properties": props}
    # POST first (create); 422 → PUT (update existing)
    req = urlrequest.Request(
        f"{WEAVIATE_BASE}/v1/objects",
        data=json.dumps(payload).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        urlrequest.urlopen(req, timeout=15).read()
        return "created"
    except urlerror.HTTPError as e:
        if e.code in (409, 422):
            r2 = urlrequest.Request(
                f"{WEAVIATE_BASE}/v1/objects/Decisions/{obj_id}",
                data=json.dumps(payload).encode(),
                method="PUT",
                headers={"Content-Type": "application/json"},
            )
            try:
                urlrequest.urlopen(r2, timeout=15).read()
                return "upserted"
            except urlerror.HTTPError as e2:
                return f"err_put:{e2.code}"
        return f"err_post:{e.code}"


def load_cursor() -> dict:
    if CURSOR_PATH.exists():
        try:
            return json.loads(CURSOR_PATH.read_text())
        except Exception:
            return {}
    return {}


def save_cursor(cur: dict) -> None:
    try:
        CURSOR_PATH.write_text(json.dumps(cur, indent=2))
    except OSError as e:
        log.warning("cursor save failed: %s", e)


def process_file(path: Path) -> dict:
    rel = str(path.relative_to(REPO_ROOT))
    text = path.read_text(errors="replace")
    chunks = chunk_markdown(text)
    category = classify_category(rel)
    mtime_iso = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    stats = {"file": rel, "chunks": 0, "created": 0, "upserted": 0, "errors": 0}
    for i, chunk in enumerate(chunks):
        obj_id = stable_uuid(rel, i)
        props = {
            "raw_text": chunk,
            "agent": "governance",
            "kei": "",
            "environment_hash": "",
            "created_at": mtime_iso,
        }
        # Decisions schema accepts raw_text + a few attrs; add source-pointer in raw_text as JSON wrapper
        wrapped = json.dumps({
            "source_path": rel,
            "category": category,
            "chunk_index": i,
            "chunk_total": len(chunks),
            "text": chunk,
            "mtime": mtime_iso,
        })
        props["raw_text"] = wrapped
        result = upsert(obj_id, props)
        if result == "created":
            stats["created"] += 1
        elif result == "upserted":
            stats["upserted"] += 1
        else:
            stats["errors"] += 1
            log.error("upsert err %s/%d: %s", rel, i, result)
        stats["chunks"] += 1
    return stats


def run_once() -> dict:
    cursor = load_cursor()
    targets = discover_targets()
    grand = {"files_scanned": 0, "files_changed": 0, "chunks": 0, "created": 0, "upserted": 0, "errors": 0, "skipped_unchanged": 0}
    for path in targets:
        grand["files_scanned"] += 1
        rel = str(path.relative_to(REPO_ROOT))
        mtime = path.stat().st_mtime
        if cursor.get(rel, {}).get("mtime") == mtime:
            grand["skipped_unchanged"] += 1
            continue
        log.info("processing %s (mtime=%s)", rel, datetime.fromtimestamp(mtime).isoformat())
        try:
            stats = process_file(path)
        except Exception as e:
            log.exception("process_file failed for %s: %s", rel, e)
            grand["errors"] += 1
            continue
        grand["files_changed"] += 1
        grand["chunks"] += stats["chunks"]
        grand["created"] += stats["created"]
        grand["upserted"] += stats["upserted"]
        grand["errors"] += stats["errors"]
        cursor[rel] = {"mtime": mtime, "chunks": stats["chunks"]}
        save_cursor(cursor)
    log.info("run_once done: %s", grand)
    return grand


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--once", action="store_true")
    p.add_argument("--daemon", type=int, metavar="SECONDS")
    args = p.parse_args()
    if args.once:
        run_once()
        return 0
    if args.daemon:
        log.info("daemon mode: poll=%ss", args.daemon)
        while True:
            try:
                run_once()
            except Exception:
                log.exception("daemon iteration failed")
            time.sleep(args.daemon)
    p.error("--once or --daemon required")


if __name__ == "__main__":
    sys.exit(main())
