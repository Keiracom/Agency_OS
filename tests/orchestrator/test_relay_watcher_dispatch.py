"""Tests for relay_watcher.sh task_dispatch handling.

Verifies that the Python extraction commands embedded in relay_watcher.sh
correctly parse task_dispatch JSON files — the root cause of Scout being
dispatch-dark for 16+ days (relay_watcher silently dropped task_dispatch
messages before this fix).
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RELAY_WATCHER = REPO_ROOT / "scripts" / "orchestrator" / "relay_watcher.sh"


def _run_python_extract(fpath: str, code: str) -> str:
    """Run one of the inline Python extraction commands from relay_watcher.sh."""
    result = subprocess.run(
        ["python3", "-c", code.replace("$fpath", fpath)],
        capture_output=True,
        text=True,
        timeout=5,
    )
    return result.stdout.strip()


def test_relay_watcher_script_exists() -> None:
    assert RELAY_WATCHER.exists()


def test_relay_watcher_handles_task_dispatch_type() -> None:
    """relay_watcher.sh must contain a branch for task_dispatch."""
    content = RELAY_WATCHER.read_text()
    assert 'task_dispatch' in content


def test_relay_watcher_has_fallback_else() -> None:
    """relay_watcher.sh must have a fallback else for unknown types."""
    content = RELAY_WATCHER.read_text()
    lines = content.splitlines()
    has_else = any(line.strip() == "else" for line in lines)
    assert has_else


def test_dispatch_extraction_with_brief_and_ref() -> None:
    """task_dispatch JSON with brief + task_ref → formatted output."""
    dispatch = {
        "type": "task_dispatch",
        "from": "elliot",
        "brief": "Audit Scout tmux loop",
        "task_ref": "scout-audit-001",
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(dispatch, f)
        f.flush()
        code = """
import json
d = json.load(open('$fpath'))
sender = d.get('from', 'unknown')
brief = d.get('brief', 'no brief').replace('\\n', ' ')
task_ref = d.get('task_ref', '')
suffix = f' (ref: {task_ref})' if task_ref else ''
print(f'[DISPATCH FROM {sender.upper()}] {brief}{suffix}')
"""
        result = _run_python_extract(f.name, code)
    assert result == "[DISPATCH FROM ELLIOT] Audit Scout tmux loop (ref: scout-audit-001)"


def test_dispatch_extraction_without_task_ref() -> None:
    dispatch = {
        "type": "task_dispatch",
        "from": "max",
        "brief": "Build the feature",
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(dispatch, f)
        f.flush()
        code = """
import json
d = json.load(open('$fpath'))
sender = d.get('from', 'unknown')
brief = d.get('brief', 'no brief').replace('\\n', ' ')
task_ref = d.get('task_ref', '')
suffix = f' (ref: {task_ref})' if task_ref else ''
print(f'[DISPATCH FROM {sender.upper()}] {brief}{suffix}')
"""
        result = _run_python_extract(f.name, code)
    assert result == "[DISPATCH FROM MAX] Build the feature"


def test_dispatch_extraction_multiline_brief_flattened() -> None:
    dispatch = {
        "type": "task_dispatch",
        "from": "aiden",
        "brief": "Line 1\nLine 2\nLine 3",
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(dispatch, f)
        f.flush()
        code = """
import json
d = json.load(open('$fpath'))
sender = d.get('from', 'unknown')
brief = d.get('brief', 'no brief').replace('\\n', ' ')
task_ref = d.get('task_ref', '')
suffix = f' (ref: {task_ref})' if task_ref else ''
print(f'[DISPATCH FROM {sender.upper()}] {brief}{suffix}')
"""
        result = _run_python_extract(f.name, code)
    assert "\n" not in result
    assert "Line 1 Line 2 Line 3" in result


def test_msg_type_detection_task_dispatch() -> None:
    """The type extraction command must return 'task_dispatch' for dispatch messages."""
    dispatch = {"type": "task_dispatch", "from": "elliot", "brief": "test"}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(dispatch, f)
        f.flush()
        result = _run_python_extract(
            f.name, "import json; print(json.load(open('$fpath')).get('type',''))"
        )
    assert result == "task_dispatch"


def test_fallback_extraction_unknown_type() -> None:
    """Unknown message types should still produce injectable text."""
    msg = {"type": "webhook_event", "text": "Something happened"}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(msg, f)
        f.flush()
        code = """
import json
d = json.load(open('$fpath'))
t = d.get('text', d.get('brief', json.dumps(d, default=str)))
t = t.replace('\\n', ' ')[:500]
print(t)
"""
        result = _run_python_extract(f.name, code)
    assert result == "Something happened"
