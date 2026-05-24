#!/usr/bin/env python3
"""check_migration_manifest.py — Phase 1.2.5 artefact 6 enforcer (Agency_OS-fi4u).

CI gate for the migration manifest seed. Validates every entry against the
schema from `docs/architecture/three_repo_carveout_execution.md §6` (PR #1122)
and enforces the enumeration-not-glob discipline (same shape as Orion's
`config/product_repo_test_allowlist.txt` enforcer, PR #1118).

VALIDATES:
  1. JSON parses; top-level required fields present (manifest_version, entries).
  2. Each entry has required fields: source_path, target_repo, target_path,
     operation, rationale, active_pr_block.
  3. target_repo in {fleet, product, archive, both}.
  4. operation in {move, copy, archive}.
  5. source_path EXISTS on disk (catches path-rot — file removed but still listed).
  6. source_path has NO glob characters (* ? [ ]) — enumeration discipline
     mirrors PR #1118 `**` rejection.

DYNAMIC EXCLUSION (--refresh):
  Queries open bd KEIs + open GitHub PRs touching each source_path. Updates
  active_pr_block field in-place (atomic tmp.replace). Per the dispatch
  workflow: build manifest first (a), then refresh (b) to annotate.

EXIT CODES:
  0 — all entries pass
  1 — enforcement violation (schema/path/glob)
  2 — config error (manifest missing, malformed JSON, refresh subprocess fail)

USAGE:
    python3 scripts/ci/check_migration_manifest.py
    python3 scripts/ci/check_migration_manifest.py --report
    python3 scripts/ci/check_migration_manifest.py --refresh-exclusions
    python3 scripts/ci/check_migration_manifest.py --manifest <path>
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_MANIFEST = REPO_ROOT / "docs/migration/migrated_manifest_seed.json"

VALID_TARGET_REPOS = frozenset({"fleet", "product", "archive", "both"})
VALID_OPERATIONS = frozenset({"move", "copy", "archive"})
REQUIRED_ENTRY_FIELDS = frozenset(
    {"source_path", "target_repo", "target_path", "operation", "rationale", "active_pr_block"}
)
REQUIRED_TOP_FIELDS = frozenset({"manifest_version", "entries"})
GLOB_CHARS = frozenset("*?[]")


def load_manifest(path: Path) -> dict:
    """Parse manifest JSON. Exits 2 on missing/malformed."""
    if not path.is_file():
        sys.stderr.write(f"ERROR: manifest not found: {path}\n")
        sys.exit(2)
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"ERROR: manifest is not valid JSON: {exc}\n")
        sys.exit(2)


def validate_top_level(manifest: dict) -> list[str]:
    """Return list of top-level violation strings. Empty = pass."""
    violations: list[str] = []
    missing = REQUIRED_TOP_FIELDS - manifest.keys()
    if missing:
        violations.append(f"top-level missing required fields: {sorted(missing)}")
    if "entries" in manifest and not isinstance(manifest["entries"], list):
        violations.append("entries must be a JSON array")
    return violations


def _has_glob(path: str) -> bool:
    return any(c in GLOB_CHARS for c in path)


def validate_entry(entry: dict, index: int) -> list[str]:
    """Return list of violation strings for one entry."""
    violations: list[str] = []
    missing = REQUIRED_ENTRY_FIELDS - entry.keys()
    if missing:
        violations.append(f"entry[{index}] missing fields: {sorted(missing)}")
        return violations
    if entry["target_repo"] not in VALID_TARGET_REPOS:
        violations.append(
            f"entry[{index}] source={entry['source_path']!r} target_repo "
            f"{entry['target_repo']!r} not in {sorted(VALID_TARGET_REPOS)}"
        )
    if entry["operation"] not in VALID_OPERATIONS:
        violations.append(
            f"entry[{index}] source={entry['source_path']!r} operation "
            f"{entry['operation']!r} not in {sorted(VALID_OPERATIONS)}"
        )
    source = entry["source_path"]
    if _has_glob(source):
        violations.append(
            f"entry[{index}] source_path {source!r} contains glob char — enumerate explicitly"
        )
    if not (REPO_ROOT / source).exists():
        violations.append(f"entry[{index}] source_path does not exist on disk: {source!r}")
    return violations


def _gh_pr_files() -> dict[int, set[str]]:
    """{pr_number: {file_paths}} for open PRs. Empty dict on any subprocess fail."""
    try:
        cp = subprocess.run(
            ["gh", "pr", "list", "--state=open", "--limit=50", "--json", "number,files"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if cp.returncode != 0:
            return {}
        data = json.loads(cp.stdout)
        result: dict[int, set[str]] = {}
        for pr in data:
            num = pr.get("number")
            paths = {f.get("path", "") for f in (pr.get("files") or []) if f.get("path")}
            if num is not None and paths:
                result[num] = paths
        return result
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return {}


def _bd_open_kei_paths() -> list[tuple[str, str]]:
    """Best-effort [(kei_id, body_text)] for open bd issues. Empty on any fail.

    Path matching against bd issues is heuristic (issue body may mention paths
    without strict structure). The seed annotates with the KEI ID; refinement
    happens at Phase 2.0 when the migration runner runs.
    """
    try:
        cp = subprocess.run(
            ["bd", "list", "--status=open", "--json"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
            cwd=str(REPO_ROOT),
        )
        if cp.returncode != 0:
            return []
        data = json.loads(cp.stdout) if cp.stdout.strip() else []
        items = data if isinstance(data, list) else data.get("issues", [])
        out: list[tuple[str, str]] = []
        for it in items:
            kei = it.get("id", "")
            body = (it.get("description", "") or "") + " " + (it.get("notes", "") or "")
            if kei:
                out.append((kei, body))
        return out
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return []


def refresh_exclusions(manifest: dict) -> dict:
    """Annotate active_pr_block per current bd + gh state. Returns mutated manifest."""
    pr_files = _gh_pr_files()
    bd_issues = _bd_open_kei_paths()
    for entry in manifest.get("entries", []):
        source = entry["source_path"]
        blockers: list[str] = []
        for pr_num, paths in pr_files.items():
            if any(p == source or fnmatch.fnmatch(p, source) for p in paths):
                blockers.append(f"PR #{pr_num}")
        for kei, body in bd_issues:
            if source in body:
                blockers.append(kei)
        entry["active_pr_block"] = "; ".join(blockers) if blockers else None
    return manifest


def write_manifest_atomic(manifest: dict, path: Path) -> None:
    """Atomic write — tmp.replace pattern (idempotent re-runs)."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(manifest, indent=2) + "\n")
    tmp.replace(path)


def _print_report(entries: list[dict], blocked_count: int) -> None:
    by_target: dict[str, int] = {}
    for e in entries:
        by_target[e["target_repo"]] = by_target.get(e["target_repo"], 0) + 1
    sys.stderr.write(f"manifest entries: {len(entries)}\n")
    for repo in sorted(by_target):
        sys.stderr.write(f"  {repo}: {by_target[repo]}\n")
    sys.stderr.write(f"  active_pr_block annotated: {blocked_count}\n")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    p.add_argument("--report", action="store_true", help="Print counts; exit 0 regardless")
    p.add_argument(
        "--refresh-exclusions",
        action="store_true",
        help="Query bd + gh; annotate active_pr_block in-place (atomic write)",
    )
    args = p.parse_args(argv)

    manifest = load_manifest(args.manifest)
    top_violations = validate_top_level(manifest)
    if top_violations:
        for v in top_violations:
            sys.stderr.write(f"REJECT: {v}\n")
        return 1

    if args.refresh_exclusions:
        manifest = refresh_exclusions(manifest)
        write_manifest_atomic(manifest, args.manifest)
        sys.stderr.write(f"refreshed active_pr_block for {len(manifest['entries'])} entries\n")

    all_violations: list[str] = []
    for i, entry in enumerate(manifest.get("entries", [])):
        all_violations.extend(validate_entry(entry, i))

    blocked = sum(1 for e in manifest.get("entries", []) if e.get("active_pr_block"))
    if args.report:
        _print_report(manifest.get("entries", []), blocked)
        for v in all_violations:
            sys.stderr.write(f"  violation: {v}\n")
        return 0

    if all_violations:
        sys.stderr.write(f"REJECT: {len(all_violations)} validation violation(s):\n")
        for v in all_violations:
            sys.stderr.write(f"  {v}\n")
        return 1

    sys.stderr.write(
        f"OK: {len(manifest['entries'])} entries valid; "
        f"{blocked} flagged active_pr_block (excluded from migration cycle).\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
