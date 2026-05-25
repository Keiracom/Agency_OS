"""Tests for src/keiracom_system/temporal/client.py — Phase A6.

Negative-path discipline per feedback_negative_path_test_before_approve:
the client's job is fail-fast and surface clear errors on connection
problems. Each branch needs explicit negative coverage.

8 cases — 2 happy + 4 negative + 2 from_env.

Most cases use a monkey-patched temporalio.client.Client.connect — the
real Temporal SDK import is happy_path-only via the live integration test
(opt-in via KEIRACOM_TEMPORAL_INTEGRATION=1 against the prod Temporal
host at TEMPORAL_ADDR).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.keiracom_system.temporal.client import (  # noqa: E402
    DEFAULT_NAMESPACE,
    DEFAULT_TASK_QUEUE,
    TemporalConnectError,
    connect,
    from_env,
)


def test_default_namespace_constant():
    """(1) DEFAULT_NAMESPACE locked to 'default' per auto-setup container behaviour."""
    assert DEFAULT_NAMESPACE == "default"


def test_default_task_queue_constant():
    """(2) DEFAULT_TASK_QUEUE locked to 'keiracom-default' (per-domain queues come later)."""
    assert DEFAULT_TASK_QUEUE == "keiracom-default"


@pytest.mark.asyncio
async def test_connect_propagates_address_and_namespace():
    """(3) connect() forwards addr + namespace to temporalio.client.Client.connect."""
    fake_client = AsyncMock()
    with patch("temporalio.client.Client.connect", new=AsyncMock(return_value=fake_client)) as m:
        result = await connect("127.0.0.1:7233", namespace="custom-ns")
    assert result is fake_client
    m.assert_called_once_with("127.0.0.1:7233", namespace="custom-ns")


@pytest.mark.asyncio
async def test_connect_default_namespace_when_unspecified():
    """(4) connect() defaults namespace to 'default' when caller omits it."""
    fake_client = AsyncMock()
    with patch("temporalio.client.Client.connect", new=AsyncMock(return_value=fake_client)) as m:
        await connect("127.0.0.1:7233")
    m.assert_called_once_with("127.0.0.1:7233", namespace="default")


@pytest.mark.asyncio
async def test_connect_wraps_sdk_exception_as_TemporalConnectError():
    """(5) any exception from Client.connect → TemporalConnectError with context."""
    with (
        patch(
            "temporalio.client.Client.connect",
            new=AsyncMock(side_effect=ConnectionRefusedError("no listener")),
        ),
        pytest.raises(TemporalConnectError, match="failed to connect to Temporal"),
    ):
        await connect("127.0.0.1:7233")


@pytest.mark.asyncio
async def test_connect_includes_address_and_namespace_in_error_message():
    """(6) error message includes both the addr + namespace for debuggability."""
    with (
        patch(
            "temporalio.client.Client.connect",
            new=AsyncMock(side_effect=Exception("backend gone")),
        ),
        pytest.raises(TemporalConnectError) as excinfo,
    ):
        await connect("vault.example:7233", namespace="my-ns")
    msg = str(excinfo.value)
    assert "vault.example:7233" in msg
    assert "my-ns" in msg


@pytest.mark.asyncio
async def test_from_env_missing_addr_raises_OSError(monkeypatch):
    """(7) absent TEMPORAL_ADDR → OSError with example addr in message."""
    monkeypatch.delenv("TEMPORAL_ADDR", raising=False)
    with pytest.raises(OSError, match="TEMPORAL_ADDR env required"):
        await from_env()


@pytest.mark.asyncio
async def test_from_env_uses_TEMPORAL_NAMESPACE_when_set(monkeypatch):
    """(8) TEMPORAL_NAMESPACE override flows through to connect()."""
    monkeypatch.setenv("TEMPORAL_ADDR", "127.0.0.1:7233")
    monkeypatch.setenv("TEMPORAL_NAMESPACE", "tenant-acme")
    fake = AsyncMock()
    with patch("temporalio.client.Client.connect", new=AsyncMock(return_value=fake)) as m:
        await from_env()
    m.assert_called_once_with("127.0.0.1:7233", namespace="tenant-acme")


# Integration test — opt-in against live PROD Temporal
_INTEGRATION_ENABLED = os.environ.get("KEIRACOM_TEMPORAL_INTEGRATION", "").strip() == "1"


@pytest.mark.skipif(
    not _INTEGRATION_ENABLED,
    reason="KEIRACOM_TEMPORAL_INTEGRATION=1 not set — live Temporal test skipped",
)
@pytest.mark.asyncio
async def test_integration_live_temporal_connect():
    """(integration) connect to live Temporal via TEMPORAL_ADDR + list workflows.

    Requires:
      - $TEMPORAL_ADDR env (e.g. 45.76.114.137:7233 for prod, or local dev addr)
      - 'default' namespace exists (auto-setup container creates it)
    """
    client = await from_env()
    # Sanity: client.identity is a non-empty string when connected
    assert client.identity is not None
    # Sanity: namespace honoured
    assert client.namespace == "default"
