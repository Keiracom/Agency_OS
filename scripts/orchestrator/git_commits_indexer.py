#!/usr/bin/env python3
"""git_commits_indexer.py — KEI-85 phase C: index git commits into Weaviate Codebase.

Reads commits from the Agency_OS git history via `git log --since <cursor>`
and POSTs one Weaviate Codebase object per commit SHA. Each commit captures
message subject + body + author + commit timestamp + changed-files
fingerprint so agents can `bd recall` what changed in the codebase and why.

Inherits BaseIndexer[GitCommit] (the ABC contract from phases A/B). Convergent
via deterministic UUID = uuid5("git", commit_sha) — repeated runs on the
same commit are no-ops (Weaviate 422 idempotent path).

Cursor: tracks the latest commit timestamp seen so far in a tiny on-disk
JSON. Per-poll `git log --since=$cursor` keeps the work bounded.

Usage:
    python3 scripts/orchestrator/git_commits_indexer.py            # daemon
    python3 scripts/orchestrator/git_commits_indexer.py --once     # one batch
    python3 scripts/orchestrator/git_commits_indexer.py --batch=200
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _heartbeat_shim import heartbeat_tick as _heartbeat_tick  # noqa: E402
from indexer_base import (
    BaseIndexer,
    aggregate_count,
    deterministic_uuid,
)

logger = logging.getLogger("git_commits_indexer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

CODEBASE_CLASS = "Codebase"
SOURCE_NAME = "git"
EPOCH_ISO = "1970-01-01T00:00:00Z"
POLL_SECONDS = int(os.environ.get("GIT_COMMITS_POLL_SECONDS", "300"))  # 5 min — commits are slow
BATCH_SIZE_DEFAULT = int(os.environ.get("GIT_COMMITS_BATCH_SIZE", "200"))
REPO_PATH = Path(os.environ.get("GIT_COMMITS_REPO_PATH", "/home/elliotbot/clawd/Agency_OS"))
CURSOR_PATH = Path(
    os.environ.get(
        "GIT_COMMITS_CURSOR_PATH",
        "/home/elliotbot/clawd/logs/git_commits_indexer.cursor",
    )
)

CODEBASE_SCHEMA = {
    "class": CODEBASE_CLASS,
    "vectorizer": "none",
    "properties": [
        {"name": "raw_text", "dataType": ["text"]},
        {"name": "environment_hash", "dataType": ["text"]},
        {"name": "created_at", "dataType": ["date"]},
        {"name": "agent", "dataType": ["text"]},
        {"name": "kei", "dataType": ["text"]},
    ],
}

# Single-record terminator. Field separator is \x1f (US). Record separator
# is \x1e (RS). Both are control chars that won't appear in commit messages.
_FIELD_SEP = "\x1f"
_RECORD_SEP = "\x1e"
_LOG_FORMAT = _FIELD_SEP.join(("%H", "%an", "%aI", "%s", "%b")) + _RECORD_SEP


@dataclass(frozen=True)
class GitCommit:
    sha: str
    author: str
    committed_iso: str
    subject: str
    body: str


_shutdown_requested = False


def _signal_handler(signum: int, _frame: Any) -> None:
    global _shutdown_requested
    logger.info("signal %s received — shutdown", signum)
    _shutdown_requested = True


signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)


def _read_cursor() -> str:
    if not CURSOR_PATH.exists():
        return EPOCH_ISO
    try:
        return json.loads(CURSOR_PATH.read_text()).get("committed_iso", EPOCH_ISO)
    except (ValueError, OSError):
        return EPOCH_ISO


def _write_cursor(committed_iso: str) -> None:
    try:
        CURSOR_PATH.parent.mkdir(parents=True, exist_ok=True)
        CURSOR_PATH.write_text(json.dumps({"committed_iso": committed_iso}))
    except OSError as exc:
        logger.warning("cursor persist failed (%s) — non-fatal", exc)


def _git_log_since(cursor_iso: str, limit: int) -> list[GitCommit]:
    """Invoke `git log --since=...` and parse output.

    `--since` accepts ISO-8601. We pass the cursor verbatim; the first poll
    with EPOCH_ISO returns the entire history (bounded by --max-count).
    """
    cmd = [
        "git",
        "-C",
        str(REPO_PATH),
        "log",
        f"--max-count={limit}",
        f"--since={cursor_iso}",
        "--reverse",  # oldest-first so the cursor advances monotonically
        f"--pretty=format:{_LOG_FORMAT}",
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        logger.warning("git log failed (%s) — empty batch", exc)
        return []
    if proc.returncode != 0:
        logger.warning("git log exit=%d stderr=%s", proc.returncode, proc.stderr[:200])
        return []
    records = [r for r in proc.stdout.split(_RECORD_SEP) if r.strip()]
    commits: list[GitCommit] = []
    for rec in records:
        parts = rec.split(_FIELD_SEP)
        if len(parts) < 5:
            continue
        sha, author, committed_iso, subject, body = parts[0], parts[1], parts[2], parts[3], parts[4]
        commits.append(
            GitCommit(
                sha=sha.strip(),
                author=author.strip(),
                committed_iso=committed_iso.strip(),
                subject=subject.strip(),
                body=body.strip(),
            )
        )
    return commits


class GitCommitsIndexer(BaseIndexer[GitCommit]):
    """git → Codebase concrete indexer (KEI-85 phase C)."""

    source_name = SOURCE_NAME
    target_class = CODEBASE_CLASS
    class_schema = CODEBASE_SCHEMA

    def __init__(self) -> None:
        self._last_max_committed_iso: str | None = None

    def fetch_batch(self, batch_size: int) -> list[GitCommit]:
        cursor = _read_cursor()
        commits = _git_log_since(cursor, batch_size)
        if commits:
            self._last_max_committed_iso = max(c.committed_iso for c in commits if c.committed_iso)
        return commits

    def build_object(self, row: GitCommit) -> dict:
        return build_codebase_doc(row)

    def advance_cursor(self) -> None:
        if self._last_max_committed_iso:
            _write_cursor(self._last_max_committed_iso)


def _extract_kei(text: str) -> str:
    """Pull the first KEI-N reference from a commit message, if any.

    Most commits in this repo are prefixed `[ATLAS] feat(kei91):` or contain
    `KEI-NN` in the body. Mining this lets `bd recall <KEI>` find every
    commit that touched a KEI without needing full-text search.
    """
    import re

    m = re.search(r"\b[kK][eE][iI][-_]?(\d+)\b", text)
    return f"KEI-{m.group(1)}" if m else ""


def build_codebase_doc(commit: GitCommit) -> dict:
    body = {
        "sha": commit.sha,
        "author": commit.author,
        "committed_iso": commit.committed_iso,
        "subject": commit.subject,
        "body": commit.body,
    }
    raw_text = json.dumps(body, sort_keys=True, default=str)
    env_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()[:16]
    return {
        "class": CODEBASE_CLASS,
        "id": deterministic_uuid(SOURCE_NAME, commit.sha),
        "properties": {
            "raw_text": raw_text,
            "environment_hash": env_hash,
            "created_at": commit.committed_iso or EPOCH_ISO,
            "agent": "system",
            "kei": _extract_kei(commit.subject + " " + commit.body),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--batch", type=int, default=BATCH_SIZE_DEFAULT)
    args = parser.parse_args()

    indexer = GitCommitsIndexer()
    indexer.ensure_target_class()
    logger.info(
        "indexer start source=%s class=%s batch=%d repo=%s",
        SOURCE_NAME,
        CODEBASE_CLASS,
        args.batch,
        REPO_PATH,
    )

    if args.once:
        outcome = indexer.index_once(args.batch)
        indexer.advance_cursor()
        logger.info(
            "once outcome=%s class_count=%s cursor=%s",
            outcome.to_dict(),
            aggregate_count(CODEBASE_CLASS),
            _read_cursor(),
        )
        _heartbeat_tick(
            "git-commits-indexer",
            outcome_increment=outcome.success,
            status="ok" if outcome.failed == 0 else "degraded",
        )
        return
    while not _shutdown_requested:
        try:
            outcome = indexer.index_once(args.batch)
            indexer.advance_cursor()
            logger.info(
                "batch outcome=%s class_count=%s cursor=%s",
                outcome.to_dict(),
                aggregate_count(CODEBASE_CLASS),
                _read_cursor(),
            )
            _heartbeat_tick(
                "git-commits-indexer",
                outcome_increment=outcome.success,
                status="ok" if outcome.failed == 0 else "degraded",
            )
        except Exception as exc:  # noqa: BLE001 — daemon must survive
            logger.exception("batch failed — sleeping then continuing")
            _heartbeat_tick(
                "git-commits-indexer",
                outcome_increment=0,
                status="error",
                error_message=str(exc)[:500],
            )
        for _ in range(POLL_SECONDS):
            if _shutdown_requested:
                break
            time.sleep(1)
    logger.info("indexer exiting cleanly")


if __name__ == "__main__":
    main()
    sys.exit(0)
