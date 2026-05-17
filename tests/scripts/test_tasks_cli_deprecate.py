"""Tests for tasks_cli deprecate subcommand (KEI-63)."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "tasks_cli.py"

_spec = importlib.util.spec_from_file_location("tasks_cli", SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["tasks_cli"] = _mod
_spec.loader.exec_module(_mod)


@pytest.fixture
def jsonl(tmp_path, monkeypatch):
    p = tmp_path / "discovery_log.jsonl"
    monkeypatch.setenv("AGENCY_OS_DISCOVERY_LOG", str(p))
    monkeypatch.setenv("CALLSIGN", "max")
    return p


def _seed(jsonl, entries):
    with jsonl.open("a", encoding="utf-8") as fh:
        for e in entries:
            fh.write(json.dumps(e) + "\n")


def test_deprecate_marks_row(jsonl, capsys):
    _seed(jsonl, [{"kei": "KEI-A", "finding": "v1"}])
    rc = _mod.main(["deprecate", "KEI-A", "--reason", "wrong"])
    assert rc == 0
    rows = [json.loads(l) for l in jsonl.read_text().splitlines()]
    assert rows[0]["deprecated"] is True
    assert rows[0]["deprecated_reason"] == "wrong"
    assert rows[0]["deprecated_by"] == "max"


def test_deprecate_json_output(jsonl, capsys):
    _seed(jsonl, [{"kei": "KEI-A", "finding": "v1"}])
    rc = _mod.main(["deprecate", "KEI-A", "--reason", "stale", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["kei"] == "KEI-A"
    assert payload["deprecated_reason"] == "stale"


def test_deprecate_missing_kei_returns_1(jsonl, capsys):
    _seed(jsonl, [{"kei": "KEI-A"}])
    rc = _mod.main(["deprecate", "KEI-MISSING", "--reason", "r"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "no discovery row" in err


def test_deprecate_requires_callsign(jsonl, capsys, monkeypatch):
    monkeypatch.delenv("CALLSIGN", raising=False)
    _seed(jsonl, [{"kei": "KEI-A"}])
    rc = _mod.main(["deprecate", "KEI-A", "--reason", "r"])
    assert rc == 2
    assert "callsign required" in capsys.readouterr().err


def test_deprecate_callsign_flag_overrides_env(jsonl, capsys):
    _seed(jsonl, [{"kei": "KEI-A"}])
    rc = _mod.main(["deprecate", "KEI-A", "--reason", "r", "--callsign", "ELLIOT"])
    assert rc == 0
    rows = [json.loads(l) for l in jsonl.read_text().splitlines()]
    assert rows[0]["deprecated_by"] == "elliot"


def test_deprecate_requires_reason(jsonl, capsys):
    _seed(jsonl, [{"kei": "KEI-A"}])
    with pytest.raises(SystemExit):
        _mod.main(["deprecate", "KEI-A"])


def test_deprecate_then_active_load_excludes(jsonl, capsys):
    """End-to-end behavioral path: deprecate → active-load filter excludes target."""
    _seed(jsonl, [{"kei": "KEI-A", "f": "v1"}, {"kei": "KEI-B", "f": "stays"}])

    spec = importlib.util.spec_from_file_location(
        "discovery_log",
        str(REPO_ROOT / "scripts" / "orchestrator" / "discovery_log.py"),
    )
    dl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dl)
    os.environ["AGENCY_OS_DISCOVERY_LOG"] = str(jsonl)

    rc = _mod.main(["deprecate", "KEI-A", "--reason", "smoke"])
    assert rc == 0
    active = dl.load_active_discoveries(jsonl)
    assert [r["kei"] for r in active] == ["KEI-B"]
