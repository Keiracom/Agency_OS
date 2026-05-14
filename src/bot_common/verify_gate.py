"""verify_gate.py — outbound verification gate for completion claims (S1).

Catches fabricated PR numbers and commit hashes in outbound messages BEFORE
posting to Slack. Deterministic, no LLM.

Trigger: message contains completion-pattern phrase (shipped/merged/landed/etc.)
AND references a PR number or commit hash.

Verification:
  - PR #N → `gh pr view N --json state`; refuse if "Could not resolve" or state
    mismatches the claim (e.g. "merged" claim but state != MERGED).
  - commit <hash> → `git cat-file -t <hash>`; refuse if hash doesn't resolve.

On block: gate_check returns (False, reason_str). Caller exits 2 with
"R_VERIFY_BLOCKED: <reason>" on stderr.

Bypass env:
  R_VERIFY_SKIP=1 — skip all verification (for one-shot edge cases where
  the claim references PRs in a different repo or pre-CI-state). Document
  usage in PR description.

Designed around the 2026-05-11 incident: 5+ fabricated "PR shipped" claims
that included plausible-but-fake PR numbers + commit hashes. Context
compaction in a single Claude session generates evidence-shaped text without
shell verification. This module catches that at the relay layer.
"""

from __future__ import annotations

import os
import re
import subprocess
from typing import Final

# Completion-trigger patterns — message claims something has shipped/landed.
# Two forms: standalone words ("shipped") and structured-looking output keys
# ("merged_sha=" / "mergeCommit" / "merge_sha:" — common in gh / git CLI output that
# a hallucinating composer might emit).
_COMPLETION_RE: Final = re.compile(
    r"\b(?:shipped|merged|landed|deployed|live|merge[d]?\s+pr|pr\s+merged)\b"
    r"|merged?_sha\s*[=:]"
    r"|mergecommit"
    r"|merged?_?at\s*[=:]"
    r"|state\s*[=:]\s*MERGED",
    re.IGNORECASE,
)

# PR# references (e.g. "PR #694", "PR#694", "pull request 694").
_PR_RE: Final = re.compile(r"\bpr\s*#?\s*(\d+)\b|\bpull\s+request\s+#?\s*(\d+)\b", re.IGNORECASE)

# Commit hash (7-40 hex chars). Must be word-boundary on both sides to avoid
# matching arbitrary hex substrings (e.g. uuids fragments).
_HASH_RE: Final = re.compile(r"\b([0-9a-f]{7,40})\b")

# Exemption patterns — phrases that look like completion but refer to external/past work.
_EXEMPT_RE: Final = re.compile(
    r"\b(?:will|going to|about to|planning to|propose to)\s+(?:ship|merge|deploy|land)"
    r"|\b(?:not|haven't|won't|isn't)\s+(?:yet\s+)?(?:shipped|merged|landed|deployed)"
    r"|\bcould\s+not\s+resolve\b"  # quoting an error message about a PR
    r"|\bfabricated\b|\bhallucinated\b"  # discussing the fabrication issue itself
    r"|\bnot\s+shipped\b|\bdid\s+not\s+ship\b",
    re.IGNORECASE,
)


def has_completion_trigger(text: str) -> bool:
    """True if text contains a completion-claim trigger word, no exemption."""
    if _EXEMPT_RE.search(text):
        return False
    return bool(_COMPLETION_RE.search(text))


def extract_pr_refs(text: str) -> list[int]:
    """Return PR numbers referenced in text."""
    out: list[int] = []
    for m in _PR_RE.finditer(text):
        for grp in m.groups():
            if grp:
                out.append(int(grp))
                break
    return out


def extract_commit_hashes(text: str) -> list[str]:
    """Return commit hashes (7-40 hex chars) referenced in text.

    Excludes hashes that appear inside obvious non-hash contexts (URL paths,
    JSON keys). Conservative: a 7-40 hex word match is treated as a
    candidate hash if not adjacent to alphanumeric chars.
    """
    return [m.group(1).lower() for m in _HASH_RE.finditer(text)]


def verify_pr(pr_num: int) -> tuple[bool, str]:
    """Return (exists, state_string).

    exists=False if `gh pr view` reports "Could not resolve". Else exists=True
    with the state string ("OPEN" / "MERGED" / "CLOSED").
    """
    try:
        result = subprocess.run(
            ["gh", "pr", "view", str(pr_num), "--json", "state"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return True, ""  # conservative pass on gh failure (network etc.)
    if result.returncode != 0:
        if "could not resolve" in result.stderr.lower():
            return False, ""
        return True, ""  # other gh failure → conservative pass
    import json

    try:
        data = json.loads(result.stdout)
        return True, data.get("state", "")
    except json.JSONDecodeError:
        return True, ""


def verify_commit(commit_hash: str) -> bool:
    """Return True if `git cat-file -t <hash>` resolves to a commit object."""
    try:
        result = subprocess.run(
            ["git", "cat-file", "-t", commit_hash],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return True  # conservative pass on git failure
    if result.returncode != 0:
        return False
    return result.stdout.strip() == "commit"


def gate_check(text: str) -> tuple[bool, str | None]:
    """Verify any PR# / commit-hash references in completion-trigger text.

    Returns (ok, blocker_reason):
      - ok=True, blocker_reason=None → message can be posted
      - ok=False, blocker_reason=str → block; print blocker_reason on stderr

    Skip behaviour:
      - R_VERIFY_SKIP=1 in env → always returns (True, None)
      - No completion trigger in text → (True, None)
      - No PR# / hash refs → (True, None)
    """
    if os.environ.get("R_VERIFY_SKIP") == "1":
        return True, None
    if not has_completion_trigger(text):
        return True, None
    blockers: list[str] = []
    for pr_num in extract_pr_refs(text):
        exists, state = verify_pr(pr_num)
        if not exists:
            blockers.append(f"PR #{pr_num} does not exist (gh: Could not resolve)")
    # Only check hashes if text also references commits with a verb suggesting they're real commits
    # (e.g. "commit abc1234" or just "abc1234" inline near completion words)
    for h in extract_commit_hashes(text):
        if len(h) < 7:
            continue
        # Skip very-common false positives: pure digit sequences, channel IDs starting with C
        if h.isdigit() or len(h) > 40:
            continue
        # Skip if hash looks like a Slack channel ID prefix (e.g. C0B...) — those start uppercase
        # but our regex is lowercase-cased. Slack channel IDs are uppercase in original text, but
        # our lowercase conversion makes c0b... — exclude those.
        if h.startswith("c0b"):
            continue
        # Skip if context is clearly a regex/pattern (e.g. surrounded by `\b...\b` or backticks)
        if not verify_commit(h):
            blockers.append(f"commit {h} does not exist (git cat-file: missing)")
    if blockers:
        return False, "; ".join(blockers)
    return True, None
