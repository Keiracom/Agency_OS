"""KEI-221c — unit tests for scripts/common/nats_status.py.

Cover:
  - is_v2 gating: both flags required
  - publish_state short-circuits (no NATS call) when gate off
  - publish_state attempts publish + handles nats-py missing fail-open
  - main() CLI: bad args → exit 2; good args → exit 0
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.common import nats_status  # noqa: E402

# ---------------------------------------------------------------------------
# Gate composition
# ---------------------------------------------------------------------------


def test_is_v2_false_when_global_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FLEET_SUPERVISOR_V2_ENABLED", raising=False)
    monkeypatch.setenv("AGENT_ROUTING_ORION", "v2")
    assert nats_status.is_v2("orion") is False


def test_is_v2_false_when_agent_routing_v1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FLEET_SUPERVISOR_V2_ENABLED", "1")
    monkeypatch.setenv("AGENT_ROUTING_ORION", "v1")
    assert nats_status.is_v2("orion") is False


def test_is_v2_true_when_both_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FLEET_SUPERVISOR_V2_ENABLED", "1")
    monkeypatch.setenv("AGENT_ROUTING_ORION", "v2")
    assert nats_status.is_v2("orion") is True


@pytest.mark.parametrize("truthy", ["1", "true", "TRUE", "yes", "On"])
def test_supervisor_v2_enabled_truthy_variants(
    monkeypatch: pytest.MonkeyPatch, truthy: str
) -> None:
    monkeypatch.setenv("FLEET_SUPERVISOR_V2_ENABLED", truthy)
    assert nats_status.supervisor_v2_enabled() is True


@pytest.mark.parametrize("falsy", ["", "0", "no", "off", "false"])
def test_supervisor_v2_enabled_falsy_variants(monkeypatch: pytest.MonkeyPatch, falsy: str) -> None:
    monkeypatch.setenv("FLEET_SUPERVISOR_V2_ENABLED", falsy)
    assert nats_status.supervisor_v2_enabled() is False


# ---------------------------------------------------------------------------
# publish_state — short-circuit + fail-open
# ---------------------------------------------------------------------------


def test_publish_state_short_circuits_when_gate_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FLEET_SUPERVISOR_V2_ENABLED", raising=False)

    # Sentinel: if nats import were attempted, this would raise — verifying
    # we never reach the import is the test contract.
    monkeypatch.setitem(sys.modules, "nats.aio.client", None)
    assert nats_status.publish_state("orion", "ready") is False


def test_publish_state_returns_false_when_nats_py_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FLEET_SUPERVISOR_V2_ENABLED", "1")
    monkeypatch.setenv("AGENT_ROUTING_ORION", "v2")
    # Force ImportError on the runtime import inside publish_state.
    monkeypatch.setitem(sys.modules, "nats", None)
    monkeypatch.setitem(sys.modules, "nats.aio", None)
    monkeypatch.setitem(sys.modules, "nats.aio.client", None)
    assert nats_status.publish_state("orion", "ready") is False


def test_publish_state_succeeds_with_mocked_nats(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FLEET_SUPERVISOR_V2_ENABLED", "1")
    monkeypatch.setenv("AGENT_ROUTING_ORION", "v2")

    # Inject a fake nats.aio.client into sys.modules. Client().connect /
    # publish / flush / close are all async coroutines; we record args for
    # assertion. Build the module chain so `import nats.aio.client as ...`
    # resolves cleanly inside publish_state's try block.
    import types

    captured: dict = {}

    class _FakeClient:
        def __init__(self) -> None:
            self.subjects: list[tuple[str, bytes]] = []

        async def connect(self, url: str, connect_timeout: float) -> None:
            captured["url"] = url
            captured["timeout"] = connect_timeout

        async def publish(self, subject: str, payload: bytes) -> None:
            self.subjects.append((subject, payload))
            captured["subject"] = subject
            captured["payload"] = payload

        async def flush(self) -> None:
            captured["flushed"] = True

        async def close(self) -> None:
            captured["closed"] = True

    fake_nats = types.ModuleType("nats")
    fake_aio = types.ModuleType("nats.aio")
    fake_client_mod = types.ModuleType("nats.aio.client")
    fake_client_mod.Client = _FakeClient
    fake_nats.aio = fake_aio
    fake_aio.client = fake_client_mod
    monkeypatch.setitem(sys.modules, "nats", fake_nats)
    monkeypatch.setitem(sys.modules, "nats.aio", fake_aio)
    monkeypatch.setitem(sys.modules, "nats.aio.client", fake_client_mod)

    assert nats_status.publish_state("orion", "ready") is True
    assert captured["subject"] == "keiracom.agent.status.orion"
    assert captured.get("flushed") is True
    assert captured.get("closed") is True
    # Payload must be JSON with state + ts keys.
    import json

    parsed = json.loads(captured["payload"])
    assert parsed["state"] == "ready"
    assert isinstance(parsed["ts"], int)


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------


def test_main_bad_args_returns_2() -> None:
    assert nats_status.main(["only-one-arg"]) == 2
    assert nats_status.main([]) == 2
    assert nats_status.main(["a", "b", "c"]) == 2


def test_main_good_args_returns_0_when_gate_off(monkeypatch: pytest.MonkeyPatch) -> None:
    # Gate off — fail-open exit 0 even though no NATS publish occurs.
    monkeypatch.delenv("FLEET_SUPERVISOR_V2_ENABLED", raising=False)
    assert nats_status.main(["orion", "ready"]) == 0
