#!/usr/bin/env python3
"""slack_history_indexer.py — KEI-201 Phase 2: incremental Slack → Weaviate daemon.

One-shot run: reads a per-channel `last_ts` checkpoint, calls Slack's
conversations.history with `oldest=<last_ts>` for each of the 5 ratified
channels, filters + classifies (reusing `slack_history_ingest`'s logic), upserts
new messages into Weaviate `Slack_history`, and writes the new checkpoint on
success.

Invoked by `slack_history_indexer.timer` every 15 min.

Checkpoint location (XDG state):
    $XDG_STATE_HOME/agency-os/slack_history_checkpoint.json
    default: ~/.local/state/agency-os/slack_history_checkpoint.json

Override via env var SLACK_HISTORY_CHECKPOINT (absolute path).

Cold start: no checkpoint file → bootstrap with current timestamp so the
indexer only catches messages from "now forward". Bulk backfill is the
companion `slack_history_ingest.py` extractor's job (KEI-201 Phase 1).

Exit codes:
    0  success (any posts/failures logged)
    1  SLACK_BOT_TOKEN missing
    2  channel resolution failed
    3  Weaviate class missing AND ensure_class failed
"""

from __future__ import annotations

import argparse
import datetime as _dt
import importlib.util
import json
import logging
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS = REPO_ROOT / "scripts" / "orchestrator"
INGEST_PATH = SCRIPTS / "slack_history_ingest.py"


def _load_ingest():
    spec = importlib.util.spec_from_file_location("slack_history_ingest", INGEST_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {INGEST_PATH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["slack_history_ingest"] = mod
    spec.loader.exec_module(mod)
    return mod


ingest = _load_ingest()

logger = logging.getLogger("slack_history_indexer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def checkpoint_path() -> Path:
    """Resolve checkpoint path: env override → XDG_STATE_HOME → ~/.local/state."""
    override = os.environ.get("SLACK_HISTORY_CHECKPOINT")
    if override:
        return Path(override)
    state_root = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(state_root) / "agency-os" / "slack_history_checkpoint.json"


def load_checkpoint(path: Path) -> dict[str, str]:
    """Return {channel_slug: last_ts} or {} if no checkpoint yet (cold start)."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("checkpoint %s unreadable (%s) — treating as cold start", path, exc)
        return {}


def save_checkpoint(path: Path, data: dict[str, str]) -> None:
    """Atomic write: tmp + rename → no torn writes if process dies mid-write."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True))
    tmp.replace(path)


def bootstrap_now_ts() -> str:
    """Slack ts format: 'unix_seconds.microseconds_padded' — used as cold-start anchor."""
    now = _dt.datetime.now(_dt.UTC).timestamp()
    return f"{now:.6f}"


def index_channel(
    slug: str,
    ch_id: str,
    oldest: str,
    by_type: dict[str, int],
) -> tuple[int, int, int, str]:
    """Returns (kept, posted, failed, new_last_ts) for one channel.

    new_last_ts = max(message.ts seen) — used as next checkpoint. Falls back to
    `oldest` if no new messages (so checkpoint advances only when we saw data).
    """
    kept = posted = failed = 0
    max_ts = oldest
    for raw in ingest.paginate_history(ch_id, oldest=oldest, total_cap=5_000):
        msg = ingest.slack_to_message(slug, raw)
        if msg is None:
            continue
        if msg.ts > max_ts:
            max_ts = msg.ts
        by_type[msg.message_type] = by_type.get(msg.message_type, 0) + 1
        kept += 1
        if ingest.post_object(ingest.build_object(msg)):
            posted += 1
        else:
            failed += 1
    return kept, posted, failed, max_ts


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="resolve channels + fetch since checkpoint, but do not POST or update checkpoint",
    )
    parser.add_argument(
        "--channel",
        choices=ingest.CHANNEL_SLUGS,
        default=None,
        help="restrict to one channel (default: all 5)",
    )
    parser.add_argument(
        "--reset-checkpoint",
        action="store_true",
        help="ignore current checkpoint and bootstrap from now (use after schema cutover)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if not ingest.BOT_TOKEN:
        logger.error("SLACK_BOT_TOKEN not set — required for incremental indexer")
        return 1

    cp_path = checkpoint_path()
    checkpoint = {} if args.reset_checkpoint else load_checkpoint(cp_path)
    channels = (args.channel,) if args.channel else ingest.CHANNEL_SLUGS

    if not args.dry_run:
        try:
            ingest.ensure_class()
        except Exception as exc:  # noqa: BLE001 — surface any schema-create failure
            logger.error("ensure_class failed: %s", exc)
            return 3

    channel_ids = ingest.resolve_channel_ids(channels)
    if not channel_ids:
        logger.error("none of the named channels resolved — check bot permissions")
        return 2

    new_checkpoint = dict(checkpoint)
    by_channel: dict[str, int] = {}
    by_type: dict[str, int] = {}
    total_posted = total_failed = 0
    started = time.time()

    for slug in channels:
        ch_id = channel_ids.get(slug)
        if not ch_id:
            logger.warning("channel #%s did not resolve — skipping", slug)
            continue
        oldest = checkpoint.get(slug) or bootstrap_now_ts()
        cold_start = slug not in checkpoint
        logger.info(
            "indexing #%s (%s) since ts=%s%s",
            slug,
            ch_id,
            oldest,
            " [cold-start]" if cold_start else "",
        )
        kept, posted, failed, new_last_ts = index_channel(slug, ch_id, oldest, by_type)
        by_channel[slug] = kept
        total_posted += posted
        total_failed += failed
        new_checkpoint[slug] = new_last_ts

    if not args.dry_run and total_failed == 0:
        save_checkpoint(cp_path, new_checkpoint)

    elapsed_ms = int((time.time() - started) * 1000)
    logger.info(
        "incremental_summary: by_channel=%s by_type=%s posted=%d failed=%d elapsed_ms=%d "
        "checkpoint=%s",
        json.dumps(by_channel),
        json.dumps(by_type),
        total_posted,
        total_failed,
        elapsed_ms,
        cp_path,
    )
    return 0 if total_failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
