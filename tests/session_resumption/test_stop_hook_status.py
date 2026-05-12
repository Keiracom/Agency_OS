"""Regression guard for the PR-C clean-close Stop hook.

The hook is a bash script with embedded Python (.claude/hooks/session_store_stop.sh).
Its only behaviour relevant to PR-C is the literal `status='closed_clean'`
argument passed to record_session_end — get that wrong (e.g. revert to
`status='closed'`) and every planned tmux kill silently breaks `claude
--resume`. Pin the literal so the bug can never quietly regress.
"""

from __future__ import annotations

from pathlib import Path

HOOK = (
    Path(__file__).resolve().parent.parent.parent
    / ".claude"
    / "hooks"
    / "session_store_stop.sh"
)


def test_stop_hook_exists() -> None:
    assert HOOK.is_file(), f"Stop hook missing at {HOOK}"


def test_stop_hook_passes_closed_clean_status() -> None:
    body = HOOK.read_text()
    assert "record_session_end(session_id=UUID(sid), status='closed_clean')" in body, (
        "Stop hook must call record_session_end with status='closed_clean' "
        "(PR-C clean-close fix). 'closed' was the previous default and broke "
        "--resume on planned restarts."
    )
    assert "status='closed')" not in body, (
        "Stop hook still contains status='closed' literal — that path is now "
        "reserved for explicit no-resume closes (no current caller)."
    )
