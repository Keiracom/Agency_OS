"""Tests for scripts/heartbeat_generator.py — Task 1B 20-item roadmap #2.

Verifies the generator turns one BASE HEARTBEAT.md + per-callsign YAML into
six customised HEARTBEAT.<callsign>.md files. Each file must:
  - preserve the BASE template content
  - include its own callsign's role / token budget / allowed paths /
    prohibited actions / escalation trigger
  - NOT include another callsign's data

Tests use real repo BASE + real config. No network, no Supabase.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "heartbeat_generator.py"
BASE_TEMPLATE = REPO_ROOT / "HEARTBEAT.md"
CONFIG_PATH = REPO_ROOT / "config" / "heartbeat_callsigns.yaml"

_spec = importlib.util.spec_from_file_location("heartbeat_generator", SCRIPT_PATH)
hb = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
sys.modules["heartbeat_generator"] = hb
_spec.loader.exec_module(hb)


EXPECTED_CALLSIGNS = ["aiden", "atlas", "elliot", "max", "orion", "scout"]


@pytest.fixture
def generated(tmp_path: Path) -> dict[str, str]:
    """Run the generator into tmp_path and return {callsign: file_content}."""
    written = hb.generate(BASE_TEMPLATE, CONFIG_PATH, tmp_path)
    bodies: dict[str, str] = {}
    for p in written:
        # filename HEARTBEAT.<callsign>.md
        callsign = p.name.removeprefix("HEARTBEAT.").removesuffix(".md")
        bodies[callsign] = p.read_text()
    return bodies


def test_generator_emits_six_files(generated):
    assert sorted(generated) == EXPECTED_CALLSIGNS


def test_each_file_preserves_base_template(generated):
    base_content = BASE_TEMPLATE.read_text().rstrip()
    for callsign, body in generated.items():
        # BASE must appear verbatim at the top so agents read the same
        # heartbeat cadence + headings regardless of callsign.
        assert body.startswith(base_content), (
            f"HEARTBEAT.{callsign}.md does not start with BASE template"
        )


def test_each_file_has_per_callsign_section(generated):
    for callsign, body in generated.items():
        assert "## Per-Callsign Context" in body
        assert f"- **Callsign:** `{callsign}`" in body


def test_each_callsign_section_contains_required_fields(generated):
    for callsign, body in generated.items():
        for label in (
            "- **Role:**",
            "- **Max token budget:**",
            "- **Allowed paths:**",
            "- **Prohibited actions:**",
            "- **Escalation trigger:**",
        ):
            assert label in body, f"HEARTBEAT.{callsign}.md missing {label!r}"


def test_token_budgets_are_callsign_specific(generated):
    # Spot-check that elliot vs scout get different budgets — proves the
    # per-callsign config is actually being applied, not a static copy.
    assert "200,000" in generated["elliot"]
    assert "120,000" in generated["scout"]


def test_files_are_distinct(generated):
    bodies = list(generated.values())
    unique = set(bodies)
    assert len(unique) == len(bodies), (
        "Generator produced duplicate output — per-callsign customisation "
        "must make every file textually distinct."
    )


def test_no_cross_contamination(generated):
    # Orion's "Touching frontend/ (Max's lane)" should NOT appear in Elliot's
    # file; Elliot's "drop scope when context > 60%" should NOT appear in
    # Atlas's file. Validates that callsign sections are isolated.
    assert "Touching frontend/ (Max's lane)" in generated["orion"]
    assert "Touching frontend/ (Max's lane)" not in generated["elliot"]
    assert "drop scope when context > 60%" in generated["elliot"]
    assert "drop scope when context > 60%" not in generated["atlas"]


def test_missing_required_field_raises(tmp_path: Path):
    bad_config = tmp_path / "bad.yaml"
    bad_config.write_text(
        "callsigns:\n"
        "  foo:\n"
        "    role: incomplete\n"
        "    max_token_budget: 1\n"
        # missing allowed_paths / prohibited_actions / escalation_trigger
    )
    with pytest.raises(ValueError, match="missing required fields"):
        hb.load_config(bad_config)


def test_generator_cli_returns_zero(tmp_path: Path, capsys):
    rc = hb.main(
        [
            "--template",
            str(BASE_TEMPLATE),
            "--config",
            str(CONFIG_PATH),
            "--output-dir",
            str(tmp_path),
        ]
    )
    assert rc == 0
    stdout = capsys.readouterr().out
    for cs in EXPECTED_CALLSIGNS:
        assert f"HEARTBEAT.{cs}.md" in stdout


def test_generator_is_deterministic(tmp_path: Path):
    """Same inputs must produce byte-identical output across runs — gives
    operators a clean diff signal when config genuinely changes."""
    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"
    hb.generate(BASE_TEMPLATE, CONFIG_PATH, out1)
    hb.generate(BASE_TEMPLATE, CONFIG_PATH, out2)
    for cs in EXPECTED_CALLSIGNS:
        assert (out1 / f"HEARTBEAT.{cs}.md").read_bytes() == (
            out2 / f"HEARTBEAT.{cs}.md"
        ).read_bytes()


def test_missing_template_returns_nonzero(tmp_path: Path, capsys):
    rc = hb.main(
        [
            "--template",
            str(tmp_path / "nope.md"),
            "--config",
            str(CONFIG_PATH),
            "--output-dir",
            str(tmp_path),
        ]
    )
    assert rc == 1
