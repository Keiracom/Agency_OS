"""scripts/compile_llm_wiki.py — Compiled LLM Wiki generator.

Phase 1 Roadmap Item #4. Implements the Karpathy LLM Wiki pattern: a single
≤2,000-token compressed architecture document agents read at cold-start to
get oriented without re-reading the full codebase / Manual / ceo_memory.

Sources (in priority order):
  1. ARCHITECTURE.md (locked spec — Sections 2, 3, 4, 5, 7, 9)
  2. README.md (top-level)
  3. docs/governance/CONSOLIDATED_RULES.md (7 rules)
  4. public.ceo_memory (live state keys: directives.last_number, roadmap, blockers)
  5. systemd --user (active service inventory)

Output: docs/llm_wiki.md (overwritten each run).

Run modes:
  python scripts/compile_llm_wiki.py            — compile + write
  python scripts/compile_llm_wiki.py --check    — compile + validate token cap, don't write
  python scripts/compile_llm_wiki.py --stdout   — emit to stdout instead of file

Wired to weekly systemd timer (infra/cron/agency-os-llm-wiki-refresh.timer).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOKEN_CAP = 2000
OUTPUT_PATH = REPO_ROOT / "docs" / "llm_wiki.md"

EXPECTED_SECTIONS = [
    "## 1. Stack",
    "## 2. Pipeline",
    "## 3. Live Vendors",
    "## 4. Dead References",
    "## 5. Outreach Channels",
    "## 6. Memory Architecture",
    "## 7. Governance",
    "## 8. Active Services",
    "## 9. CEO State",
    "## 10. Callsign Hierarchy",
    "## 11. Currency & Geography",
]


def count_tokens(text: str) -> int:
    """Return tiktoken cl100k_base token count, else char/4 fallback."""
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return len(text) // 4


def read_safe(path: Path, lines: int | None = None) -> str:
    """Read a file or return '' on miss. Optionally limit to first N lines."""
    try:
        with path.open(encoding="utf-8") as fh:
            if lines is None:
                return fh.read()
            return "".join([next(fh, "") for _ in range(lines)])
    except OSError:
        return ""


def fetch_ceo_memory_keys(keys: list[str]) -> dict[str, str]:
    """Pull selected ceo_memory keys via PostgREST. Best-effort, returns {} on fail."""
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "") or os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        return {}
    try:
        import httpx

        encoded = ",".join(f'"{k}"' for k in keys)
        resp = httpx.get(
            f"{url}/rest/v1/ceo_memory",
            params={"select": "key,value", "key": f"in.({encoded})"},
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
            timeout=5,
        )
        if resp.status_code != 200:
            return {}
        out: dict[str, str] = {}
        for row in resp.json():
            v = row.get("value")
            if isinstance(v, str):
                out[row["key"]] = v
            else:
                out[row["key"]] = json.dumps(v, separators=(",", ":"))
        return out
    except Exception:
        return {}


def list_active_systemd_units() -> list[str]:
    """Enumerate active systemd --user units relevant to Agency OS."""
    if not shutil.which("systemctl"):
        return []
    try:
        proc = subprocess.run(
            [
                "systemctl",
                "--user",
                "list-units",
                "--state=active",
                "--no-legend",
                "--type=service",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode != 0:
            return []
        names: list[str] = []
        for line in proc.stdout.splitlines():
            parts = line.split()
            if not parts:
                continue
            name = parts[0]
            if any(
                tok in name
                for tok in ("agency-os", "aiden", "max", "atlas", "orion", "elliot", "coo")
            ):
                names.append(name.replace(".service", ""))
        return sorted(set(names))
    except Exception:
        return []


def extract_arch_section(arch: str, section_header: str, max_chars: int) -> str:
    """Pull one section from ARCHITECTURE.md and truncate."""
    idx = arch.find(section_header)
    if idx < 0:
        return ""
    # Find next "## SECTION" header
    nxt = arch.find("## SECTION", idx + len(section_header))
    if nxt < 0:
        nxt = len(arch)
    body = arch[idx:nxt].strip()
    return body[:max_chars]


def extract_dead_vendors(arch: str) -> list[str]:
    """Extract vendor names from Section 3 dead-references table."""
    sec = extract_arch_section(arch, "## SECTION 3 — DEPRECATED VENDORS", 4000)
    names: list[str] = []
    for line in sec.splitlines():
        m = re.match(r"\|\s*([A-Za-z][A-Za-z0-9 .]+?)\s*\|", line)
        if m and m.group(1) not in ("Vendor", ""):
            names.append(m.group(1).strip())
    return names


def extract_live_vendors(arch: str) -> list[tuple[str, str]]:
    """Extract (vendor, purpose) from Section 4 live-vendors table."""
    sec = extract_arch_section(arch, "## SECTION 4 — LIVE VENDORS", 4000)
    rows: list[tuple[str, str]] = []
    for line in sec.splitlines():
        cells = [c.strip() for c in line.split("|")]
        if len(cells) >= 3 and cells[1] and cells[1] != "Vendor" and not cells[1].startswith("-"):
            vendor, purpose = cells[1], cells[2]
            if vendor and purpose:
                rows.append((vendor, purpose))
    return rows


def compile_wiki() -> str:
    """Build the compiled wiki markdown. Pure function — no side effects."""
    arch = read_safe(REPO_ROOT / "ARCHITECTURE.md")

    ceo = fetch_ceo_memory_keys(
        [
            "ceo:directives.last_number",
            "ceo:roadmap_20_capabilities_phases_2026-05-11",
            "ceo:workstream_memory_audit_optimization_2026-05-11",
            "ceo:max_operational_state",
        ]
    )
    units = list_active_systemd_units()
    dead = extract_dead_vendors(arch)
    live = extract_live_vendors(arch)

    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines: list[str] = []
    lines.append("# Agency OS — Compiled LLM Wiki")
    lines.append(
        "> Auto-generated by `scripts/compile_llm_wiki.py` · regenerated weekly · DO NOT EDIT"
    )
    lines.append(f"> Built: {now} · Token cap: {TOKEN_CAP}")
    lines.append("")

    lines.append("## 1. Stack")
    lines.append(
        "Python (FastAPI) backend on Railway · Next.js frontend on Vercel · "
        "Supabase Postgres (project `jatzvazlbusedwsnqxzr`) · Prefect orchestration · "
        "Redis queue · Pydantic AI agent framework. Repo `/home/elliotbot/clawd/Agency_OS`. "
        "Env `/home/elliotbot/.config/agency-os/.env`."
    )
    lines.append("")

    lines.append("## 2. Pipeline (Siege Waterfall, F v2.1)")
    lines.append(
        "Flow A (sync, <6min): Verify ICP → DataForSEO T0 multi-category discovery "
        "→ bulk insert lead_pool → ABN match (local JOIN) → activate campaign → fire Flow B."
    )
    lines.append(
        "Flow B (async, <10min): parallel `asyncio.gather` of T1 (BU ABN JOIN, local), "
        "T1.25 (ABR trading name), T1.5 (Bright Data LinkedIn Co), T2 (BD GMB backfill), "
        "T3 (Leadmagic email + Hunter L2 fallback ≥70), T-DM0 (DFS ad spend) → "
        "Stage 2 (person discovery) → Stage 2.5 (social, gated propensity ≥70) + "
        "T5 (Leadmagic mobile, gated propensity ≥85) → ALS scoring → Outreach."
    )
    lines.append("Source: `src/pipeline/{discovery,email_waterfall,mobile_waterfall}.py`.")
    lines.append("")

    lines.append("## 3. Live Vendors")
    lines.append("| Vendor | Purpose |")
    lines.append("|---|---|")
    for vendor, purpose in live[:12]:
        lines.append(f"| {vendor} | {purpose[:90]} |")
    lines.append("")

    lines.append("## 4. Dead References")
    lines.append("Never call: " + ", ".join(dead) + ".")
    lines.append(
        "Hunter is dead EXCEPT as Pipeline F v2.1 L2 email fallback (score ≥70). See ARCH §5 T3."
    )
    lines.append("")

    lines.append("## 5. Outreach Channels")
    lines.append(
        "Email = Salesforge (`SALESFORGE_API_KEY`). LinkedIn = Unipile. "
        "Voice = ElevenAgents (Alex agent). SMS = Telnyx (on hold until launch). "
        "Mail = DEAD (removed permanently)."
    )
    lines.append("")

    lines.append("## 6. Memory Architecture")
    lines.append(
        "SSOT: `public.agent_memories` (per-callsign, embeddings via OpenAI "
        "`text-embedding-3-small`, `supersedes_id` graph, ~6.3k rows). "
        "`public.ceo_memory` (kv state). `public.governance_events` (audit trail). "
        "DEPRECATED: `elliot_internal.memories` (kept warm for legacy reads). "
        "Mem0 cloud: RETIRED (see `docs/audits/memory_audit_2026-05-12_atlas_section.md`)."
    )
    lines.append("")

    lines.append("## 7. Governance — 7 Rules (Ratified 2026-05-01)")
    lines.append(
        "1 VERIFY · 2 COORDINATE · 3 APPROVE · 4 ORCHESTRATE · "
        "5 COMMUNICATE · 6 GOVERN · 7 BUSINESS"
    )
    lines.append(
        "Full text: `docs/governance/CONSOLIDATED_RULES.md`. "
        "Shared laws: `~/.claude/CLAUDE.md §Shared Governance`. "
        "Key invariants: Step 0 RESTATE mandatory (LAW XV-D); dual-CTO concur for merge; "
        "Skills > MCP > exec hierarchy (LAW VI); $AUD only (LAW II)."
    )
    lines.append("")

    lines.append("## 8. Active Services (systemd --user)")
    if units:
        for u in units[:14]:
            lines.append(f"- `{u}`")
    else:
        lines.append("(systemd inventory unavailable at compile time)")
    lines.append("")

    lines.append("## 9. CEO State (live)")
    last_dir = ceo.get("ceo:directives.last_number", "(unknown)")[:60]
    lines.append(f"- Last directive: {last_dir}")
    if "ceo:roadmap_20_capabilities_phases_2026-05-11" in ceo:
        lines.append(
            "- Roadmap key: `ceo:roadmap_20_capabilities_phases_2026-05-11` "
            "(read live for current phase)"
        )
    if "ceo:max_operational_state" in ceo:
        lines.append("- Max op state key: `ceo:max_operational_state` (read live)")
    lines.append(
        "Read fresh — never quote stale values; check `ceo:session_end_*` for last activity."
    )
    lines.append("")

    lines.append("## 10. Callsign Hierarchy")
    lines.append(
        "`Dave → Claude (CEO) → Elliot (COO) → {Aiden, Max} (CTOs) → "
        "{Orion, Atlas} (engineers)`. Clones: ATLAS = Elliot's, ORION = Aiden's. "
        "Worktrees: `/home/elliotbot/clawd/Agency_OS{,-aiden,-atlas,-orion}`. "
        "Work flows DOWN; escalation flows UP. No cross-dispatch between clones."
    )
    lines.append("")

    lines.append("## 11. Currency & Geography")
    lines.append(
        "**$AUD only.** Conversion: 1 USD = 1.55 AUD (LAW II). "
        "Target market: Australian SMBs (GMB-discovered). Pre-revenue (zero paying clients) — "
        "reject all social-proof claims unless Dave confirms (LAW pre_revenue)."
    )
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile the LLM Wiki")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Compile + verify token cap; do not write",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Emit to stdout instead of writing to disk",
    )
    args = parser.parse_args(argv)

    text = compile_wiki()
    tokens = count_tokens(text)
    sections_found = sum(1 for h in EXPECTED_SECTIONS if h in text)

    summary = (
        f"[llm-wiki] tokens={tokens}/{TOKEN_CAP} "
        f"sections={sections_found}/{len(EXPECTED_SECTIONS)} "
        f"bytes={len(text)}"
    )

    if tokens > TOKEN_CAP:
        print(f"FAIL: {summary} — exceeds cap", file=sys.stderr)
        return 1
    if sections_found < len(EXPECTED_SECTIONS):
        missing = [h for h in EXPECTED_SECTIONS if h not in text]
        print(f"FAIL: {summary} — missing sections: {missing}", file=sys.stderr)
        return 1

    if args.stdout:
        sys.stdout.write(text)
        print(summary, file=sys.stderr)
        return 0
    if args.check:
        print(summary)
        return 0

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(text, encoding="utf-8")
    print(summary)
    print(f"[llm-wiki] wrote {OUTPUT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
