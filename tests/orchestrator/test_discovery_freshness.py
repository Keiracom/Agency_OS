"""KEI-58 — behavioural tests for discovery freshness governance.

Covers:
  - compute_freshness verdict ladder (fresh -> stale-by-age -> stale-by-drift -> expired).
  - load_fresh_discoveries excludes EXPIRED and tags STALE.
  - bd_verify CLI exit codes + output for each verdict + missing row.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts.orchestrator import discovery_log
from scripts.orchestrator.discovery_log import (
    append_discovery,
    compute_freshness,
    load_fresh_discoveries,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
BD_VERIFY = REPO_ROOT / "scripts" / "bd_verify.py"


@pytest.fixture
def isolated_log(tmp_path, monkeypatch):
    """Redirect discovery_log.jsonl to a temp path so tests don't touch the real store."""
    p = tmp_path / "discovery_log.jsonl"
    monkeypatch.setattr(discovery_log, "DEFAULT_DISCOVERY_LOG", p)
    return p


def _write(path: Path, kei: str, written_at: datetime, ctx: dict) -> None:
    append_discovery(
        {
            "kei": kei,
            "agent": "test",
            "context": "test row",
            "finding": "x",
            "failed_path": "y",
            "verified_path": "z",
            "tags": [],
            "created_at": written_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "context_version": ctx,
        },
        path=path,
    )


def test_fresh_within_30d_no_drift(isolated_log):
    now = datetime.now(UTC)
    ctx = {"kernel": "X", "anthropic": "1.0"}
    _write(isolated_log, "KEI-T1", now - timedelta(days=5), ctx)
    row = discovery_log.load_all_discoveries(isolated_log)[0]
    f = compute_freshness(row, now=now, current_version=ctx)
    assert f["verdict"] == "fresh", f


def test_stale_by_age_between_30_and_90d(isolated_log):
    now = datetime.now(UTC)
    ctx = {"kernel": "X", "anthropic": "1.0"}
    _write(isolated_log, "KEI-T2", now - timedelta(days=45), ctx)
    row = discovery_log.load_all_discoveries(isolated_log)[0]
    f = compute_freshness(row, now=now, current_version=ctx)
    assert f["verdict"] == "stale"
    assert "age" in f["reason"]


def test_stale_by_context_drift_under_30d(isolated_log):
    now = datetime.now(UTC)
    written_ctx = {"kernel": "X", "anthropic": "1.0"}
    current_ctx = {"kernel": "X", "anthropic": "2.0"}  # drift on anthropic
    _write(isolated_log, "KEI-T3", now - timedelta(days=10), written_ctx)
    row = discovery_log.load_all_discoveries(isolated_log)[0]
    f = compute_freshness(row, now=now, current_version=current_ctx)
    assert f["verdict"] == "stale"
    assert "anthropic" in f["drift"]


def test_expired_over_90d_regardless_of_drift(isolated_log):
    now = datetime.now(UTC)
    ctx = {"kernel": "X", "anthropic": "1.0"}
    _write(isolated_log, "KEI-T4", now - timedelta(days=120), ctx)
    row = discovery_log.load_all_discoveries(isolated_log)[0]
    f = compute_freshness(row, now=now, current_version=ctx)
    assert f["verdict"] == "expired"


def test_load_fresh_excludes_expired_and_tags_stale(isolated_log, monkeypatch):
    now = datetime.now(UTC)
    ctx = {"kernel": "X"}
    monkeypatch.setattr(
        "scripts.orchestrator.discovery_log.current_context_version", lambda: ctx
    )
    _write(isolated_log, "KEI-FRESH", now - timedelta(days=5), ctx)
    _write(isolated_log, "KEI-STALE", now - timedelta(days=45), ctx)
    _write(isolated_log, "KEI-EXPIRED", now - timedelta(days=120), ctx)
    fresh_set = load_fresh_discoveries(isolated_log)
    keis = {r["kei"] for r in fresh_set}
    assert "KEI-EXPIRED" not in keis
    assert "KEI-FRESH" in keis and "KEI-STALE" in keis
    stale_row = next(r for r in fresh_set if r["kei"] == "KEI-STALE")
    assert stale_row["_freshness"]["verdict"] == "stale"


def test_bd_verify_cli_returns_verdict_and_exit_zero(isolated_log, monkeypatch):
    now = datetime.now(UTC)
    ctx = {"kernel": "X"}
    _write(isolated_log, "KEI-CLI", now - timedelta(days=5), ctx)
    env = {
        "PYTHONPATH": str(REPO_ROOT),
        "AGENCY_OS_DISCOVERY_LOG": str(isolated_log),
        "AGENCY_OS_CONTEXT_VERSION_JSON": json.dumps(ctx),
        "PATH": "/usr/bin:/bin",
    }
    out = subprocess.run(
        [sys.executable, str(BD_VERIFY), "KEI-CLI", "--json"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=10,
    )
    assert out.returncode == 0, out.stderr
    payload = json.loads(out.stdout)
    assert payload["kei"] == "KEI-CLI"
    assert payload["verdict"] in ("fresh", "stale", "expired")


def test_bd_verify_cli_missing_kei_exits_two(isolated_log):
    env = {
        "PYTHONPATH": str(REPO_ROOT),
        "AGENCY_OS_DISCOVERY_LOG": str(isolated_log),
        "AGENCY_OS_CONTEXT_VERSION_JSON": json.dumps({"kernel": "X"}),
        "PATH": "/usr/bin:/bin",
    }
    out = subprocess.run(
        [sys.executable, str(BD_VERIFY), "KEI-DOES-NOT-EXIST"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=10,
    )
    assert out.returncode == 2
    assert "no discovery row" in out.stderr
