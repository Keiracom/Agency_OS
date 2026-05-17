"""KEI-179 — uvicorn entrypoint for the dispatcher service.

Run via ``python3 -m src.dispatcher`` (see systemd unit + install script
for production).
"""

from __future__ import annotations

import logging
import os

import uvicorn

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8090

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    host = os.environ.get("DISPATCHER_HOST", DEFAULT_HOST)
    port = int(os.environ.get("DISPATCHER_PORT", str(DEFAULT_PORT)))
    uvicorn.run("src.dispatcher.app:app", host=host, port=port, log_level="info")
