#!/usr/bin/env python3
"""upload.py — Slack file-upload skill (slack-file-upload).

Usage:
    upload.py <channel> <file_path> [--title=<title>] [--comment=<comment>]

Env:
    SLACK_BOT_TOKEN  (required) — xoxb-... bot token
    CALLSIGN         (optional) — default "elliot"; prefix tag for comment

Exit codes:
    0  success
    1  network / Slack API error
    2  missing token, missing scope, or disallowed channel
    3  file not found or invalid / missing arguments
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Channel map (mirrors slack_relay.py CHANNELS dict — keep in sync)
# ---------------------------------------------------------------------------
CHANNELS: dict[str, str] = {
    "execution": "C0B3QB0K1GQ",
    "ceo": "C0B2PM3TV0B",
    "alerts": "C0B2EJU53EK",
    "completed_directives": "C0B2U15PSEA",
    "ops": "C0B2UCNRJ86",
}


def _resolve_callsign() -> str:
    env_val = os.environ.get("CALLSIGN", "").strip()
    if env_val:
        return env_val.lower()
    identity_path = Path(__file__).resolve().parent.parent.parent / "Agency_OS" / "IDENTITY.md"
    if identity_path.exists():
        match = re.search(
            r"^\s*\*\*?CALLSIGN:?\*\*?\s*([A-Za-z]\w*)",
            identity_path.read_text(),
            re.IGNORECASE | re.MULTILINE,
        )
        if match:
            return match.group(1).lower()
    return "elliot"


def _resolve_channel(raw: str) -> str:
    """Return channel ID. Accept friendly name or raw C... ID."""
    return CHANNELS.get(raw.lstrip("#"), raw)


def _parse_args(argv: list[str]) -> tuple[str, Path, str | None, str | None]:
    """Return (channel_id, file_path, title, comment). Exit 3 on bad args."""
    if len(argv) < 2:
        print(
            "ERROR: usage: upload.py <channel> <file_path> [--title=...] [--comment=...]",
            file=sys.stderr,
        )
        sys.exit(3)

    channel_id = _resolve_channel(argv[0])
    file_path = Path(argv[1])
    title: str | None = None
    comment: str | None = None

    for arg in argv[2:]:
        if arg.startswith("--title="):
            title = arg[len("--title=") :]
        elif arg.startswith("--comment="):
            comment = arg[len("--comment=") :]
        else:
            print(f"ERROR: unknown argument: {arg}", file=sys.stderr)
            sys.exit(3)

    return channel_id, file_path, title, comment


def _prefix_comment(comment: str | None, tag: str) -> str:
    """Prepend [CALLSIGN] tag to comment if not already present."""
    if not comment:
        return tag
    if comment.startswith(tag):
        return comment
    return f"{tag} {comment}"


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    channel_id, file_path, title, comment = _parse_args(argv)

    if not file_path.exists():
        print(f"ERROR: file not found: {file_path}", file=sys.stderr)
        sys.exit(3)

    token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    if not token:
        print("ERROR: SLACK_BOT_TOKEN not set", file=sys.stderr)
        sys.exit(2)

    callsign = _resolve_callsign()
    tag = f"[{callsign.upper()}]"
    initial_comment = _prefix_comment(comment, tag)

    try:
        from slack_sdk.errors import SlackApiError
        from slack_sdk.web import WebClient
    except ImportError:
        print("ERROR: slack_sdk not installed — run: pip install slack-sdk", file=sys.stderr)
        sys.exit(1)

    client = WebClient(token=token)
    try:
        response = client.files_upload_v2(
            channel=channel_id,
            file=str(file_path),
            filename=file_path.name,
            title=title or file_path.name,
            initial_comment=initial_comment,
        )
    except SlackApiError as e:
        error_code = e.response.get("error", "unknown")
        if error_code == "missing_scope":
            print("ERROR: missing_scope — add files:write to bot scopes", file=sys.stderr)
            sys.exit(2)
        print(f"ERROR: Slack API error: {error_code}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: network failure: {e}", file=sys.stderr)
        sys.exit(1)

    file_id = response.get("file", {}).get("id", "unknown")
    print(f"OK: uploaded {file_path.name} to {channel_id} (file_id={file_id})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
