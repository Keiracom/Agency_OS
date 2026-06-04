#!/usr/bin/env python3
"""import_closure.py — deterministic AST import-closure curation for keiracom-core.

Repo-split classification (ceo:rule:repo_split_classification_and_guarantees):
PRIMARY = dependency graph from KeiraCom's LIVE entrypoints; whatever the running
code reaches transitively IS KeiraCom. Usage-derived, so it cannot omit a file
the running code actually imports. This tool computes that closure deterministically
(stdlib `ast` — grimp absent) and reports KEEP / REMOVE for src/, plus the dead
top-level dirs.

SEEDS = every python ExecStart target across ALL base ~/.config/systemd/user/
*.service AND *.service.d/*.conf drop-ins, parsing `-m src.X`, `src/X.py`,
`uvicorn src.X:app`, and the launcher `vault-envwrap -- <python> <target>` form
(the effective entrypoint is after `--`). Plus the dispatcher's spawn entrypoint
(agent_cold_start). Conservative: a seed file that no longer exists is reported
(dangling) but skipped; over-keeping is safe, under-keeping breaks boot.

CLOSURE = transitive first-party (`src.*`) imports from every seed, walking ALL
import nodes (module-level AND lazy/function-level via ast.walk), keeping every
reached src/ module file + all ancestor __init__.py (importability).

Usage:
    python3 scripts/repo_split/import_closure.py [--json OUT] [--extra-seed src/x.py ...]
Exit 0 = closure computed + the 4 known live-edge files all landed in KEEP.
Exit 2 = a known live-edge file is REMOVE (seed set incomplete — DO NOT curate).
"""

from __future__ import annotations

import argparse
import ast
import glob
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SYSTEMD = Path.home() / ".config" / "systemd" / "user"
WORKTREE_RE = re.compile(r"(?:/home/elliotbot/clawd/Agency_OS[^/]*/|%h/clawd/Agency_OS[^/]*/)")

# The 4 known live-edge files that MUST land in KEEP (sanity assert; if any is
# REMOVE the seed set is incomplete).
KNOWN_EDGES = (
    "src/retrieval/retrieval_orchestrator.py",  # <- dispatcher.main
    "src/intelligence/gemini_client.py",  # <- keiracom chat / orchestration
    "src/services/sdk_usage_service.py",  # <- keiracom
    "src/api/webhooks/linear.py",  # <- slack_bot
)

# Dead top-level dirs removed wholesale (not src/, not closure-derived).
DEAD_DIRS = (
    "agency-os-html",
    "agency-os-prototype",
    "builds",
    "campaigns",
    "canvas",
    "competitive",
    "frontend",
    "landing-page-analysis",
    "maya-concepts",
    "research",
)

# Non-systemd entrypoints (spawned, not a unit). agent_cold_start is the
# dispatcher's DISPATCHER_AGENT_COMMAND spawn target.
EXTRA_SEEDS = ("src/keiracom_system/vault/agent_cold_start.py",)


def _rel(p: str) -> str:
    return WORKTREE_RE.sub("", p).lstrip("./")


def module_to_file(mod: str) -> str | None:
    """Dotted first-party module -> repo-relative file, or None. Tries the full
    name then shorter prefixes (so `import src.a.b.attr` resolves to src/a/b.py)."""
    if not mod.startswith("src"):
        return None
    parts = mod.split(".")
    while parts:
        p = "/".join(parts)
        for cand in (f"{p}.py", f"{p}/__init__.py"):
            if (REPO / cand).is_file():
                return cand
        parts = parts[:-1]
    return None


def file_to_module(rel: str) -> str:
    rel = rel[:-3] if rel.endswith(".py") else rel
    if rel.endswith("/__init__"):
        rel = rel[: -len("/__init__")]
    return rel.replace("/", ".")


def file_to_package(rel: str) -> str:
    """The package a file lives in, dotted (for relative-import resolution)."""
    mod = file_to_module(rel)
    if rel.endswith("/__init__.py"):
        return mod  # a package's own __init__ — its package IS itself
    return ".".join(mod.split(".")[:-1])


def first_party_imports(rel: str) -> set[str]:
    """All first-party src.* module FILES referenced by `rel` (any import node)."""
    try:
        tree = ast.parse((REPO / rel).read_text(encoding="utf-8"), filename=rel)
    except (OSError, SyntaxError):
        return set()
    pkg = file_to_package(rel)
    out: set[str] = set()

    def keep(modname: str) -> None:
        f = module_to_file(modname)
        if f:
            out.add(f)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                keep(a.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                base_parts = pkg.split(".")
                base_parts = (
                    base_parts[: len(base_parts) - (node.level - 1)]
                    if node.level > 1
                    else base_parts
                )
                base = ".".join(base_parts)
                mod = f"{base}.{node.module}" if node.module else base
            else:
                mod = node.module or ""
            if not mod.startswith("src"):
                continue
            keep(mod)
            for a in node.names:  # `from src.a.b import c` -> also try src.a.b.c
                keep(f"{mod}.{a.name}")
    return out


def discover_seeds() -> tuple[list[str], list[str]]:
    """Return (existing_seed_files, dangling_targets). Reads base + drop-in
    ExecStart, parses every python target form incl vault-envwrap."""
    targets: set[str] = set()
    files = glob.glob(f"{SYSTEMD}/*.service") + glob.glob(f"{SYSTEMD}/*.service.d/*.conf")
    for f in files:
        try:
            lines = Path(f).read_text(errors="ignore").splitlines()
        except OSError:
            continue
        for ln in lines:
            s = ln.strip()
            if not s.startswith("ExecStart=") or s == "ExecStart=":
                continue
            body = s.split("ExecStart=", 1)[1].strip().lstrip("-+@!:")
            toks = body.split()
            if "--" in toks:  # vault-envwrap -- <python> <target...>
                toks = toks[toks.index("--") + 1 :]
            for i, t in enumerate(toks):
                if t == "-m" and i + 1 < len(toks):
                    targets.add(("module", toks[i + 1]))
                    break
                if t.endswith(".py"):
                    targets.add(("script", t))
                    break
                if t == "uvicorn" and i + 1 < len(toks):
                    targets.add(("uvicorn", toks[i + 1]))
                    break
                if ":app" in t and "/" not in t:
                    targets.add(("uvicorn", t))
                    break
    existing: set[str] = set()
    dangling: list[str] = []
    for kind, val in sorted(targets):
        if kind in ("module", "uvicorn"):
            f = module_to_file(val.split(":")[0])
            (existing.add(f) if f else dangling.append(val))
        else:
            rel = _rel(val)
            if (REPO / rel).is_file():
                existing.add(rel)
            elif rel.startswith(("src/", "scripts/")):
                dangling.append(rel)  # repo entrypoint referenced but file ABSENT
            # else: external path / flag (other repo, log artifact) — not ours
    for s in EXTRA_SEEDS:
        if (REPO / s).is_file():
            existing.add(s)
    return sorted(existing), sorted(set(dangling))


def ancestors_init(rel: str) -> set[str]:
    """Every ancestor __init__.py from src/ down to the file's dir."""
    out: set[str] = set()
    parts = rel.split("/")[:-1]  # drop filename
    for i in range(1, len(parts) + 1):
        init = "/".join(parts[:i]) + "/__init__.py"
        if (REPO / init).is_file():
            out.add(init)
    return out


def build_closure(seed_files: list[str]) -> set[str]:
    """BFS: from every seed file, follow first-party src.* imports transitively.
    Returns the KEEP set of repo-relative src/ files (+ ancestor __init__.py)."""
    keep: set[str] = set()
    work: list[str] = []
    for s in seed_files:
        if s.startswith("src/"):
            work.append(s)
        else:  # scripts/ (or other) entrypoint — seed via its src imports
            work.extend(first_party_imports(s))
    while work:
        f = work.pop()
        if not f.startswith("src/") or f in keep:
            continue
        keep.add(f)
        for imp in first_party_imports(f):
            if imp not in keep:
                work.append(imp)
    for f in list(keep):
        keep |= ancestors_init(f)
    return keep


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None)
    ap.add_argument("--extra-seed", action="append", default=[])
    args = ap.parse_args()

    seeds, dangling = discover_seeds()
    seeds = sorted(set(seeds) | {s for s in args.extra_seed if (REPO / s).is_file()})
    keep = build_closure(seeds)

    all_src = {os.path.relpath(str(p), str(REPO)) for p in (REPO / "src").rglob("*.py")}
    remove = sorted(all_src - keep)

    # Sanity assert: the 4 known live-edge files must be KEEP.
    edge_fail = [e for e in KNOWN_EDGES if e not in keep]

    print(f"seeds discovered (existing entrypoint files): {len(seeds)}")
    print(f"dangling ExecStart targets (referenced, file ABSENT): {len(dangling)}")
    for d in dangling:
        print(f"  DANGLING: {d}")
    print(f"src/ total .py: {len(all_src)}  |  KEEP: {len(keep)}  |  REMOVE: {len(remove)}")
    print("─── 4 known live-edge files (MUST be KEEP) ───")
    for e in KNOWN_EDGES:
        print(f"  {'KEEP ✓' if e in keep else 'REMOVE ✗ !!!'}  {e}")

    if args.json:
        Path(args.json).write_text(
            json.dumps(
                {
                    "seeds": seeds,
                    "dangling": dangling,
                    "keep": sorted(keep),
                    "remove": remove,
                    "dead_dirs": [d for d in DEAD_DIRS if (REPO / d).is_dir()],
                    "edge_check_failed": edge_fail,
                },
                indent=2,
            )
        )
        print(f"\nmanifest → {args.json}")

    if edge_fail:
        print(
            f"\nEDGE CHECK FAILED — seed set INCOMPLETE, do NOT curate: {edge_fail}",
            file=sys.stderr,
        )
        return 2
    print("\nEDGE CHECK PASS — all 4 known live-edge files are in KEEP.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
