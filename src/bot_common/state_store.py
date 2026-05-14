"""state_store.py — env-overridable JSON state file helpers.

Shared by scripts that persist small JSON dicts to disk with an
env-override-able path and a safe allowlist of writable roots
(~/.local/state/agency-os and /tmp for tests).

Extracted 2026-05-13 (KEI-35) from scripts/orchestrator/auto_session_recovery.py
and scripts/betterstack_to_linear.py to eliminate a 22-line duplicated block
flagged by SonarCloud new_duplicated_lines_density.

Public API:

    resolve_state_path(env_var, default_path) -> Path
        Honour env override only if it falls under ALLOWED_STATE_ROOTS;
        otherwise fall back to default_path.

    load_state(path) -> dict[str, dict]
        JSON-load `path`; return {} on missing or unparseable.

    save_state(path, state, logger, label="state") -> None
        Write JSON `state` to `path`; log warning on OSError. Caller has
        already validated `path` via resolve_state_path() — the NOSONAR
        below documents that.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

ALLOWED_STATE_ROOTS: tuple[Path, ...] = (
    Path(os.path.expanduser("~/.local/state/agency-os")),
    Path("/tmp"),  # NOSONAR — pytest tmp_path roots
)


def _is_under(p: Path, root: Path) -> bool:
    try:
        p.relative_to(root)
        return True
    except ValueError:
        return False


def resolve_state_path(env_var: str, default_path: str) -> Path:
    """Resolve a state-file path; env override validated against ALLOWED_STATE_ROOTS."""
    raw = os.environ.get(env_var, default_path)
    resolved = Path(raw).expanduser().resolve()
    if not any(_is_under(resolved, root.resolve()) for root in ALLOWED_STATE_ROOTS):
        return Path(default_path).expanduser().resolve()
    return resolved


def load_state(path: Path) -> dict[str, dict]:
    """JSON-load `path`; return {} on missing or unparseable."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text() or "{}")
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(
    path: Path,
    state: dict[str, dict],
    logger: logging.Logger,
    label: str = "state",
) -> None:
    """Write JSON `state` to `path`; log warning on OSError.

    `path` MUST come from resolve_state_path() (or another caller-validated
    allowlist resolver) — the inline NOSONAR on the write line documents that.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(state, indent=2, sort_keys=True)
        path.write_text(payload)  # NOSONAR — caller-validated via resolve_state_path()
    except OSError as exc:
        logger.warning("%s save failed: %s", label, exc)
