"""Skills directory atomizer — Week 2 acceptance criterion.

Walks `skills/` directory (or any provided root), runs Atomizer + Verifier
on each markdown skill file, stores atoms + edges + job rows. Dry-run by
default; --execute flag required to write.

Mirrors the operator-script pattern from PR #1172 / #1174 / #1176 hand-
migrations (dry-run default, idempotent state-file, fail-loud on errors).

State file at runtime/skills_atomization_state.jsonl records each (skill_path,
job_id, status) so re-runs skip already-atomized skills. Safe to abort + resume.

Acceptance per Elliot dispatch: "Week 2: full skills directory atomized +
retrieval working + composer prototype." This module handles the first half;
retriever.py + composer.py cover the second + third.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from src.keiracom_system.atomization.atomizer import Atomizer, is_atomizer_enabled

log = logging.getLogger("skills_atomizer")

DEFAULT_SKILLS_ROOT = Path("skills")
DEFAULT_STATE_FILE = Path("runtime/skills_atomization_state.jsonl")
DEFAULT_SOURCE_KIND = "skill"

# Cap on file size we'll send to Gemini Flash. Skills over this are skipped
# with a warning — atomization works on document-scale prose, not 50KB monsters.
MAX_SKILL_BYTES: int = 50_000


class SkillsAtomizerError(RuntimeError):
    """Raised on operator-side errors (bad config, missing skills root, etc.)."""


def iter_skill_files(root: Path) -> Iterable[Path]:
    """Yield all *.md files under `root` recursively, sorted for determinism."""
    if not root.is_dir():
        raise SkillsAtomizerError(f"skills root {root} not a directory")
    yield from sorted(root.rglob("*.md"))


def load_state(path: Path) -> set[str]:
    """Read the state file; return set of already-atomized source_refs."""
    if not path.exists():
        return set()
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            if row.get("ok") and row.get("source_ref"):
                seen.add(row["source_ref"])
        except json.JSONDecodeError:
            continue
    return seen


def append_state(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")


def atomize_skill(
    *,
    atomizer: Atomizer,
    skill_path: Path,
    skills_root: Path,
) -> tuple[bool, str]:
    """Atomize one skill file. Returns (ok, info)."""
    content = skill_path.read_text(encoding="utf-8")
    if len(content.encode("utf-8")) > MAX_SKILL_BYTES:
        return False, f"skill {skill_path} exceeds MAX_SKILL_BYTES={MAX_SKILL_BYTES}"
    # source_ref is relative to skills_root for portability.
    try:
        rel = skill_path.relative_to(skills_root)
    except ValueError:
        rel = skill_path
    source_ref = f"skills/{rel}"
    try:
        job = atomizer.atomize(
            source_ref=source_ref,
            source_kind=DEFAULT_SOURCE_KIND,
            source_text=content,
        )
        return True, f"job_id={job.job_id} atoms={job.atoms_produced}"
    except Exception as exc:  # noqa: BLE001
        log.warning("atomize failed for %s: %s", skill_path, exc)
        return False, f"error: {exc}"


def run(
    *,
    atomizer: Atomizer,
    skills_root: Path,
    state_path: Path,
    execute: bool,
) -> int:
    """Walk skills/, atomize each. Returns rc=0 on clean, 1 on any failure."""
    if not skills_root.is_dir():
        log.error("skills_root %s missing", skills_root)
        return 2

    seen = load_state(state_path)
    log.info("state-file already-atomized: %d", len(seen))

    n_total = n_ok = n_fail = n_skip = 0
    for skill_path in iter_skill_files(skills_root):
        n_total += 1
        # Compute source_ref to match what atomize_skill would generate.
        try:
            rel = skill_path.relative_to(skills_root)
        except ValueError:
            rel = skill_path
        source_ref = f"skills/{rel}"

        if source_ref in seen:
            n_skip += 1
            log.debug("skip already-atomized: %s", source_ref)
            continue

        if not execute:
            log.info("dry-run: would atomize %s", source_ref)
            continue

        ok, info = atomize_skill(
            atomizer=atomizer,
            skill_path=skill_path,
            skills_root=skills_root,
        )
        row: dict[str, Any] = {
            "source_ref": source_ref,
            "ok": ok,
            "info": info,
        }
        append_state(state_path, row)
        if ok:
            n_ok += 1
        else:
            n_fail += 1
            log.warning("atomize %s FAILED: %s", source_ref, info)

    log.info(
        "summary: total=%d ok=%d fail=%d skip=%d (execute=%s)",
        n_total,
        n_ok,
        n_fail,
        n_skip,
        execute,
    )
    return 0 if n_fail == 0 else 1


def _check_feature_flag_or_warn() -> None:
    """Warn (don't fail) if KEIRACOM_ATOMIZER_ENABLED is off.

    The orchestration script itself doesn't gate on the flag (Atomizer is
    injected pre-constructed); but if ops runs this without the flag on,
    they may be surprised that the feature-flag-aware caller won't actually
    drive the atomization in production. Warn loudly.
    """
    if not is_atomizer_enabled():
        log.warning(
            "KEIRACOM_ATOMIZER_ENABLED is OFF — this run will execute even "
            "though the production feature flag would block atomization. "
            "Confirm intent before --execute."
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills-root", type=Path, default=DEFAULT_SKILLS_ROOT)
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE_FILE)
    parser.add_argument("--execute", action="store_true", help="atomize (default dry-run)")
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()


def main(argv: list[str] | None = None) -> int:
    """Module-as-script entry. Atomizer must be constructed by the caller —
    we don't import the Gemini key in this orchestration module to keep the
    LLM dependency explicit. Callers wire up Atomizer via the production
    bootstrap script.

    For dry-run on the current repo's skills/, this module-as-script can be
    invoked without a real Atomizer by mocking _build_atomizer in tests.
    """
    # Lazy-import the bootstrap so module imports don't fail without
    # GEMINI_API_KEY set (dry-run + tests work without it).
    args = _parse_args()
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(message)s")
    _check_feature_flag_or_warn()
    if not args.execute:
        # Dry-run path doesn't need an actual Atomizer; just walk + print.
        n = sum(1 for _ in iter_skill_files(args.skills_root))
        log.info("dry-run: %d skill files under %s", n, args.skills_root)
        return 0
    # Execute path needs a real Atomizer + Verifier; caller assembles via a
    # bootstrap module (out of scope for this orchestration script).
    log.error(
        "--execute requires Atomizer + AtomStore + Verifier construction; "
        "use scripts/bootstrap_atomize_skills.py instead (separate module)"
    )
    return 3


if __name__ == "__main__":
    sys.exit(main())
