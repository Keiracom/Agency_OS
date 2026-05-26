"""Tests for §7 piece 6 cutover-checklist generator.

bd: Agency_OS-7uy6
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts" / "dispatcher"))

_mod = importlib.import_module("cutover_checklist")


def _make_systemd_dir(tmp_path: Path, names: list[str]) -> Path:
    d = tmp_path / "systemd"
    d.mkdir()
    for n in names:
        (d / n).write_text("", encoding="utf-8")
    return d


def test_discover_returns_callsign_prefixed_service_files(tmp_path: Path):
    d = _make_systemd_dir(
        tmp_path,
        [
            "atlas-agent.service",
            "atlas-inbox-watcher.service",
            "atlas-relay-watcher.service",
            "elliot-agent.service",  # different callsign — excluded
            "some-other.service",
        ],
    )
    out = _mod.discover_callsign_units("atlas", systemd_dir=d)
    assert out == [
        "atlas-agent.service",
        "atlas-inbox-watcher.service",
        "atlas-relay-watcher.service",
    ]


def test_discover_filters_disabled_suffix_files(tmp_path: Path):
    d = _make_systemd_dir(
        tmp_path,
        [
            "atlas-agent.service",
            "atlas-polling-loop.service.disabled-2026-05-18",
            "atlas-old.service.disabled",
        ],
    )
    out = _mod.discover_callsign_units("atlas", systemd_dir=d)
    assert out == ["atlas-agent.service"]


def test_discover_returns_empty_when_systemd_dir_missing(tmp_path: Path):
    out = _mod.discover_callsign_units("atlas", systemd_dir=tmp_path / "no-such-dir")
    assert out == []


def test_discover_excludes_other_callsign_prefixes(tmp_path: Path):
    """`atlas-` prefix must not match `atlas2-` or `atlast-`."""
    d = _make_systemd_dir(
        tmp_path,
        [
            "atlas-agent.service",
            "atlas2-spurious.service",
            "atlast-spurious.service",
        ],
    )
    out = _mod.discover_callsign_units("atlas", systemd_dir=d)
    # Atlas2-/atlast- both START with "atlas-" actually NO — "atlas2-" starts with
    # "atlas2" not "atlas-". Our prefix is "atlas-" so atlas2-... won't match.
    assert out == ["atlas-agent.service"]


def test_render_checklist_carries_callsign_and_units():
    out = _mod.render_checklist("atlas", ["atlas-agent.service", "atlas-inbox-watcher.service"])
    assert "# Cutover-day checklist — `atlas`" in out
    assert "atlas-agent.service" in out
    assert "atlas-inbox-watcher.service" in out
    assert "keiracom-dispatcher@atlas.service" in out
    assert "Step 5 — (rollback" in out


def test_render_checklist_handles_no_units():
    out = _mod.render_checklist("nova", [])
    assert "# Cutover-day checklist — `nova`" in out
    assert "_(no current per-callsign units discovered" in out
    # All 5 steps still rendered
    assert "Step 1 — Pre-cutover snapshot" in out
    assert "Step 5 — (rollback" in out


def test_callsigns_constant_covers_seven_fleet_callsigns():
    assert set(_mod.CALLSIGNS) == {"elliot", "aiden", "max", "atlas", "orion", "scout", "nova"}


def test_main_writes_to_output_file(tmp_path: Path, capsys):
    systemd = _make_systemd_dir(tmp_path, ["atlas-agent.service"])
    out_path = tmp_path / "out.md"
    rc = _mod.main(
        [
            "--callsign",
            "atlas",
            "--output",
            str(out_path),
            "--systemd-dir",
            str(systemd),
        ]
    )
    assert rc == 0
    body = out_path.read_text(encoding="utf-8")
    assert "atlas-agent.service" in body
    assert "Cutover-day checklist — `atlas`" in body


def test_main_emits_all_seven_callsigns(tmp_path: Path, capsys):
    systemd = _make_systemd_dir(
        tmp_path,
        [f"{cs}-agent.service" for cs in _mod.CALLSIGNS],
    )
    rc = _mod.main(["--all", "--systemd-dir", str(systemd)])
    assert rc == 0
    captured = capsys.readouterr().out
    for cs in _mod.CALLSIGNS:
        assert f"Cutover-day checklist — `{cs}`" in captured
