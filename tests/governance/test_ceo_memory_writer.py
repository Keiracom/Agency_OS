"""Tests for src/governance/ceo_memory_writer.py — KEI-87.

Mocks psycopg.connect via a minimal fake. Verifies the wrapper's
SQL emission order (SET LOCAL agency_os.callsign first, then the
INSERT/UPDATE) — the trigger from the matching migration depends on
the session var being set in the same transaction before the write.

Trigger semantics themselves are covered by the migration's own
acceptance probe (live Supabase test post-deploy); these tests cover
the wrapper contract.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from src.governance import ceo_memory_writer


class _Cursor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple | None]] = []
        self.rowcount = 1

    def execute(self, sql: str, params: tuple | None = None) -> None:
        self.executed.append((sql, params))

    def __enter__(self) -> _Cursor:
        return self

    def __exit__(self, *a: Any) -> None:
        return None


class _Conn:
    def __init__(self) -> None:
        self.cur = _Cursor()
        self.commits = 0

    def cursor(self) -> _Cursor:
        return self.cur

    def commit(self) -> None:
        self.commits += 1

    def __enter__(self) -> _Conn:
        return self

    def __exit__(self, *a: Any) -> None:
        return None


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/x")


def test_upsert_sets_local_callsign_before_write() -> None:
    conn = _Conn()
    with patch("psycopg.connect", return_value=conn):
        ceo_memory_writer.upsert_ceo_memory_key("elliot", "ceo:phase_lock", {"v": 1})
    sqls = [s for s, _ in conn.cur.executed]
    assert "SET LOCAL agency_os.callsign" in sqls[0]
    assert conn.cur.executed[0][1] == ("elliot",)
    assert "INSERT INTO public.ceo_memory" in sqls[1]
    assert conn.commits == 1


def test_update_sets_local_callsign_then_update() -> None:
    conn = _Conn()
    with patch("psycopg.connect", return_value=conn):
        ceo_memory_writer.update_ceo_memory_value("dave", "ceo:phase_lock", {"v": 2})
    sqls = [s for s, _ in conn.cur.executed]
    assert "SET LOCAL agency_os.callsign" in sqls[0]
    assert conn.cur.executed[0][1] == ("dave",)
    assert "UPDATE public.ceo_memory" in sqls[1]
    assert conn.commits == 1


def test_update_missing_row_raises_key_error() -> None:
    conn = _Conn()
    conn.cur.rowcount = 0
    with patch("psycopg.connect", return_value=conn), pytest.raises(KeyError):
        ceo_memory_writer.update_ceo_memory_value("max", "ceo:phase_lock", {"v": 3})


def test_callsign_required() -> None:
    with pytest.raises(ValueError):
        ceo_memory_writer.upsert_ceo_memory_key("", "ceo:phase_lock", {"v": 4})
    with pytest.raises(ValueError):
        ceo_memory_writer.update_ceo_memory_value("   ", "ceo:phase_lock", {"v": 5})


def test_dsn_falls_back_to_supabase_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://fallback/x")
    assert ceo_memory_writer._dsn() == "postgresql://fallback/x"


class _RaisingCursor(_Cursor):
    """Cursor that raises CheckViolation on the second execute (the UPDATE/INSERT)
    to simulate the trigger refusing the write — KEI-87 negative-path proof."""

    def __init__(self, exc: BaseException) -> None:
        super().__init__()
        self._exc = exc
        self._call = 0

    def execute(self, sql: str, params: tuple | None = None) -> None:
        super().execute(sql, params)
        self._call += 1
        if self._call >= 2:
            raise self._exc


class _RaisingConn(_Conn):
    def __init__(self, exc: BaseException) -> None:
        super().__init__()
        self.cur = _RaisingCursor(exc)


def test_upsert_propagates_trigger_check_violation() -> None:
    """Wrapper passes through the CheckViolation when the trigger refuses.
    Simulates SET LOCAL agency_os.callsign='aiden' → trigger RAISES on ceo:*.
    """
    import psycopg

    conn = _RaisingConn(
        psycopg.errors.CheckViolation("KEI-87 ceo_memory write-guard: aiden not in (elliot, dave)")
    )
    with patch("psycopg.connect", return_value=conn):
        with pytest.raises(psycopg.errors.CheckViolation):
            ceo_memory_writer.upsert_ceo_memory_key("aiden", "ceo:phase_lock", {"v": 1})
    # SET LOCAL still executed; the exception happens on the INSERT (call 2)
    assert any("SET LOCAL agency_os.callsign" in s for s, _ in conn.cur.executed)


def test_update_propagates_trigger_check_violation() -> None:
    """Same negative-path proof on update_ceo_memory_value."""
    import psycopg

    conn = _RaisingConn(psycopg.errors.CheckViolation("refused"))
    with patch("psycopg.connect", return_value=conn):
        with pytest.raises(psycopg.errors.CheckViolation):
            ceo_memory_writer.update_ceo_memory_value("max", "ceo:phase_lock", {"v": 2})


def test_upsert_uses_prepare_threshold_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """psycopg.connect called with prepare_threshold=None per pgbouncer pin."""
    captured: dict[str, Any] = {}

    def _fake_connect(dsn: str, **kwargs: Any) -> _Conn:
        captured["kwargs"] = kwargs
        return _Conn()

    monkeypatch.setattr("psycopg.connect", _fake_connect)
    ceo_memory_writer.upsert_ceo_memory_key("elliot", "ceo:phase_lock", {"v": 99})
    assert captured["kwargs"].get("prepare_threshold") is None


# ---------------------------------------------------------------------------
# KEI-87 follow-up migration — per-call-site monkeypatch tests
# ---------------------------------------------------------------------------


def test_heartbeat_tick_calls_upsert_ceo_memory_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """heartbeat.tick() routes ceo_memory write via upsert_ceo_memory_key."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
    from observability import heartbeat as hb  # noqa: PLC0415

    calls: list[tuple] = []

    def _fake_upsert(cs: str, key: str, value: Any) -> None:
        calls.append((cs, key, value))

    monkeypatch.setattr(hb, "upsert_ceo_memory_key", _fake_upsert)
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/d")
    monkeypatch.setenv("CALLSIGN", "max")

    # Patch psycopg.connect so _read_previous returns None (no prior state).
    # _read_previous uses conn.cursor() as ctx-mgr + cur.execute + cur.fetchone.
    class _HeartbeatCursor(_Cursor):
        def fetchone(self):  # noqa: ANN201
            return None  # No prior heartbeat state

    class _HeartbeatConn(_Conn):
        def cursor(self) -> _HeartbeatCursor:  # type: ignore[override]
            return _HeartbeatCursor()

    monkeypatch.setattr("psycopg.connect", lambda *a, **k: _HeartbeatConn())

    hb.tick("test-service", outcome_increment=3, status="ok")

    assert len(calls) == 1
    cs, key, value = calls[0]
    assert cs == "max"
    assert key == "heartbeat:test-service"
    assert value["last_outcome_counter_value"] == 3
    assert value["last_status"] == "ok"

    # Negative-path: no raw psycopg INSERT in heartbeat source
    import re

    src = Path(__file__).resolve().parents[2] / "src" / "observability" / "heartbeat.py"
    text = src.read_text()
    assert not re.search(r"INSERT\s+INTO\s+(public\.)?ceo_memory", text), (
        "heartbeat.py still contains a direct ceo_memory INSERT"
    )


def test_completion_sync_worker_sink_calls_upsert(monkeypatch: pytest.MonkeyPatch) -> None:
    """_sink_ceo_memory routes via upsert_ceo_memory_key."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "orchestrator"))
    import importlib

    # completion_sync_worker imports _heartbeat_shim at module level; stub it
    monkeypatch.setitem(sys.modules, "_heartbeat_shim", type(sys)("_heartbeat_shim"))
    sys.modules["_heartbeat_shim"].heartbeat_tick = lambda *a, **k: None  # type: ignore[attr-defined]

    csw = importlib.import_module("completion_sync_worker")

    calls: list[tuple] = []

    def _fake_upsert(cs: str, key: str, value: Any) -> None:
        calls.append((cs, key, value))

    monkeypatch.setattr(csw, "upsert_ceo_memory_key", _fake_upsert)
    monkeypatch.setenv("CALLSIGN", "system")

    csw._sink_ceo_memory("KEI-58", "done")

    assert len(calls) == 1
    cs, key, value = calls[0]
    assert key == "completion:KEI-58"
    assert value["status"] == "done"
    assert value["via"] == "kei74"

    # Negative-path: no raw INSERT in completion_sync_worker source
    import re

    src = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "orchestrator"
        / "completion_sync_worker.py"
    )
    text = src.read_text()
    assert not re.search(r"INSERT\s+INTO\s+(public\.)?ceo_memory", text), (
        "completion_sync_worker.py still contains a direct ceo_memory INSERT"
    )


def test_cis_outcome_service_calls_upsert(monkeypatch: pytest.MonkeyPatch) -> None:
    """save_propensity_weights delegates to upsert_ceo_memory_key."""
    import asyncio
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

    # Patch heavy deps before importing the service
    import types

    for mod in ("sqlalchemy", "sqlalchemy.orm", "sqlalchemy.ext.asyncio"):
        if mod not in sys.modules:
            monkeypatch.setitem(sys.modules, mod, types.ModuleType(mod))

    # Ensure the service can import without real DB
    import src.services.cis_outcome_service as cos  # noqa: PLC0415

    calls: list[tuple] = []

    def _fake_upsert(cs: str, key: str, value: Any) -> None:
        calls.append((cs, key, value))

    monkeypatch.setattr(cos, "upsert_ceo_memory_key", _fake_upsert)
    monkeypatch.setenv("CALLSIGN", "system")

    result = asyncio.run(cos.save_propensity_weights(db=None, weights={"tier_a": 0.7}))

    assert result["success"] is True
    assert len(calls) == 1
    cs, key, value = calls[0]
    assert key == "ceo:propensity_weights_v3"
    assert value == {"tier_a": 0.7}

    # Negative-path: no raw INSERT in cis_outcome_service source
    import re

    src = Path(__file__).resolve().parents[2] / "src" / "services" / "cis_outcome_service.py"
    text = src.read_text()
    assert not re.search(r"INSERT\s+INTO\s+(public\.)?ceo_memory", text), (
        "cis_outcome_service.py still contains a direct ceo_memory INSERT"
    )


def test_session_end_hook_calls_upsert(monkeypatch: pytest.MonkeyPatch) -> None:
    """write_memory() routes ceo_memory write via upsert_ceo_memory_key."""
    import importlib.util
    import sys
    from pathlib import Path

    script = Path(__file__).resolve().parents[2] / "scripts" / "session_end_hook.py"
    spec = importlib.util.spec_from_file_location("session_end_hook_test", script)
    hook = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec.loader is not None
    sys.modules["session_end_hook_test"] = hook
    spec.loader.exec_module(hook)  # type: ignore[attr-defined]

    calls: list[tuple] = []

    def _fake_upsert(cs: str, key: str, value: Any) -> None:
        calls.append((cs, key, value))

    monkeypatch.setattr(hook, "upsert_ceo_memory_key", _fake_upsert)
    monkeypatch.setenv("CALLSIGN", "elliot")
    # No DSN so agent_memories branch skips
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)

    summary = {"reason": "exit", "manual_mirror": {"changed": False, "mirror_invoked": False}}
    result = hook.write_memory(summary)

    assert result["ceo_memory_upserted"] is True
    assert len(calls) == 1
    cs, key, _ = calls[0]
    assert cs == "elliot"
    assert key.startswith("ceo:session_end_")

    # Negative-path: no raw INSERT in session_end_hook source
    import re

    src = Path(__file__).resolve().parents[2] / "scripts" / "session_end_hook.py"
    text = src.read_text()
    assert not re.search(r"INSERT\s+INTO\s+(public\.)?ceo_memory", text), (
        "session_end_hook.py still contains a direct ceo_memory INSERT"
    )


# ---------------------------------------------------------------------------
# Repo-wide enforcement: zero direct ceo_memory INSERTs outside the wrapper
# ---------------------------------------------------------------------------


def test_zero_direct_ceo_memory_inserts_in_repo() -> None:
    """The repo-wide negative-path enforcer.

    Scans scripts/ and src/ for raw 'INSERT INTO ceo_memory' or
    'INSERT INTO public.ceo_memory'. Must be zero matches, excluding:
      - src/governance/ceo_memory_writer.py (the wrapper itself)
      - src/bot_common/enforcer_deterministic.py (regex-pattern matcher)

    This is the acceptance criterion for KEI-87 follow-up: all 13 call-sites
    migrated to upsert_ceo_memory_key.
    """
    import re
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    pattern = re.compile(r"INSERT\s+INTO\s+(public\.)?ceo_memory", re.IGNORECASE)
    excluded = {
        repo_root / "src" / "governance" / "ceo_memory_writer.py",
        repo_root / "src" / "bot_common" / "enforcer_deterministic.py",
    }

    violations: list[str] = []
    for path in sorted(repo_root.rglob("*.py")):
        if path in excluded:
            continue
        # Skip tests/, virtual envs, and build artefacts — test assertion
        # strings like `assert "INSERT INTO public.ceo_memory" in sqls[1]`
        # would otherwise trigger false positives.
        if any(
            part in path.parts
            for part in ("tests", ".venv", "venv", "__pycache__", ".git", "node_modules")
        ):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if pattern.search(line):
                violations.append(f"{path.relative_to(repo_root)}:{lineno}: {line.strip()}")

    assert violations == [], (
        "Direct ceo_memory INSERT found outside wrapper — KEI-87 violation:\n"
        + "\n".join(violations)
    )
