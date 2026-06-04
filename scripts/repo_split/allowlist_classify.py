#!/usr/bin/env python3
"""allowlist_classify.py — TERMINAL keiracom-core curation method (Atlas+elliot ruling).

The category/denylist sweep is structurally non-converging (always a next uncovered
category). This INVERTS to allowlist-KEEP / archive-REST:

  KEEP-SET = curated .py (src closure 238 + kept scripts/tests + tooling)
             UNION explicit fleet/product NON-.py allowlist (infra/config/governance/
             fleet-docs/MAL-product assets).
  ARCHIVE  = every tracked file NOT in the keep-set.

Inverse risk: wrongly archiving a fleet/product file. Mitigation: keep-set is built
conservatively and anything UNCERTAIN is emitted to a FLAG bucket (treated as KEEP,
surfaced for human ruling) — never silently archived.

NON-DESTRUCTIVE: this only classifies + writes lists. Apply (git rm the archive list)
is a separate, human-gated step after HoO confirms the method switch.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MANIFEST = REPO / "scripts" / "repo_split" / "closure_manifest.json"

# ── fleet/product dirs kept WHOLESALE (infra, governance, config, product) ──
KEEP_DIR_PREFIXES = (
    ".beads/", ".github/", ".githooks/", ".gates/", ".cache/",
    ".clawdbot/", ".clawdhub/", ".openclaw/",
    "supabase/", "systemd/", "infra/", "governance/", "config/",
    "personas/", "keiracom_system/", "agents/", "app-data/", "hooks/",
    "projects/", "mcp-servers/",  # dead-vendor mcp dirs already archived
)

# ── fleet/product doc subtrees kept (everything else under docs/ -> archive/flag) ──
KEEP_DOC_PREFIXES = (
    "docs/governance/", "docs/runbooks/", "docs/manuals/", "docs/deliberations/",
    "docs/postmortems/", "docs/proof_runs/", "docs/retrieval/", "docs/decomposition/",
    "docs/clones/", "docs/compliance/", "docs/legal/", "docs/legal_corpus/",
    "docs/design/", "docs/schema/", "docs/operations/", "docs/audits/",
    "docs/cutover/", "docs/migration/", "docs/classification/",
)
# fleet/product single docs at docs/ root (non-BDR architecture/ops/governance)
KEEP_DOC_FILES = {
    "docs/MANUAL.md", "docs/AGENCY_OS_SSOT.md", "docs/keiracom_architecture.md",
    "docs/memory_interface.md", "docs/ephemeral_boundary.md",
    "docs/intelligence_layer_design.md", "docs/governance_chunking.md",
    "docs/llm_wiki.md", "docs/project_structure.md", "docs/FOLDER_STRUCTURE.md",
    "docs/ENV_CHECKLIST.md", "docs/agent_sops.md", "docs/agent_audit_anthropic.md",
    "docs/ROADMAP_V2.md", "docs/RUNBOOK_POSTGRES_RESTORE.md",
    "docs/PREFECT_SPOT_MIGRATION.md", "docs/PREFECT_RAILWAY_SETUP.md",
    "docs/enforcer_redesign_spec.md", "docs/memory_interface.md",
    "docs/DELEGATED_ACCESS_REQUIREMENTS.md", "docs/direct-api-reference.md",
    "docs/retrieval/", "docs/daily_log.md",
}

# ── BDR signals: anything matching (path) is dead-BDR -> ARCHIVE even if under a kept dir
BDR_SIG = re.compile(
    r"campaign|/lead|lead_|gmb|/abn|abn_|business_universe|prospect|enrich|waterfall|"
    r"dataforseo|prospeo|salesforge|telnyx|unipile|vapi|brightdata|smartlead|pipedrive|"
    r"hubspot|zoominfo|contactout|leadmagic|siege|outreach|/cis|cis_|icp|sourcing|serp|"
    r"dashboard|landing|marketing|/voice/|pilot|founding_2|distribution|scoring|"
    r"smartlead_migration|sales_infrastructure|nationwide",
    re.I,
)
# explicit fleet-skill allowlist (LAW XII canonical fleet/product skills)
KEEP_SKILLS = {
    "skills/agents", "skills/callback-poller", "skills/cognee-recall",
    "skills/composio-oauth", "skills/decomposer", "skills/drive-manual",
    "skills/frontend", "skills/mcp-bridge", "skills/pr-tool", "skills/superpowers",
    "skills/testing", "skills/three-store-save", "skills/weaviate-vectorizer",
    "skills/slack-file-upload", "skills/DEPRECATED.md", "skills/SKILL_INDEX.md",
}
# fleet .claude skills (dead-BDR .claude skills excluded -> archive)
DEAD_CLAUDE = re.compile(r"\.claude/skills/(dataforseo|enrichment)/", re.I)


def src_imports(rel: str) -> set[str]:
    out: set[str] = set()
    for ln in (REPO / rel).read_text(errors="ignore").splitlines():
        s = ln.strip()
        if s.startswith("#"):
            continue
        for mm in re.finditer(r"(?:from|import)\s+(src\.[A-Za-z0-9_.]+)", s):
            out.add(mm.group(1))
    return out


def src_exists(mod: str) -> bool:
    p = mod.replace(".", "/")
    return (REPO / f"{p}.py").is_file() or (REPO / f"{p}/__init__.py").is_file()


def classify() -> dict:
    m = json.loads(MANIFEST.read_text())
    seeds = set(m["seeds"])
    files = [f for f in subprocess.run(
        ["git", "ls-files", "-z"], capture_output=True, cwd=REPO
    ).stdout.decode().split("\0") if f]

    keep, archive, flag = [], [], []
    for f in files:
        reason = _classify_one(f, seeds)
        if reason[0] == "KEEP":
            keep.append(f)
        elif reason[0] == "ARCHIVE":
            archive.append((f, reason[1]))
        else:
            flag.append((f, reason[1]))
    return {"keep": keep, "archive": archive, "flag": flag}


def _classify_one(f: str, seeds: set[str]) -> tuple[str, str]:
    # 1) tooling + the curation artefacts always KEEP
    if f.startswith("scripts/repo_split/") or "keiracom_core_curation" in f:
        return ("KEEP", "curation-tooling")
    # 2) .py — curated set: src kept (closure already purged), scripts seeds/fleet-ops,
    #    tests of kept code. BDR-signal .py NOT a seed -> archive.
    if f.endswith(".py"):
        if f.startswith("src/"):
            return ("KEEP", "src-closure") if not BDR_SIG.search(f) else ("FLAG", "src-py-bdr-signal")
        if f in seeds:
            return ("KEEP", "live-entrypoint-seed")
        if f.startswith("tests/"):
            imps = src_imports(f)
            if imps and any(not src_exists(i) and not src_exists(".".join(i.split(".")[:-1])) for i in imps):
                return ("ARCHIVE", "test-imports-removed-module")
            if BDR_SIG.search(f):
                return ("ARCHIVE", "test-bdr-signal")
            return ("KEEP", "test-of-kept-code")
        if f.startswith("scripts/"):
            if BDR_SIG.search(f):
                return ("ARCHIVE", "script-bdr-signal")
            # non-BDR non-seed script: fleet-ops tool -> keep, but flag for eyeball
            return ("KEEP", "fleet-ops-script")
        return ("KEEP", "py-other")
    # 3) dead-BDR .claude skills
    if DEAD_CLAUDE.search(f):
        return ("ARCHIVE", "dead-bdr-claude-skill")
    # 4) BDR-signal anywhere -> archive (the leak the denylist missed)
    if BDR_SIG.search(f):
        return ("ARCHIVE", "bdr-signal-path")
    # 5) wholesale-keep fleet dirs
    if f.startswith(KEEP_DIR_PREFIXES) or f.startswith(".claude/"):
        return ("KEEP", "fleet-dir")
    # 6) skills allowlist
    if f.startswith("skills/"):
        top = "/".join(f.split("/")[:2])
        return ("KEEP", "fleet-skill") if (top in KEEP_SKILLS or f in KEEP_SKILLS) else ("ARCHIVE", "non-allowlist-skill")
    # 7) docs allowlist
    if f.startswith("docs/"):
        if f.startswith(tuple(KEEP_DOC_PREFIXES)) or f in KEEP_DOC_FILES:
            return ("KEEP", "fleet-doc")
        return ("FLAG", "doc-uncertain")  # keep+flag (inverse-risk) — human ruling
    # 8) root infra/config + fleet docs
    if "/" not in f:
        return ("KEEP", "root-fleet-or-config")
    # 9) memory/ + everything else uncertain -> FLAG (keep, surface)
    return ("FLAG", "uncertain-keep")


if __name__ == "__main__":
    r = classify()
    out = REPO / "scripts" / "repo_split"
    (out / "allowlist_archive.txt").write_text("\0".join(f for f, _ in r["archive"]))
    (out / "allowlist_flag.txt").write_text("\n".join(f"{f}\t{why}" for f, why in r["flag"]))
    print(f"KEEP: {len(r['keep'])}  ARCHIVE: {len(r['archive'])}  FLAG(keep+review): {len(r['flag'])}")
    from collections import Counter
    print("\n-- ARCHIVE reasons --")
    for k, v in Counter(w for _, w in r["archive"]).most_common():
        print(f"  {v:4} {k}")
    print("\n-- FLAG reasons (kept, need ruling) --")
    for k, v in Counter(w for _, w in r["flag"]).most_common():
        print(f"  {v:4} {k}")
