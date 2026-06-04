#!/usr/bin/env python3
"""neg_test.py — objective validation gate for the keiracom-core curation.

Runs over the CURATED (post-removal) tree, against the COMPLETE entrypoint set
(systemd + Claude Code hooks + product + HoO-confirmed) — the SAME set used as
closure seeds (HoO standard: a services-only neg-test shares the systemd blind
spot that nearly archived the 42). Three objective checks:

  (a) COMPILE   — every kept src/*.py byte-compiles (py_compile).
  (b) RESOLVE   — every entrypoint's transitive first-party (src.*) imports all
                  resolve to a KEPT file in the curated tree (no import points at
                  a removed module). This is the deterministic "each entrypoint
                  resolves against the curated tree" — no runtime side effects.
  (c) ZERO-REF  — grep the curated tree (src/ + kept scripts) for any import of a
                  removed module = 0 (the clean-dependency guarantee).

Reads the manifest (seeds + remove) produced by import_closure.py.
Exit 0 = all three pass. Exit 1 = any failure (verbatim evidence printed).
"""

from __future__ import annotations

import ast
import json
import py_compile
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MANIFEST = REPO / "scripts" / "repo_split" / "closure_manifest.json"


def module_to_file(mod: str) -> str | None:
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


def first_party_imports(rel: str) -> set[str]:
    try:
        tree = ast.parse((REPO / rel).read_text(encoding="utf-8"), filename=rel)
    except (OSError, SyntaxError):
        return set()
    out: set[str] = set()
    mod_self = rel[:-3].replace("/", ".")
    pkg = ".".join(mod_self.split(".")[:-1])
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.startswith("src"):
                    out.add(a.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                bp = pkg.split(".")
                base = ".".join(bp[: len(bp) - (node.level - 1)] if node.level > 1 else bp)
                mod = f"{base}.{node.module}" if node.module else base
            else:
                mod = node.module or ""
            if mod.startswith("src"):
                out.add(mod)
                for a in node.names:
                    out.add(f"{mod}.{a.name}")
    return out


def main() -> int:
    m = json.loads(MANIFEST.read_text())
    seeds = [s for s in m["seeds"] if (REPO / s).is_file()]  # entrypoints still present
    removed = set(m["remove"])
    removed_mods = {f[:-3].replace("/", ".").removesuffix(".__init__") for f in removed}
    ok = True

    # (a) COMPILE every kept src/*.py
    kept = [str(p.relative_to(REPO)) for p in (REPO / "src").rglob("*.py")]
    fails = []
    for f in kept:
        try:
            py_compile.compile(str(REPO / f), doraise=True)
        except py_compile.PyCompileError as e:
            fails.append((f, str(e).splitlines()[0]))
    print(f"(a) COMPILE: {len(kept)} kept src/*.py compiled, {len(fails)} failures")
    for f, e in fails[:20]:
        print(f"    FAIL {f}: {e}")
    ok = ok and not fails

    # (b) RESOLVE: every entrypoint's transitive src imports resolve to a kept file
    visited: set[str] = set()
    work = list(seeds)
    unresolved: list[tuple[str, str]] = []
    while work:
        f = work.pop()
        if f in visited or not (REPO / f).is_file():
            continue
        visited.add(f)
        for imp in first_party_imports(f):
            # An import whose module (or a prefix) was removed = a broken edge.
            if any(imp == rm or imp.startswith(rm + ".") for rm in removed_mods):
                unresolved.append((f, imp))
                continue
            tgt = module_to_file(imp)
            if tgt is None:
                continue  # not a real first-party module (attribute import etc.)
            if tgt not in visited:
                work.append(tgt)
    print(
        f"(b) RESOLVE: {len(seeds)} entrypoints, walked {len(visited)} files, "
        f"{len(unresolved)} imports pointing at a MISSING (removed) module"
    )
    for f, imp in unresolved[:20]:
        print(f"    BROKEN {f} -> {imp}")
    ok = ok and not unresolved

    # (c) ZERO-REF: curated tree has no import of any removed module
    if removed_mods:
        alt = "|".join(re.escape(mm) for mm in sorted(removed_mods))
        # Anchored to a REAL import statement at line start (after strip); comment
        # lines skipped — prose mentioning a module is not a dependency.
        ref_re = re.compile(rf"^(?:from|import)\s+({alt})(?:[.\s,]|$)")
        refs = []
        for base in ("src", "scripts"):
            for p in (REPO / base).rglob("*.py"):
                rel = str(p.relative_to(REPO))
                try:
                    for ln in p.read_text(errors="ignore").splitlines():
                        s = ln.strip()
                        if s.startswith("#"):
                            continue
                        mm = ref_re.match(s)
                        if mm:
                            refs.append((rel, mm.group(1)))
                except OSError:
                    continue
        print(f"(c) ZERO-REF: removed modules referenced in curated tree = {len(refs)}")
        for rel, mod in refs[:20]:
            print(f"    REF {rel} -> {mod}")
        ok = ok and not refs

    print(
        f"\nNEG-TEST {'PASS' if ok else 'FAIL'} (compile+resolve+zero-ref over "
        f"{len(seeds)} entrypoints, {len(kept)} kept, {len(removed)} removed)"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
