"""client.py — Temporal gRPC client wrapper for Keiracom.

Phase A6 build per bd Agency_OS-(A6).

CANONICAL KEY ANCHOR — ceo:dave_decisions_2026_05_26.decision_5_temporal_ephemeral_instance
(2026-05-25, Option C ratified):
  - NEW Vultr Sydney vc2-2c-4gb instance, self-host (Cloud ruled out)
  - 4GB RAM operable for V1 single-worker scope
  - UFW :7233 ALLOW from fleet host only

CANONICAL KEY ANCHOR — ceo:keiracom_architecture_v2_locked Cat 5 (verbatim):
  - temp.middleware (RATIFIED-CEO) — single chokepoint between chat input and
    LLM token call
  - temp.dispatcher (RATIFIED-CEO) — Temporal as workflow execution engine for
    dispatcher (replaces NATS-loop/tmux-pane-injection per v1_completion_criteria
    criterion 1; ephemeral scoping PR #1140)

This module exposes a minimal connection client. Worker registration + workflow
definitions land in sibling modules once Elliot's temp.contract_doc ratifies
(per Cat 5 row 100 LOOSE blocker — see deep dive layer_05_orchestration.md).

USAGE:
    from keiracom_system.temporal import from_env
    client = await from_env()
    # client is a temporalio.client.Client — ready for start_workflow / signal / etc.
"""

from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)

DEFAULT_NAMESPACE = "default"
DEFAULT_TASK_QUEUE = "keiracom-default"


class TemporalConnectError(RuntimeError):
    """Raised when the Temporal gRPC connect fails (transport, auth, namespace)."""


async def connect(addr: str, namespace: str = DEFAULT_NAMESPACE):
    """Connect to Temporal at addr (e.g. '45.76.114.137:7233').

    Lazy-imports temporalio so the module is collectable on hosts without
    the SDK installed (matches Vault decryptor pattern from PR #1146 — lets
    the package import without throwing on import-time dependency miss).
    """
    try:
        from temporalio.client import Client
    except ImportError as exc:
        raise TemporalConnectError(
            f"temporalio SDK not installed; `pip install temporalio` first ({exc})"
        ) from exc
    try:
        return await Client.connect(addr, namespace=namespace)
    except Exception as exc:
        raise TemporalConnectError(
            f"failed to connect to Temporal at {addr!r} (namespace {namespace!r}): {exc}"
        ) from exc


async def from_env():
    """Construct a Temporal client from TEMPORAL_ADDR + TEMPORAL_NAMESPACE env.

    TEMPORAL_ADDR is required. TEMPORAL_NAMESPACE defaults to 'default'.
    Raises EnvironmentError if TEMPORAL_ADDR absent.
    """
    addr = os.environ.get("TEMPORAL_ADDR")
    if not addr:
        raise OSError(
            "from_env(): TEMPORAL_ADDR env required "
            "(e.g. 45.76.114.137:7233 for prod, 127.0.0.1:7233 for dev)"
        )
    namespace = os.environ.get("TEMPORAL_NAMESPACE", DEFAULT_NAMESPACE)
    return await connect(addr, namespace=namespace)
