#!/usr/bin/env python3
"""Pub/sub smoke test per Linear KEI-75 / bd KEI-101 acceptance.

Publishes to keiracom:tasks:available; subscriber must receive in <5ms.
Returns 0 on pass, 1 on fail. Stdout includes verbatim latency.
"""

from __future__ import annotations

import socket
import sys
import threading
import time

CHANNEL = "keiracom:tasks:available"
RESP_SUB = (
    b"*2\r\n$9\r\nSUBSCRIBE\r\n$"
    + str(len(CHANNEL)).encode()
    + b"\r\n"
    + CHANNEL.encode()
    + b"\r\n"
)
RESP_PUB = (
    b"*3\r\n$7\r\nPUBLISH\r\n$"
    + str(len(CHANNEL)).encode()
    + b"\r\n"
    + CHANNEL.encode()
    + b"\r\n$4\r\nping\r\n"
)


def subscribe(out: dict) -> None:
    with socket.create_connection(("127.0.0.1", 6379), timeout=5) as sock:
        sock.sendall(RESP_SUB)
        sock.recv(1024)
        out["ready_at"] = time.perf_counter_ns()
        out["ready"].set()
        sock.recv(1024)
        out["recv_at"] = time.perf_counter_ns()


def main() -> int:
    state: dict = {"ready": threading.Event()}
    thread = threading.Thread(target=subscribe, args=(state,), daemon=True)
    thread.start()
    if not state["ready"].wait(timeout=2):
        print("FAIL: subscriber never ready", file=sys.stderr)
        return 1
    time.sleep(0.05)
    with socket.create_connection(("127.0.0.1", 6379), timeout=2) as sock:
        send_at = time.perf_counter_ns()
        sock.sendall(RESP_PUB)
        sock.recv(64)
    thread.join(timeout=2)
    latency_us = (state["recv_at"] - send_at) // 1000
    print(f"channel={CHANNEL} publish_to_receive_us={latency_us}")
    return 0 if latency_us < 5000 else 1


if __name__ == "__main__":
    sys.exit(main())
