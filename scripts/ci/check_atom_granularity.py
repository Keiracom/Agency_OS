#!/usr/bin/env python3
"""check_atom_granularity.py — CI gate enforcing the atom-granularity spec.

Spec: docs/architecture/atom_granularity_spec.md (Agency_OS-3g9t, Wave 1
CUTOVER GATE). Per GOV-12 ("Gates As Code, Not Comments") this is the
runtime executable conditional, not documentation.

Scans configurable locations for atom-shaped JSON / JSONL files and
validates each row against the spec via
`src.keiracom_system.memory.atom_granularity.validate_atom`. Mirrors the
existing CI gate pattern (`scripts/ci/check_migration_manifest.py`):
deterministic exit codes, --report mode for inspection, --paths to override
scan locations.

EXIT CODES:
  0 — all atoms pass OR no atoms found in scan locations
  1 — at least one atom violates the spec (gate FAILS)
  2 — config error (malformed JSON, scan location wrong)

USAGE:
    python3 scripts/ci/check_atom_granularity.py
    python3 scripts/ci/check_atom_granularity.py --report
    python3 scripts/ci/check_atom_granularity.py --paths path1.jsonl,path2.json
    KEIRACOM_ATOM_SCAN_PATHS=p1.jsonl:p2.json python3 scripts/ci/check_atom_granularity.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.keiracom_system.memory.atom_granularity import (  # noqa: E402
    GranularityRules,
    ValidationOutcome,
    validate_atom,
)

DEFAULT_SCAN_PATHS: tuple[str, ...] = (
    "tests/keiracom_system/memory/fixtures/atoms/*.json",
    "tests/keiracom_system/memory/fixtures/atoms/*.jsonl",
)
SCAN_PATHS_ENV = "KEIRACOM_ATOM_SCAN_PATHS"


def _resolve_paths(arg_paths: str | None) -> list[Path]:
    """Resolve scan paths from --paths arg, env var, or defaults.

    --paths beats env beats defaults. Globs are expanded against REPO_ROOT.
    """
    raw: list[str]
    if arg_paths:
        raw = [p.strip() for p in arg_paths.split(",") if p.strip()]
    else:
        env = os.environ.get(SCAN_PATHS_ENV, "")
        raw = (
            [p.strip() for p in env.replace(":", ",").split(",") if p.strip()]
            if env
            else list(DEFAULT_SCAN_PATHS)
        )
    out: list[Path] = []
    for pattern in raw:
        candidate = Path(pattern)
        if candidate.is_absolute():
            out.extend(sorted(candidate.parent.glob(candidate.name)))
            continue
        out.extend(sorted(REPO_ROOT.glob(pattern)))
    return out


def _load_atoms(path: Path) -> list[dict]:
    """Load atoms from a JSON or JSONL file. Returns list[dict].

    JSON file may be either a top-level list or a top-level dict with
    `atoms` key. JSONL is one atom per line.
    """
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        out = []
        for line_no, line in enumerate(text.splitlines(), start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"{path}:{line_no} JSON parse error: {e}") from e
            if not isinstance(parsed, dict):
                raise RuntimeError(f"{path}:{line_no} expected dict, got {type(parsed).__name__}")
            out.append(parsed)
        return out
    # .json — array OR {atoms: [...]} OR {memories: [...]}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"{path} JSON parse error: {e}") from e
    if isinstance(parsed, list):
        return [p for p in parsed if isinstance(p, dict)]
    if isinstance(parsed, dict):
        for key in ("atoms", "memories", "rows"):
            if key in parsed and isinstance(parsed[key], list):
                return [p for p in parsed[key] if isinstance(p, dict)]
    raise RuntimeError(
        f"{path} unsupported JSON shape; expected list[dict] or {{atoms|memories|rows: list[dict]}}"
    )


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _format_outcome(path: Path, idx: int, outcome: ValidationOutcome) -> str:
    rules_listing = ", ".join(f"{v.rule_id}: {v.detail}" for v in outcome.violations)
    return f"{_display_path(path)}[#{idx} atom_id={outcome.atom_id}] -> {rules_listing}"


def _run(paths: list[Path], *, report: bool) -> int:
    rules = GranularityRules()
    total_atoms = 0
    total_violations: list[str] = []
    if not paths:
        print(
            "OK (atom-granularity): no atom-shaped fixtures found in scan paths — gate inactive.\n"
            "Override scan paths via --paths or "
            f"{SCAN_PATHS_ENV} env var."
        )
        return 0
    for path in paths:
        if not path.is_file():
            continue
        try:
            atoms = _load_atoms(path)
        except RuntimeError as e:
            print(f"ERROR (atom-granularity): {e}", file=sys.stderr)
            return 2
        for idx, atom in enumerate(atoms):
            total_atoms += 1
            outcome = validate_atom(atom, rules=rules)
            if not outcome.ok:
                total_violations.append(_format_outcome(path, idx, outcome))
            elif report:
                print(
                    f"OK {_display_path(path)}[#{idx} atom_id={outcome.atom_id}]"
                    + (f" (exempt: {outcome.exempt_reason})" if outcome.exempt_reason else "")
                )
    if total_violations:
        print(f"FAIL (atom-granularity): {len(total_violations)} atom(s) violate the spec:")
        for line in total_violations:
            print(f"  - {line}")
        return 1
    print(f"OK (atom-granularity): all {total_atoms} atom(s) pass.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0] if __doc__ else None)
    parser.add_argument(
        "--paths",
        help=(
            f"Comma-separated glob patterns (relative to repo root or absolute). "
            f"Defaults: {','.join(DEFAULT_SCAN_PATHS)}. Env override: {SCAN_PATHS_ENV}."
        ),
    )
    parser.add_argument(
        "--report", action="store_true", help="print OK lines too, not only failures"
    )
    args = parser.parse_args(argv)
    paths = _resolve_paths(args.paths)
    return _run(paths, report=args.report)


if __name__ == "__main__":
    sys.exit(main())
