"""Tests for scripts/orchestrator/supervisor_wake_publish.py — Agency_OS-Phase-0.

Three required test paths per dispatch:
  (i)  script publishes valid JSON envelope to the correct subject
  (ii) envelope has required fields (from, kind, summary, ts)
  (iii) skip-if-NATS-unavailable for CI portability

Plus housekeeping:
  (iv) --dry-run prints valid JSON to stdout and exits 0 without publishing
  (v)  build_envelope returns the exact constants the dispatch contract specifies

The live-publish test (i) requires a reachable NATS server. Skipped when
NATS_URL env is unset OR connect fails — keeps CI green in environments
without NATS.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts" / "orchestrator"))

import supervisor_wake_publish as swp  # noqa: E402

NATS_URL = os.environ.get("NATS_URL", "nats://127.0.0.1:4222")


def _nats_reachable() -> bool:
    """True if we can connect to NATS within 2s. Used to skip live tests."""
    try:
        import nats
    except ImportError:
        return False

    async def _probe() -> bool:
        try:
            nc = await nats.connect(NATS_URL, connect_timeout=2)
            await nc.close()
            return True
        except Exception:
            return False

    try:
        return asyncio.run(_probe())
    except Exception:
        return False


# (v) Build-envelope unit test — runs everywhere, no NATS needed.
def test_build_envelope_has_required_fields():
    """Path (ii) — envelope must have from, kind, summary, ts."""
    envelope = swp.build_envelope()
    assert envelope["from"] == "supervisor-wake"
    assert envelope["kind"] == "supervise_check"
    assert "[SUPERVISE-WAKE]" in envelope["summary"]
    assert isinstance(envelope["ts"], float)
    assert envelope["ts"] > 0


def test_build_envelope_uses_provided_timestamp():
    """build_envelope respects an injected `now` (deterministic testing)."""
    envelope = swp.build_envelope(now=1234567890.0)
    assert envelope["ts"] == 1234567890.0


def test_envelope_required_fields_set_matches_dispatch_contract():
    """Path (ii) verbose — assert the exact field set the dispatch spec'd."""
    envelope = swp.build_envelope()
    required = {"from", "kind", "summary", "ts"}
    assert required.issubset(envelope.keys()), (
        f"envelope missing required fields: {required - envelope.keys()}"
    )


def test_default_subject_is_canonical_elliot_inbox():
    """Default NATS subject must be the canonical inbound-to-Elliot path.

    Anchored to ceo:comm_architecture canonical key. Prevents a silent
    rename / typo of DEFAULT_SUBJECT from passing all other tests (live
    tests use keiracom.test.*; --dry-run doesn't surface subject). Max's
    quality-lens add 2026-05-24.
    """
    assert swp.DEFAULT_SUBJECT == "keiracom.elliot.inbox"


# (iv) Dry-run CLI smoke — no NATS required.
def test_dry_run_prints_json_and_exits_zero(tmp_path):
    """--dry-run prints valid JSON envelope to stdout, exit 0, no publish."""
    script = REPO_ROOT / "scripts" / "orchestrator" / "supervisor_wake_publish.py"
    result = subprocess.run(
        [sys.executable, str(script), "--dry-run"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, f"--dry-run exit {result.returncode}: {result.stderr}"
    payload = json.loads(result.stdout)
    assert payload["from"] == "supervisor-wake"
    assert payload["kind"] == "supervise_check"


# (i) Live publish test — skip if NATS unreachable (path iii).
@pytest.mark.skipif(
    not _nats_reachable(),
    reason="NATS unreachable at NATS_URL — live publish test skipped (path iii)",
)
def test_publish_wake_emits_envelope_to_subject():
    """Path (i) — publish_wake() to a test subject returns 0 + envelope lands.

    Uses a unique-per-run test subject (keiracom.test.supervisor_wake.<ts>) so
    we don't pollute the real keiracom.elliot.inbox subject during CI. Verify by
    subscribing first, publishing second, then asserting the message arrived.
    """
    import nats

    test_subject = f"keiracom.test.supervisor_wake.{int(time.time())}"
    received: list[bytes] = []

    async def _flow() -> int:
        nc = await nats.connect(NATS_URL, connect_timeout=5)
        sub = await nc.subscribe(test_subject)
        rc = await swp.publish_wake(NATS_URL, test_subject)
        try:
            msg = await asyncio.wait_for(sub.next_msg(timeout=3), timeout=4)
            received.append(msg.data)
        except TimeoutError:
            pass
        await sub.unsubscribe()
        await nc.close()
        return rc

    rc = asyncio.run(_flow())
    assert rc == 0, "publish_wake should return 0 on successful publish"
    assert len(received) == 1, f"expected 1 message, got {len(received)}"
    envelope = json.loads(received[0])
    assert envelope["kind"] == "supervise_check"
    assert envelope["from"] == "supervisor-wake"


# (iii) Skip-if-no-NATS sanity — assert publish_wake fails gracefully.
def test_publish_wake_returns_1_on_bad_url():
    """publish_wake against an unreachable URL must return 1, not raise.

    Exercises the (iii) skip-when-NATS-unavailable contract end-to-end:
    the script's exit-1-fail-fast behaviour is what systemd Restart=on-failure
    keys off (though we use Type=oneshot here, the timer catches the next
    cycle). Use an obviously-dead port to force a connect failure.
    """
    rc = asyncio.run(swp.publish_wake("nats://127.0.0.1:1", "keiracom.test.unreachable"))
    assert rc == 1, "publish_wake should return 1 on connect failure (not raise)"
