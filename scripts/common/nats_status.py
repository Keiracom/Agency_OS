"""nats_status.py — shared agent-status NATS publisher (KEI-221c).

Replaces per-agent Slack tmux-send [READY:callsign] emission with a NATS
publish to subject `keiracom.agent.status.<callsign>`. The Slack emit stays
in place during cutover (caller decides — this module never touches Slack).

Gating:
  is_v2(callsign) returns True iff BOTH
    FLEET_SUPERVISOR_V2_ENABLED env is truthy AND
    AGENT_ROUTING_<CALLSIGN> env is "v2".
  publish_state() short-circuits and returns False when is_v2(callsign) is
  False — the cutover-safe path leaves all current Slack signalling intact
  for agents that haven't been opted into v2.

Fail-open everywhere — NATS unavailable, nats-py uninstalled, malformed
NATS_URL must NEVER raise. Status emission is non-critical; the agent must
keep running.

CLI usage (callable from bash hooks like emit_ready_marker.sh):
    python3 -m scripts.common.nats_status <callsign> <state>
Exit 0 on success / no-op (gate off / NATS unreachable / nats-py missing).
Non-zero only on bad arguments.

Same source-of-truth pattern as scripts/fleet_supervisor.py:_is_v2() /
_supervisor_v2_enabled() (KEI-221a) — env reads happen at call time, never
import time, so install/test env writes always take effect.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time

log = logging.getLogger(__name__)

FLEET_SUPERVISOR_V2_ENV = "FLEET_SUPERVISOR_V2_ENABLED"
NATS_URL_ENV = "NATS_URL"
DEFAULT_NATS_URL = "nats://127.0.0.1:4222"
NATS_CONNECT_TIMEOUT_SECONDS = 2.0
_TRUTHY = frozenset({"1", "true", "yes", "on"})


def supervisor_v2_enabled() -> bool:
    """True iff FLEET_SUPERVISOR_V2_ENABLED env is set truthy."""
    return os.environ.get(FLEET_SUPERVISOR_V2_ENV, "").strip().lower() in _TRUTHY


def agent_routing(callsign: str) -> str:
    """Return 'v2' if AGENT_ROUTING_<CALLSIGN> opts that agent in, else 'v1'."""
    return os.environ.get(f"AGENT_ROUTING_{callsign.upper()}", "v1")


def is_v2(callsign: str) -> bool:
    """True when both global flag and per-agent routing are set to v2."""
    return supervisor_v2_enabled() and agent_routing(callsign) == "v2"


def publish_state(callsign: str, state: str) -> bool:
    """Publish {state, ts} to NATS subject keiracom.agent.status.<callsign>.

    Returns True if the publish succeeded, False if gate is off, nats-py
    is missing, or the publish failed (caller can decide whether to fall
    back to Slack — though current cutover policy is dual-write).
    """
    if not is_v2(callsign):
        return False
    try:
        import asyncio  # noqa: PLC0415 — lazy import inside try

        import nats.aio.client as nats_client  # noqa: PLC0415 — nats-py optional on v1 path

        payload = json.dumps({"state": state, "ts": int(time.time())}).encode()
        subject = f"keiracom.agent.status.{callsign}"
        url = os.environ.get(NATS_URL_ENV, DEFAULT_NATS_URL)

        async def _publish() -> None:
            nc = nats_client.Client()
            await nc.connect(url, connect_timeout=NATS_CONNECT_TIMEOUT_SECONDS)
            try:
                await nc.publish(subject, payload)
                await nc.flush()
            finally:
                await nc.close()

        asyncio.run(_publish())
        log.debug("[%s] NATS PUBLISH %s → %s", callsign, subject, state)
    except Exception as exc:  # noqa: BLE001 — fail-open by contract
        log.warning("[%s] NATS publish failed (non-fatal): %s", callsign, exc)
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        print("usage: nats_status.py <callsign> <state>", file=sys.stderr)
        return 2
    callsign, state = args
    publish_state(callsign.strip().lower(), state.strip().lower())
    return 0


if __name__ == "__main__":
    sys.exit(main())
