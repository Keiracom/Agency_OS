#!/usr/bin/env python3
"""
tg_marker_wrapper.py — stream a tmux pane via FIFO, detect [TG] markers,
write outbox JSON for the relay watcher to forward to Telegram.

Usage:
    python tg_marker_wrapper.py --callsign ELLIOT --tmux-session main \
        [--tmux-window 0] [--tmux-pane 0]
"""

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# ANSI escape code stripper
# ---------------------------------------------------------------------------
ANSI_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


# ---------------------------------------------------------------------------
# Outbox writer
# ---------------------------------------------------------------------------
def write_outbox(outbox_dir: Path, text: str, chat_id: str) -> None:
    text = text.strip()
    if not text:
        return
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    uid = uuid.uuid4().hex[:8]
    filename = outbox_dir / f"{ts}_{uid}.json"
    payload = {"text": text, "chat_id": chat_id}
    tmp = filename.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload))
    tmp.rename(filename)
    print(f"[tg_marker_wrapper] wrote {filename.name}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Line parser — yields complete messages as strings
# ---------------------------------------------------------------------------
class MarkerParser:
    def __init__(self):
        self._in_block = False
        self._buf: list[str] = []

    def feed(self, raw_line: str):
        """Feed one raw line; returns a message string or None."""
        line = strip_ansi(raw_line).rstrip("\r\n")

        if self._in_block:
            if line.strip() == "[/TG]":
                msg = "\n".join(self._buf)
                self._buf = []
                self._in_block = False
                return msg
            self._buf.append(line)
            return None

        # Single-line marker: [TG] some text (must have non-whitespace content)
        m = re.match(r"^\[TG\]\s+(\S.*)", line)
        if m:
            return m.group(1).strip()

        # Block-open marker: [TG] alone on a line
        if line.strip() == "[TG]":
            self._in_block = True
            self._buf = []
            return None

        return None


# ---------------------------------------------------------------------------
# FIFO + pipe-pane setup
# ---------------------------------------------------------------------------
def make_fifo(tmp_dir: str, callsign: str) -> str:
    fifo_path = os.path.join(tmp_dir, f"tg_pipe_{callsign}.fifo")
    if os.path.exists(fifo_path):
        os.remove(fifo_path)
    os.mkfifo(fifo_path)
    return fifo_path


def attach_pipe_pane(session: str, window: str, pane: str, fifo: str) -> None:
    target = f"{session}:{window}.{pane}"
    # Disable any existing pipe first
    subprocess.run(["tmux", "pipe-pane", "-t", target], check=False)
    # Attach new pipe — cat writes to FIFO
    subprocess.run(
        ["tmux", "pipe-pane", "-o", "-t", target, f"cat >> {fifo}"],
        check=True,
    )
    print(f"[tg_marker_wrapper] pipe-pane attached to {target} -> {fifo}", file=sys.stderr)


def detach_pipe_pane(session: str, window: str, pane: str) -> None:
    target = f"{session}:{window}.{pane}"
    subprocess.run(["tmux", "pipe-pane", "-t", target], check=False)
    print(f"[tg_marker_wrapper] pipe-pane detached from {target}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="Forward [TG]-marked tmux output to Telegram outbox")
    ap.add_argument("--callsign", required=True, help="Bot callsign (e.g. ELLIOT)")
    ap.add_argument("--tmux-session", required=True, help="tmux session name")
    ap.add_argument("--tmux-window", default="0", help="tmux window index/name (default: 0)")
    ap.add_argument("--tmux-pane", default="0", help="tmux pane index (default: 0)")
    ap.add_argument("--chat-id", default="-1003926592540", help="Telegram chat_id")
    args = ap.parse_args()

    callsign = args.callsign.lower()
    outbox_dir = Path(f"/tmp/telegram-relay-{callsign}/outbox")
    outbox_dir.mkdir(parents=True, exist_ok=True)

    tmp_dir = tempfile.mkdtemp(prefix="tg_marker_")
    fifo = make_fifo(tmp_dir, callsign)

    shutdown = {"requested": False}

    def handle_signal(signum, frame):
        print(f"[tg_marker_wrapper] caught signal {signum}, shutting down", file=sys.stderr)
        shutdown["requested"] = True

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    attach_pipe_pane(args.tmux_session, args.tmux_window, args.tmux_pane, fifo)

    parser = MarkerParser()
    try:
        with open(fifo, "r", errors="replace") as fh:
            while not shutdown["requested"]:
                line = fh.readline()
                if not line:
                    # EOF — pipe closed (tmux session ended)
                    print("[tg_marker_wrapper] FIFO EOF, exiting", file=sys.stderr)
                    break
                msg = parser.feed(line)
                if msg:
                    write_outbox(outbox_dir, msg, args.chat_id)
    finally:
        detach_pipe_pane(args.tmux_session, args.tmux_window, args.tmux_pane)
        try:
            os.remove(fifo)
            os.rmdir(tmp_dir)
        except OSError:
            pass
        print("[tg_marker_wrapper] clean exit", file=sys.stderr)


if __name__ == "__main__":
    main()
