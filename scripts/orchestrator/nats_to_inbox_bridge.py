#!/usr/bin/env python3
"""nats_to_inbox_bridge.py — Subscribe to keiracom.elliot.inbox, drain into elliot's inbox dir.

NATS is the agent-to-agent whiteboard. This bridge fans the elliot-addressed
subject (keiracom.elliot.inbox) into the file-based inbox the existing
elliot-inbox-watcher.service already reads. The watcher then injects each
message into the elliottbot tmux pane the same way Slack #ceo posts arrive.

Net effect:
  - Other agents publish to keiracom.elliot.inbox via NATS
  - This bridge writes a JSON file per message into /tmp/telegram-relay-elliot/inbox/
  - The existing watcher injects [<sender>@nats:elliot.inbox] <text> into my pane

Envelope expected on the NATS subject (typed envelope per KEI-205 design):
    {from, to, kind, task_id?, summary, ts}
We map: sender=from, text=summary (fallback to JSON-dumped body), channel="nats:elliot.inbox".

Idempotency: each NATS message is dropped to a uniquely-named JSON file,
the watcher moves processed files into processed/. No dedup is needed.

Resilience: subscribe with a durable consumer so messages published while
the bridge is offline are replayed on restart.
"""
from __future__ import annotations
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
SUBJECT = os.environ.get("ELLIOT_INBOX_SUBJECT", "keiracom.elliot.inbox")
INBOX_DIR = Path(os.environ.get("ELLIOT_INBOX_DIR", "/tmp/telegram-relay-elliot/inbox"))
DURABLE_NAME = os.environ.get("ELLIOT_INBOX_DURABLE", "elliot-inbox-bridge")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("nats_to_inbox_bridge")


def write_inbox_file(envelope: dict) -> Path:
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    sender = envelope.get("from") or envelope.get("sender") or "nats"
    text = envelope.get("summary") or envelope.get("text") or json.dumps(envelope, default=str)[:1500]
    payload = {
        "channel": "nats:elliot.inbox",
        "sender": sender,
        "sender_name": sender,
        "text": text,
        "ts": envelope.get("ts") or time.time(),
        "raw_envelope": envelope,
    }
    fname = f"nats_{int(time.time())}_{uuid.uuid4().hex[:8]}.json"
    path = INBOX_DIR / fname
    path.write_text(json.dumps(payload))
    return path


async def message_handler(msg):
    try:
        data = msg.data.decode()
        try:
            envelope = json.loads(data)
            if not isinstance(envelope, dict):
                envelope = {"text": data}
        except json.JSONDecodeError:
            envelope = {"text": data}
        path = write_inbox_file(envelope)
        log.info("inbox <- nats subject=%s ts=%s file=%s", msg.subject, envelope.get("ts","?"), path.name)
        await msg.ack()
    except Exception as e:
        log.exception("message_handler failed: %s", e)


async def main() -> int:
    log.info("connecting to %s, subscribing %s", NATS_URL, SUBJECT)
    nc = await nats.connect(NATS_URL, connect_timeout=10, max_reconnect_attempts=-1)
    js = nc.jetstream()
    # Durable pull subscription on the elliot_inbox stream
    try:
        sub = await js.subscribe(SUBJECT, durable=DURABLE_NAME, manual_ack=True)
    except Exception as e:
        log.exception("subscribe failed: %s", e)
        await nc.close()
        return 2
    log.info("subscribed; awaiting messages")
    stop = asyncio.Event()
    def _shutdown(*_):
        log.info("signal received — shutdown")
        stop.set()
    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)
    while not stop.is_set():
        try:
            msg = await asyncio.wait_for(sub.next_msg(timeout=10), timeout=15)
            await message_handler(msg)
        except (asyncio.TimeoutError, NatsTimeoutError):
            continue
        except Exception as e:
            log.exception("fetch loop error: %s", e)
            await asyncio.sleep(2)
    await nc.close()
    log.info("bridge exiting cleanly")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
