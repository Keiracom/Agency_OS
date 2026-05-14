"""
Tests for the Governance Equality Guard exemption logic.

Each test builds a minimal fake git workspace and runs the guard shell script
extracted from .github/workflows/governance-equality-guard.yml.

Scenarios verified:
  1. No CLAUDE.md change       → PASS  (equality preserved)
  2. Changed + new @include    → PASS  (exemption 1)
  3. Changed + gov PR title    → PASS  (exemption 2 via PR title)
  4. Changed + gov commit msg  → PASS  (exemption 2 via commit message)
  5. Changed + no exemption    → FAIL  (guard blocks)
"""

import os
import subprocess
import textwrap
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Extract the shell logic from the workflow file once at import time.
# ---------------------------------------------------------------------------

WORKFLOW = (
    Path(__file__).parents[2]
    / ".github/workflows/governance-equality-guard.yml"
)


def _extract_shell_script() -> str:
    """Return the raw 'run' block with GitHub Actions expressions stripped."""
    content = WORKFLOW.read_text()
    # Find 'run: |' and grab everything after
    idx = content.find("run: |\n")
    assert idx != -1, "Could not find 'run: |' in workflow file"
    raw = content[idx + len("run: |\n"):]
    lines = []
    for line in raw.split("\n"):
        # Strip 10-space YAML indent (workflow step body indentation)
        stripped = line[10:] if line.startswith(" " * 10) else line
        # Replace ${{ github.event.pull_request.base.ref }} → $BASE_REF_INJECT
        # (callers set BASE_REF directly so fetch is no-op — see harness below)
        stripped = stripped.replace(
            "${{ github.event.pull_request.base.ref }}", "$BASE_REF_INJECT"
        )
        # Replace ${{ github.event.pull_request.title }} → $PR_TITLE_INJECT
        stripped = stripped.replace(
            "${{ github.event.pull_request.title }}", "$PR_TITLE_INJECT"
        )
        lines.append(stripped)
    return "\n".join(lines)


GUARD_SCRIPT = _extract_shell_script()


# ---------------------------------------------------------------------------
# Harness helpers
# ---------------------------------------------------------------------------

def _write_fake_git(tmp_path: Path, base_content: str, head_content: str,
                    diff_output: str, log_output: str) -> Path:
    """
    Build a fake git workspace under tmp_path.

    We stub out git with a tiny shell script that returns canned output
    for the specific git invocations the guard uses.

    Content files are written to disk so the fake git script can `cat` them —
    this avoids printf/repr escaping mismatches for multi-line content.
    """
    # Write CLAUDE.md (HEAD version — the real file the guard md5sums)
    (tmp_path / "CLAUDE.md").write_text(head_content)

    # Write canned output files
    (tmp_path / "_fake_base.txt").write_text(base_content)
    (tmp_path / "_fake_diff.txt").write_text(diff_output)
    (tmp_path / "_fake_log.txt").write_text(log_output)

    # Fake git binary — handles only the calls the guard makes:
    #   git fetch origin <ref> --depth=1   → no-op
    #   git show origin/<ref>:CLAUDE.md    → cat _fake_base.txt
    #   git diff origin/<ref>...HEAD -- CLAUDE.md → cat _fake_diff.txt
    #   git log --pretty=%s origin/<ref>..HEAD    → cat _fake_log.txt
    fake_git = tmp_path / "git"
    # FAKE_DIR is injected into the script at write time (absolute path, no escaping issues)
    fake_dir = str(tmp_path)
    fake_git.write_text(
        textwrap.dedent(f"""\
        #!/usr/bin/env bash
        FAKE_DIR={fake_dir!r}
        case "$*" in
          fetch*)
            exit 0 ;;
          show*)
            cat "$FAKE_DIR/_fake_base.txt" ;;
          "diff "*)
            cat "$FAKE_DIR/_fake_diff.txt" ;;
          "log "*)
            cat "$FAKE_DIR/_fake_log.txt" ;;
          *)
            echo "fake git: unhandled: $*" >&2
            exit 1 ;;
        esac
        """),
        encoding="utf-8",
    )
    fake_git.chmod(0o755)
    return tmp_path


def _run_guard(tmp_path: Path, pr_title: str, base_ref: str = "main") -> subprocess.CompletedProcess:
    """Run the extracted guard script in tmp_path with the given env."""
    env = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",  # fake git first
        "BASE_REF_INJECT": base_ref,
        "PR_TITLE_INJECT": pr_title,
    }
    # Prepend BASE_REF assignment so the script can resolve it
    script = f"BASE_REF={base_ref!r}\n" + GUARD_SCRIPT
    return subprocess.run(
        ["bash", "-s"],
        input=script,
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=env,
    )


# ---------------------------------------------------------------------------
# Scenario helpers
# ---------------------------------------------------------------------------

COMMON_BASE = "line1\nline2\n"
COMMON_HEAD = COMMON_BASE  # identical → hash match


# ---------------------------------------------------------------------------
# Test 1: No change in CLAUDE.md → guard passes (equality preserved)
# ---------------------------------------------------------------------------

def test_no_claude_md_change(tmp_path):
    _write_fake_git(tmp_path, COMMON_BASE, COMMON_HEAD,
                    diff_output="", log_output="")
    result = _run_guard(tmp_path, pr_title="[AIDEN] feat: something unrelated")
    assert result.returncode == 0, f"Expected PASS.\nstdout={result.stdout}\nstderr={result.stderr}"
    assert "equality preserved" in result.stdout


# ---------------------------------------------------------------------------
# Test 2: Changed + new @include → exemption 1 fires
# ---------------------------------------------------------------------------

def test_exemption_1_new_include(tmp_path):
    base = "line1\n"
    head = "line1\n@.claude/modules/_discovery_log.md\n"
    # diff output simulates what 'git diff ... -- CLAUDE.md' would print
    diff = "+@.claude/modules/_discovery_log.md"
    _write_fake_git(tmp_path, base, head, diff_output=diff, log_output="")
    result = _run_guard(tmp_path, pr_title="[ELLIOT] chore: untagged")
    assert result.returncode == 0, f"Expected PASS (exemption 1).\nstdout={result.stdout}\nstderr={result.stderr}"
    assert "exemption applied" in result.stdout
    assert "include" in result.stdout


# ---------------------------------------------------------------------------
# Test 3: Changed + governance-tagged PR title → exemption 2 (title)
# ---------------------------------------------------------------------------

def test_exemption_2_pr_title(tmp_path):
    base = "line1\n"
    head = "line1\nsome other change\n"
    # No new @include line in diff
    diff = "+some other change"
    _write_fake_git(tmp_path, base, head, diff_output=diff, log_output="")
    result = _run_guard(
        tmp_path,
        pr_title="[ELLIOT] feat(governance): extend the guard with exemptions",
    )
    assert result.returncode == 0, f"Expected PASS (exemption 2 title).\nstdout={result.stdout}\nstderr={result.stderr}"
    assert "exemption applied" in result.stdout
    assert "governance-tagged" in result.stdout


# ---------------------------------------------------------------------------
# Test 4: Changed + governance-tagged commit message → exemption 2 (commit)
# ---------------------------------------------------------------------------

def test_exemption_2_commit_message(tmp_path):
    base = "line1\n"
    head = "line1\nsome other change\n"
    diff = "+some other change"
    log = "[ELLIOT] feat(kei50): discovery log module add"
    _write_fake_git(tmp_path, base, head, diff_output=diff, log_output=log)
    result = _run_guard(tmp_path, pr_title="[ELLIOT] chore: not tagged")
    assert result.returncode == 0, f"Expected PASS (exemption 2 commit).\nstdout={result.stdout}\nstderr={result.stderr}"
    assert "exemption applied" in result.stdout
    assert "governance-tagged" in result.stdout


# ---------------------------------------------------------------------------
# Test 5: Changed + no exemption → guard fails
# ---------------------------------------------------------------------------

def test_no_exemption_fails(tmp_path):
    base = "line1\n"
    head = "line1\nrogue change\n"
    # diff has no @include pattern
    diff = "+rogue change"
    # commit log has no governance tag
    log = "[ELLIOT] chore: random cleanup"
    _write_fake_git(tmp_path, base, head, diff_output=diff, log_output=log)
    result = _run_guard(
        tmp_path,
        pr_title="[ELLIOT] fix: something without governance tag",
    )
    assert result.returncode == 1, f"Expected FAIL (no exemption).\nstdout={result.stdout}\nstderr={result.stderr}"
    assert "without exemption" in result.stdout or "without exemption" in result.stderr
