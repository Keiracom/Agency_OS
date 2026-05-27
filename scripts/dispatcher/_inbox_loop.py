"""Inbox-watch loop with atomic-claim race-safety.

Per PR #1140 §6 Stage 1 (file-claim race-safety + tmux-watcher coexistence):
the dispatcher and the legacy tmux watcher may run in parallel on the same
inbox dir. Atomic `os.rename` to `inbox/processing/<file>` is the chokepoint
— exactly ONE consumer succeeds for each file. The loser sees ENOENT or a
rename-failure (depending on platform) and moves on.

inotify-based watching is a Phase 2 optimisation; polling is fine for
Stage 1 (latency budget = poll interval).

bd: Agency_OS-8416
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

DEFAULT_POLL_SECONDS = 2.0


def iter_claimed_envelopes(
    inbox_dir: Path,
    *,
    processing_dir: Path,
    poll_seconds: float = DEFAULT_POLL_SECONDS,
    stop_after: int | None = None,
    clock: Any = time,
) -> Iterator[tuple[Path, dict]]:
    """Generator yielding (claimed_path, decoded_envelope) for each claimed file.

    `stop_after` (None = forever) bounds the loop for tests. `clock` is
    injectable so tests can substitute a fake (avoid real sleeps).

    Atomic-claim primitive: `os.rename(src, dest)` where dest lives in a
    sibling `processing/` dir. POSIX rename is atomic on the same filesystem;
    if two processes race, exactly one rename succeeds + the other gets
    FileNotFoundError or OSError, which we catch + skip.
    """
    processing_dir.mkdir(parents=True, exist_ok=True)
    iterations = 0
    while stop_after is None or iterations < stop_after:
        for candidate in _scan_inbox(inbox_dir):
            claimed = _try_claim(candidate, processing_dir)
            if claimed is None:
                continue
            envelope = _decode_envelope(claimed)
            if envelope is None:
                continue
            yield claimed, envelope
        iterations += 1
        if stop_after is not None and iterations >= stop_after:
            return
        clock.sleep(poll_seconds)


def _scan_inbox(inbox_dir: Path) -> list[Path]:
    """Return sorted list of *.json files in inbox_dir (non-recursive)."""
    if not inbox_dir.is_dir():
        return []
    return sorted(p for p in inbox_dir.glob("*.json") if p.is_file())


def _try_claim(candidate: Path, processing_dir: Path) -> Path | None:
    """Atomic-rename a candidate into processing/. Returns None on race-loss."""
    dest = processing_dir / candidate.name
    try:
        os.rename(candidate, dest)
    except (FileNotFoundError, OSError) as exc:
        # Either another consumer won the race (FileNotFoundError on src)
        # or the destination FS differs (OSError on cross-device rename).
        # Both are "skip this file" — log at debug, don't spam warnings.
        log.debug("claim failed for %s: %s", candidate.name, exc)
        return None
    return dest


def _decode_envelope(claimed: Path) -> dict | None:
    """Decode the claimed JSON file. Returns None on decode failure."""
    try:
        return json.loads(claimed.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("envelope decode failed for %s: %s", claimed.name, exc)
        return None
