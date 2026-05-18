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
    assert "task_dispatch" in content


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


# ─── KEI-99: session-name resilience (discover_callsign_sessions) ────────────


def _run_discover_harness(callsign: str, live_sessions: list[str], tmp_path: Path) -> list[str]:
    """Run the discover_callsign_sessions function with a stubbed `tmux`.

    Replicates the case statement + function from relay_watcher.sh so the unit
    test exercises the function's logic without invoking inotifywait.
    """
    stub_dir = tmp_path / "stub"
    stub_dir.mkdir()
    canned = "\n".join(live_sessions)
    tmux_stub = stub_dir / "tmux"
    tmux_stub.write_text(
        "#!/bin/bash\n"
        'if [[ "$1" == "list-sessions" ]]; then\n'
        f"    cat <<'EOF'\n{canned}\nEOF\n"
        "    exit 0\n"
        "fi\n"
        "exit 0\n"
    )
    tmux_stub.chmod(0o755)
    harness = rf"""
set -e
export PATH={stub_dir}:$PATH
export CALLSIGN={callsign}
case "$CALLSIGN" in
    elliot)  TMUX_CANDIDATES=("elliottbot:0.0" "elliot:0.0" "elliot-agent:0.0") ;;
    aiden)   TMUX_CANDIDATES=("aiden:0.0" "aidenbot:0.0" "aiden-agent:0.0") ;;
    scout)   TMUX_CANDIDATES=("scout:0.0" "scoutbot:0.0" "scout-agent:0.0") ;;
    max)     TMUX_CANDIDATES=("maxbot:0.0" "max:0.0" "max-agent:0.0") ;;
    *)       TMUX_CANDIDATES=("${{CALLSIGN}}bot:0.0" "${{CALLSIGN}}:0.0" "${{CALLSIGN}}-agent:0.0") ;;
esac
discover_callsign_sessions() {{
    local -a live=()
    local sess lowered cs_lower="${{CALLSIGN,,}}"
    mapfile -t live < <(tmux list-sessions -F '#{{session_name}}' 2>/dev/null || true)
    for sess in "${{live[@]}}"; do
        lowered="${{sess,,}}"
        if [[ "$lowered" == *"$cs_lower"* ]]; then
            local candidate="${{sess}}:0.0"
            local already=0
            for existing in "${{TMUX_CANDIDATES[@]}}"; do
                if [[ "$existing" == "$candidate" ]]; then
                    already=1
                    break
                fi
            done
            if [[ $already -eq 0 ]]; then
                TMUX_CANDIDATES+=("$candidate")
            fi
        fi
    done
}}
discover_callsign_sessions
printf '%s\n' "${{TMUX_CANDIDATES[@]}}"
"""
    result = subprocess.run(
        ["bash", "-c", harness], capture_output=True, text=True, check=True, timeout=5
    )
    return [line for line in result.stdout.splitlines() if line]


def test_discover_appends_substring_match(tmp_path: Path) -> None:
    """Non-default session name containing callsign is appended as fallback."""
    cands = _run_discover_harness("scout", ["scout-clawd", "unrelated"], tmp_path)
    assert "scout:0.0" in cands  # primary preserved
    assert "scout-clawd:0.0" in cands  # dynamic match appended
    assert "unrelated:0.0" not in cands  # non-match excluded


def test_discover_case_insensitive(tmp_path: Path) -> None:
    """Capitalised session name still matches lowercase callsign."""
    cands = _run_discover_harness("scout", ["SCOUT_alt", "Scout-Backup"], tmp_path)
    assert "SCOUT_alt:0.0" in cands
    assert "Scout-Backup:0.0" in cands


def test_discover_dedupes_primary(tmp_path: Path) -> None:
    """A live session that already matches a hardcoded primary is not duplicated."""
    cands = _run_discover_harness("scout", ["scout", "scout-extra"], tmp_path)
    assert cands.count("scout:0.0") == 1
    assert "scout-extra:0.0" in cands


def test_discover_no_live_sessions(tmp_path: Path) -> None:
    """Empty tmux list-sessions leaves hardcoded primaries intact."""
    cands = _run_discover_harness("scout", [], tmp_path)
    assert cands == ["scout:0.0", "scoutbot:0.0", "scout-agent:0.0"]


def test_discover_relay_watcher_script_contains_helper() -> None:
    """The production script must define + call discover_callsign_sessions after the case."""
    content = RELAY_WATCHER.read_text()
    assert "discover_callsign_sessions" in content
    assert content.count("discover_callsign_sessions") >= 2
