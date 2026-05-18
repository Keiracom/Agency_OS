"""KEI-213 / KEI-108 gate: dispatcher.service has matching install path + assertions.

Asserts that:
  1. infra/systemd/agents/dispatcher.service exists with expected Exec/Unit fields.
  2. scripts/install_dispatcher.sh exists, is executable, and references the unit.
  3. The install script sources the unit from infra/systemd/agents/ (paths align).

This test is the operational-deployment hook the KEI-108 sweep audit looks for —
"unit shipped without install/acceptance hooks" silently produces a not-running
service on deploy. This test is the audit's positive marker for dispatcher.service.
"""

from __future__ import annotations

import os
import re
import stat
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIT_PATH = REPO_ROOT / "infra/systemd/agents/dispatcher.service"
INSTALL_PATH = REPO_ROOT / "scripts/install_dispatcher.sh"


def test_dispatcher_service_unit_exists() -> None:
    assert UNIT_PATH.is_file(), f"missing systemd unit: {UNIT_PATH}"


def test_dispatcher_service_unit_has_expected_exec() -> None:
    body = UNIT_PATH.read_text()
    assert "src.dispatcher.main:app" in body, "ExecStart must launch main:app"
    assert "Restart=always" in body, "Restart=always required for reliability"
    assert "WatchdogSec=" in body, "WatchdogSec required for liveness"
    assert "EnvironmentFile=" in body, "EnvironmentFile required for secrets"


def test_install_script_exists_and_executable() -> None:
    assert INSTALL_PATH.is_file(), f"missing install script: {INSTALL_PATH}"
    mode = INSTALL_PATH.stat().st_mode
    assert mode & stat.S_IXUSR, "install script must be executable (chmod +x)"


def test_install_script_references_unit() -> None:
    body = INSTALL_PATH.read_text()
    assert "dispatcher.service" in body, "install script must reference the unit name"
    assert "infra/systemd/agents/dispatcher.service" in body, (
        "install script must source the unit from infra/systemd/agents/"
    )
    assert "systemctl --user enable --now dispatcher.service" in body, (
        "install script must enable + start the unit (KEI-108 wiring requirement)"
    )


def test_install_script_idempotent_shape() -> None:
    body = INSTALL_PATH.read_text()
    assert "set -euo pipefail" in body, "install script must fail-fast on errors"
    assert "daemon-reload" in body, "install script must reload systemd daemon"
    assert re.search(r"mkdir\s+-p", body), "install script must mkdir -p UNITS_DIR"


def test_unit_and_install_script_agree_on_path() -> None:
    """Cross-check: the install script's UNIT_SOURCE path must point at where the
    unit actually lives. Caught by KEI-108 gate if the script references a stale
    path."""
    install_body = INSTALL_PATH.read_text()
    match = re.search(r'UNIT_SOURCE="\$\{REPO_DIR\}/([^"]+)"', install_body)
    assert match, "install script must define UNIT_SOURCE relative to REPO_DIR"
    referenced_rel = match.group(1)
    expected_rel = os.path.relpath(UNIT_PATH, REPO_ROOT)
    assert referenced_rel == expected_rel, (
        f"install script UNIT_SOURCE={referenced_rel} but unit lives at {expected_rel}"
    )
