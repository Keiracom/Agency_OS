#!/usr/bin/env python3
"""Initialise the 6 Valkey streams/channels per Linear KEI-75 / bd KEI-101.

Idempotent. Localhost only. No AUTH (network-isolation boundary).
"""

from __future__ import annotations

import socket
import sys


def send(cmd: list[str]) -> str:
    """Send a single RESP command and return decoded reply."""
    parts = [f"*{len(cmd)}\r\n"]
    for arg in cmd:
        parts.append(f"${len(arg)}\r\n{arg}\r\n")
    payload = "".join(parts).encode()
    with socket.create_connection(("127.0.0.1", 6379), timeout=2) as sock:
        sock.sendall(payload)
        return sock.recv(4096).decode(errors="replace").strip()


def main() -> int:
    results: list[tuple[str, str]] = []
    streams = ["orchestration", "deliberation_thread_bootstrap"]
    for stream in streams:
        results.append((f"XADD {stream}", send(["XADD", stream, "*", "bootstrap", "init"])))
    results.append(
        (
            "HSET keiracom:agent:status:bootstrap",
            send(["HSET", "keiracom:agent:status:bootstrap", "init", "1"]),
        )
    )
    pubsub_channels = [
        "keiracom:tasks:available",
        "keiracom:tasks:completed:bootstrap",
        "keiracom:ceo:escalation",
    ]
    for ch in pubsub_channels:
        results.append((f"PUBLISH {ch}", send(["PUBLISH", ch, "init"])))
    for label, reply in results:
        print(f"{label}: {reply}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
