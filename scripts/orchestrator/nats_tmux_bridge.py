#!/usr/bin/env python3
"""nats_tmux_bridge.py — generic NATS-to-tmux subscriber for any callsign.

Subscribes to one or more NATS subjects and writes incoming messages to the
callsign's inbox dir. The corresponding inbox-watcher injects them into the
tmux pane.

Mirrors nats_to_inbox_bridge.py (elliot-specific) but parameterised. Used by:
- worker dispatch bridges (atlas, orion, scout, nova) — subscribe to keiracom.dispatch.<self>
- reviewer bridges (aiden, max) — subscribe to keiracom.review.> + keiracom.deliberation.>
- the elliot inbox bridge still uses the dedicated script for backward compat

Args:
    --callsign CS         : which agent (used for inbox dir + durable consumer name)
    --subject SUBJ        : NATS subject pattern (repeatable for multiple)
    --inbox-dir DIR       : override default /tmp/telegram-relay-<callsign>/inbox

Envelope expected (typed per KEI-205): {from, to, kind, task_id?, summary, ts}
Output JSON written to inbox dir: {channel:"nats:<subject>", sender, text, ts, raw_envelope}
"""
from __future__ import annotations
import argparse
import asyncio
import json
import logging
import os
import signal
import sys
import time
import uuid
from pathlib import Path

import nats
from nats.errors import TimeoutError as NatsTimeoutError

NATS_URL = os.environ.get("NATS_URL", "nats://127.0.0.1:4222")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("nats_tmux_bridge")


def write_inbox_file(envelope: dict, subject: str, inbox_dir: Path) -> Path:
    inbox_dir.mkdir(parents=True, exist_ok=True)
    sender = envelope.get("from") or envelope.get("sender") or "nats"
    text = envelope.get("summary") or envelope.get("text") or json.dumps(envelope, default=str)[:1500]
    payload = {
        "channel": f"nats:{subject}",
        "sender": sender,
        "sender_name": sender,
        "text": text,
        "ts": envelope.get("ts") or time.time(),
        "raw_envelope": envelope,
    }
    fname = f"nats_{int(time.time())}_{uuid.uuid4().hex[:8]}.json"
    path = inbox_dir / fname
    path.write_text(json.dumps(payload))
    return path


def make_handler(subject: str, inbox_dir: Path):
    async def handler(msg):
        try:
            data = msg.data.decode()
            try:
                envelope = json.loads(data)
                if not isinstance(envelope, dict):
                    envelope = {"text": data}
            except json.JSONDecodeError:
                envelope = {"text": data}
            path = write_inbox_file(envelope, msg.subject or subject, inbox_dir)
            log.info("inbox <- subj=%s ts=%s file=%s", msg.subject, envelope.get("ts","?"), path.name)
            try:
                await msg.ack()
            except Exception:
                pass
        except Exception as e:
            log.exception("handler failed: %s", e)
    return handler


async def main_async(callsign: str, subjects: list[str], inbox_dir: Path) -> int:
    log.info("connecting %s; callsign=%s; subjects=%s; inbox=%s", NATS_URL, callsign, subjects, inbox_dir)
    nc = await nats.connect(NATS_URL, connect_timeout=10, max_reconnect_attempts=-1)
    js = nc.jetstream()
    subs = []
    for subject in subjects:
        durable = f"{callsign}-bridge-{subject.replace('.','_').replace('>','star').replace('*','star')}"[:60]
        try:
            sub = await js.subscribe(subject, durable=durable, manual_ack=True)
            subs.append((subject, sub))
            log.info("subscribed subj=%s durable=%s", subject, durable)
        except Exception as e:
            log.exception("subscribe failed for %s: %s", subject, e)
    if not subs:
        await nc.close()
        return 2
    stop = asyncio.Event()
    def _shutdown(*_):
        log.info("signal — shutdown")
        stop.set()
    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)
    # Round-robin poll across all subscriptions
    while not stop.is_set():
        any_progress = False
        for subject, sub in subs:
            try:
                msg = await asyncio.wait_for(sub.next_msg(timeout=2), timeout=3)
                await make_handler(subject, inbox_dir)(msg)
                any_progress = True
            except (asyncio.TimeoutError, NatsTimeoutError):
                pass
            except Exception as e:
                log.exception("poll error subj=%s: %s", subject, e)
                await asyncio.sleep(1)
        if not any_progress:
            await asyncio.sleep(0.2)
    await nc.close()
    log.info("bridge exiting cleanly")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--callsign", required=True)
    p.add_argument("--subject", action="append", required=True, help="repeat for multiple subjects")
    p.add_argument("--inbox-dir", default=None)
    args = p.parse_args()
    inbox_dir = Path(args.inbox_dir) if args.inbox_dir else Path(f"/tmp/telegram-relay-{args.callsign}/inbox")
    return asyncio.run(main_async(args.callsign, args.subject, inbox_dir))


if __name__ == "__main__":
    sys.exit(main())
