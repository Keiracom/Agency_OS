"""generator.py — orchestrator: compress → claude → SKILL.md → PR.

End-to-end pipeline for Drevon PR-B internal tooling. Each step is split so
callers / tests can substitute components.

Naming: skill name is derived from the dominant tool pattern or an explicit
override. Heuristic in `derive_skill_name()`.

PR opener uses `gh pr create` via subprocess; tests inject a stub.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.skill_gen.claude_invoke import ClaudeResult, invoke
from src.skill_gen.extractor import CompressedSession, compress

_SKILL_PROMPT_TEMPLATE = """\
You are generating a reusable SKILL.md from a captured Claude Code session.

The session record below summarises one directive end-to-end: which tools were
called, in what order, which files were touched, which errors surfaced, and
the user messages that bounded the work.

Synthesise a single SKILL.md following this exact shape:

---
name: <kebab-case-name>
description: <one-line, action-oriented>
---
# <Title Case Name>

## When to use
- <bullet> 3-5 bullets describing the situations this skill matches

## Steps
1. <imperative> 4-8 numbered steps capturing the working pattern

## Failure modes
- <bullet> 2-4 bullets pulled from the `errors` field below

## Verification
- <bullet> 2-3 verification commands or signals

Keep the output under 80 lines. Do NOT echo the input session JSON. Do NOT
include narrative outside the SKILL.md body.

SESSION:
```json
{session_json}
```
"""

_NAME_SAFE_RE = re.compile(r"[^a-z0-9-]+")


@dataclass(frozen=True)
class GenerateResult:
    skill_path: Path
    skill_name: str
    pr_url: str | None
    claude: ClaudeResult


def derive_skill_name(session: CompressedSession, override: str | None) -> str:
    """Pick a kebab-case slug for the new skill directory."""
    if override:
        return _NAME_SAFE_RE.sub("-", override.lower()).strip("-") or "untitled-skill"
    if session["tool_call_freq"]:
        dominant = max(session["tool_call_freq"].items(), key=lambda kv: kv[1])[0]
        slug = _NAME_SAFE_RE.sub("-", dominant.lower()).strip("-")
        return f"{slug}-pattern" if slug else "captured-pattern"
    return "captured-pattern"


def build_prompt(session: CompressedSession) -> str:
    return _SKILL_PROMPT_TEMPLATE.format(session_json=json.dumps(session, indent=2, default=str))


def write_skill(repo_root: Path, skill_name: str, body: str, *, overwrite: bool = False) -> Path:
    """Write skills/<skill_name>/SKILL.md. Returns the file path."""
    skill_dir = repo_root / "skills" / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_path = skill_dir / "SKILL.md"
    if skill_path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing skill: {skill_path}")
    skill_path.write_text(body)
    return skill_path


def open_pr(
    repo_root: Path,
    skill_path: Path,
    directive_ref: str,
    *,
    runner=subprocess.run,
) -> str | None:
    """Open a PR for the new skill. Returns the PR URL or None on failure.

    Caller (or CI) is responsible for branch creation + push. This function
    assumes the branch is already pushed and `gh` is authenticated.
    """
    title = f"[ATLAS] feat(skills): auto-generated from {directive_ref}"
    body = (
        f"Auto-generated SKILL.md from Drevon PR-B skill-gen pipeline.\n\n"
        f"Source directive: {directive_ref}\n"
        f"Skill path: `{skill_path.relative_to(repo_root)}`\n\n"
        "Review for accuracy before merging."
    )
    result = runner(
        ["gh", "pr", "create", "--title", title, "--body", body],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        check=False,
    )
    if result.returncode != 0:
        return None
    out = (result.stdout or "").strip()
    return out or None


def generate(
    repo_root: Path,
    session_id: str,
    start_ts: str,
    end_ts: str,
    directive_ref: str,
    *,
    skill_name_override: str | None = None,
    overwrite: bool = False,
    claude_runner=None,
    pr_runner=subprocess.run,
    extractor_overrides: dict[str, Any] | None = None,
) -> GenerateResult:
    """End-to-end: compress → claude → write → PR.

    Injection points:
        - `claude_runner`: replaces subprocess.run in claude_invoke.invoke
        - `pr_runner`: replaces subprocess.run in open_pr
        - `extractor_overrides`: keyword args forwarded to `compress()`
    """
    compress_kwargs = extractor_overrides or {}
    session = compress(session_id, start_ts, end_ts, **compress_kwargs)
    prompt = build_prompt(session)
    invoke_kwargs: dict[str, Any] = {}
    if claude_runner is not None:
        invoke_kwargs["runner"] = claude_runner
    claude_result = invoke(prompt, **invoke_kwargs)
    if claude_result.returncode != 0:
        raise RuntimeError(
            f"claude invocation failed (exit {claude_result.returncode}): "
            f"{claude_result.stderr[:500]}"
        )
    skill_name = derive_skill_name(session, skill_name_override)
    skill_path = write_skill(repo_root, skill_name, claude_result.stdout, overwrite=overwrite)
    pr_url = open_pr(repo_root, skill_path, directive_ref, runner=pr_runner)
    return GenerateResult(
        skill_path=skill_path,
        skill_name=skill_name,
        pr_url=pr_url,
        claude=claude_result,
    )
