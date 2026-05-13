#!/usr/bin/env python3
"""ceo_rule_auto_record.py — KEI-22 D7 Slack-relay auto-rule-detect-and-record.

Per Dave CEO directive ts ~1778667300:
    "Every CEO operational directive that establishes a standing rule must
     be recorded in ceo_memory at the time of issue. Key pattern:
     ceo:rule:[rule-name]"

Pattern source: KEI-26 BS-incident → Linear KEI auto-create webhook (PR #815).
This script provides the same shape for ceo_memory rule capture.

Invocation (by Slack relay on every Dave #ceo post):

    python3 scripts/orchestrator/ceo_rule_auto_record.py \
        --channel C0B2PM3TV0B \
        --author dave \
        --slug optional_explicit_slug \
        --body-file /tmp/msg.txt

Filter chain (all must match for the auto-record to fire):
    1. channel == #ceo (C0B2PM3TV0B) — other channels never trigger
    2. author == 'dave' (case-insensitive) — only Dave's posts establish rules
    3. body matches at least one governance trigger phrase

Trigger phrases (matching Dave's verbatim language):
    - 'standing rule'
    - 'effective immediately'
    - 'from now on'
    - 'no exceptions'
    - 'hard stop'
    - 'no build without'           (Dave's pattern for negative rules)
    - 'must be recorded'           (self-referential rule)

Slug resolution (in priority order):
    1. --slug CLI arg (relay-provided, e.g. LLM-extracted)
    2. Body explicit pattern: 'ceo:rule:<slug>' or 'Key: ceo:rule:<slug>'
    3. Heuristic: snake-case the first 5-8 words after the trigger phrase

Output: JSON to stdout with {'fired': bool, 'key': str|null, 'reason': str}.

Best-effort: ceo_memory write failure is logged + returns fired=False, reason=
'write_failed' so the relay can retry on the next dispatch. Exit code 0 either
way (never crashes the relay).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

DEFAULT_LOG = Path("/home/elliotbot/clawd/logs/ceo-rule-auto-record.log")
CEO_CHANNEL_ID = "C0B2PM3TV0B"

_TRIGGER_RE = re.compile(
    r"\bstanding rule\b"
    r"|\beffective immediately\b"
    r"|\bfrom now on\b"
    r"|\bno exceptions\b"
    r"|\bhard stop\b"
    r"|\bno build without\b"
    r"|\bmust be recorded\b",
    re.IGNORECASE,
)

_EXPLICIT_KEY_RE = re.compile(
    r"ceo:rule:([a-z][a-z0-9_]*)",
    re.IGNORECASE,
)


def _log(msg: str, log_path: Path = DEFAULT_LOG) -> None:
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a") as fh:
            fh.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}\n")
    except OSError:
        pass


def _heuristic_slug(body: str) -> str:
    """Snake-case first 5-8 content words after the first trigger phrase."""
    m = _TRIGGER_RE.search(body)
    if not m:
        return "unnamed_rule"
    after = body[m.end() :].strip().lower()
    # Strip common stopwords + punctuation
    tokens: list[str] = []
    stop = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "be",
        "for",
        "of",
        "to",
        "and",
        "or",
        "in",
        "on",
        "this",
        "that",
        "it",
        "as",
        "at",
    }
    for tok in re.split(r"[^\w]+", after):
        if not tok or tok in stop:
            continue
        tokens.append(tok)
        if len(tokens) >= 6:
            break
    return "_".join(tokens) or "unnamed_rule"


def resolve_slug(*, slug_arg: str | None, body: str) -> str:
    """Return the slug to use, in priority: --slug → ceo:rule:<x> in body → heuristic."""
    if slug_arg:
        return re.sub(r"[^a-z0-9_]+", "_", slug_arg.lower()).strip("_") or "unnamed_rule"
    m = _EXPLICIT_KEY_RE.search(body)
    if m:
        return m.group(1).lower()
    return _heuristic_slug(body)


def should_fire(
    *,
    channel: str,
    author: str,
    body: str,
) -> tuple[bool, str]:
    """Return (fire, reason)."""
    if channel != CEO_CHANNEL_ID:
        return False, "wrong_channel"
    if (author or "").strip().lower() != "dave":
        return False, "not_dave"
    if not _TRIGGER_RE.search(body):
        return False, "no_trigger_phrase"
    return True, "governance_trigger_matched"


def record_rule(
    *,
    channel: str,
    author: str,
    body: str,
    slug_arg: str | None = None,
    upsert_fn: Callable[[str, dict[str, Any]], bool] | None = None,
    now_iso: str | None = None,
) -> dict[str, Any]:
    """Pure-Python entry. upsert_fn is injectable for tests."""
    fire, reason = should_fire(channel=channel, author=author, body=body)
    if not fire:
        _log(f"skipped reason={reason} author={author!r} channel={channel!r}")
        return {"fired": False, "key": None, "reason": reason}

    slug = resolve_slug(slug_arg=slug_arg, body=body)
    key = f"ceo:rule:{slug}"
    value = {
        "rule_body": body.strip(),
        "author": author,
        "recorded_at": now_iso or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "channel": channel,
        "source": "kei22_d7_auto_record",
    }

    if upsert_fn is None:
        upsert_fn = _default_upsert_fn

    try:
        ok = upsert_fn(key, value)
    except Exception as exc:
        _log(f"write_failed key={key!r} exc={exc}")
        return {"fired": False, "key": key, "reason": f"write_failed: {exc}"}

    if not ok:
        _log(f"write_returned_false key={key!r}")
        return {"fired": False, "key": key, "reason": "write_failed"}

    _log(f"recorded key={key!r} author={author!r}")
    return {"fired": True, "key": key, "reason": "recorded"}


def _default_upsert_fn(key: str, value: dict[str, Any]) -> bool:
    """Default upsert via Supabase REST. Best-effort; returns False on failure."""
    try:
        from src.evo.supabase_client import sb_post
    except Exception:
        return False
    try:
        sb_post(
            "ceo_memory",
            {"key": key, "value": value},
        )
        return True
    except Exception:
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel", required=True)
    parser.add_argument("--author", required=True)
    parser.add_argument("--slug", default=None)
    parser.add_argument(
        "--body-file",
        type=Path,
        help="Path to a file containing the message body (avoids shell-escaping).",
    )
    parser.add_argument(
        "--body",
        default=None,
        help="Inline message body (alternative to --body-file).",
    )
    args = parser.parse_args(argv)

    body = ""
    if args.body_file:
        try:
            body = args.body_file.read_text()
        except OSError:
            body = ""
    elif args.body:
        body = args.body
    else:
        body = sys.stdin.read() if not sys.stdin.isatty() else ""

    result = record_rule(
        channel=args.channel,
        author=args.author,
        body=body,
        slug_arg=args.slug,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
