#!/usr/bin/env python3
"""governance_freshness_probe.py — KEI Agency_OS-cd36.

Periodically verifies that recently-committed governance content
(docs/governance/*.md, personas/*.md, .claude/modules/*.md, CLAUDE.md) has
been indexed into Cognee within the freshness SLO defined by Layered
Governance Matrix v1 §FRESHNESS SLO:

    - WARN     at age >  1h since git commit AND content not in Cognee top-3
    - CRITICAL at age >  6h since git commit AND content not in Cognee top-3

Alert path: publishes per-breach NATS messages to
  - keiracom.elliot.inbox  — for Elliot to triage
  - keiracom.audit         — for the audit trail

Per-file algorithm:
    1. For each file in the scope set:
         a. age = NOW - git commit timestamp of the file
         b. probe_query = a short distinctive snippet from the file
                         (title-line or first non-empty line, capped 120 chars)
         c. results = cognee.search(probe_query, top_k=3)
         d. classify:
             - SYNCED   = results contain a fragment matching the file content
             - MISSING  = no result mentions the file's marker text
             - STALE    = result mentions marker but text drifted vs file
    2. If status != SYNCED and age > 1h → WARN
    3. If status != SYNCED and age > 6h → CRITICAL

Fail-open: Cognee unreachable → skip alert (cognee health probed separately).

Usage:
    python3 scripts/orchestrator/governance_freshness_probe.py            # one-shot
    python3 scripts/orchestrator/governance_freshness_probe.py --json     # JSON report
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

logger = logging.getLogger("governance_freshness_probe")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# SLO thresholds — Layered Governance Matrix v1 §FRESHNESS SLO.
WARN_THRESHOLD_SECONDS = 3600  # 1 hour
CRITICAL_THRESHOLD_SECONDS = 6 * 3600  # 6 hours

DEFAULT_NATS_URL = "nats://127.0.0.1:4222"
NATS_SUBJECT_INBOX = "keiracom.elliot.inbox"
NATS_SUBJECT_AUDIT = "keiracom.audit"

# Files in scope — matrix lists docs/governance, personas, CLAUDE.md modules.
GOVERNANCE_GLOBS = (
    "docs/governance/*.md",
    "personas/*.md",
    ".claude/modules/*.md",
    "CLAUDE.md",
)


# ---------------------------------------------------------------------------
# File scope + age.
# ---------------------------------------------------------------------------


def collect_governance_files(repo_root: Path) -> list[Path]:
    """Return the absolute paths of every governance file in scope."""
    out: list[Path] = []
    for pattern in GOVERNANCE_GLOBS:
        for p in repo_root.glob(pattern):
            if p.is_file():
                out.append(p)
    return sorted(out)


def git_commit_age_seconds(repo_root: Path, path: Path) -> float | None:
    """Seconds since the file's last git commit. None if untracked / git fails.

    Untracked files have no commit timestamp — they're either being authored
    right now or got committed-then-removed; SLO doesn't apply to them.
    """
    try:
        proc = subprocess.run(  # noqa: S603, S607 — controlled args
            ["git", "log", "-1", "--format=%ct", str(path)],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.debug("git log failed for %s: %s", path, exc)
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    try:
        commit_ts = int(proc.stdout.strip())
    except ValueError:
        return None
    return time.time() - commit_ts


def probe_snippet(path: Path) -> str:
    """Extract a short distinctive snippet for Cognee search.

    Priority: first H1 heading after YAML frontmatter > first non-empty line.
    Skips the entire `---\\n...\\n---\\n` frontmatter block, not just the
    delimiters. Capped at 120 chars.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        logger.debug("read snippet failed for %s: %s", path, exc)
        return path.name

    lines = text.split("\n")
    cursor = 0
    # Skip leading blank lines, then optional YAML frontmatter block.
    while cursor < len(lines) and not lines[cursor].strip():
        cursor += 1
    if cursor < len(lines) and lines[cursor].strip() == "---":
        # Frontmatter open — skip until the next `---` line.
        cursor += 1
        while cursor < len(lines) and lines[cursor].strip() != "---":
            cursor += 1
        cursor += 1  # past the closing ---

    for line in lines[cursor:]:
        stripped = line.strip()
        if not stripped:
            continue
        # Strip leading markdown heading markers.
        if stripped.startswith("#"):
            stripped = stripped.lstrip("#").strip()
        return stripped[:120] if stripped else path.name
    return path.name


# ---------------------------------------------------------------------------
# Cognee probe.
# ---------------------------------------------------------------------------


def cognee_top_k(query: str, top_k: int = 3) -> list[str]:
    """Return top-k textual results from Cognee for a query. Returns [] on failure."""
    try:
        from cognee_http_client import search  # noqa: PLC0415 — fail-open import
    except ImportError as exc:
        logger.debug("cognee_http_client import failed: %s", exc)
        return []
    try:
        resp = search(query, top_k=top_k)
    except Exception as exc:  # noqa: BLE001 — fail-open
        logger.warning("cognee search failed (query_len=%d): %s", len(query), exc)
        return []
    # Response shape varies — try the common keys.
    if isinstance(resp, list):
        return [_extract_text(item) for item in resp if item]
    if isinstance(resp, dict):
        for key in ("results", "hits", "items", "answers"):
            if key in resp and isinstance(resp[key], list):
                return [_extract_text(item) for item in resp[key] if item]
    return []


def _extract_text(item: Any) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        for key in ("text", "content", "answer", "snippet", "value"):
            v = item.get(key)
            if isinstance(v, str):
                return v
    return str(item)


def classify_file(file_text: str, results: list[str]) -> str:
    """Return SYNCED / STALE / MISSING.

    Strategy: pick a marker from file_text (longest distinctive token, or
    first 60 chars). Token threshold lowered to 8 chars to catch real
    governance headings ("layered_governance_matrix" etc.) while staying
    selective enough that common words ("the", "and") don't dominate.
    If the marker appears in any result → SYNCED. Results present but
    marker absent → STALE. No results → MISSING.
    """
    if not results:
        return "MISSING"
    marker = _pick_marker(file_text)
    for r in results:
        if marker.lower() in r.lower():
            return "SYNCED"
    return "STALE"


def _pick_marker(text: str) -> str:
    """A distinctive substring that should appear in Cognee result if indexed.

    Two-stage: prefer the longest meaningful token (>=8 chars); fall back
    to the first 60 non-whitespace chars when no qualifying token exists.
    """
    longest = ""
    for tok in text.replace("\n", " ").split():
        clean = tok.strip(".,():`*_-#")
        if len(clean) >= 8 and len(clean) > len(longest):
            longest = clean
    if longest:
        return longest
    # Fall back to first 60 non-whitespace chars.
    flat = " ".join(text.split())
    return flat[:60]


# ---------------------------------------------------------------------------
# NATS alerts.
# ---------------------------------------------------------------------------


def _publish_nats(subject: str, payload: dict[str, Any]) -> bool:
    """Publish one message via NATS. Fail-open; returns True on success."""
    try:
        import nats.aio.client as nats_client  # noqa: PLC0415 — optional dep
    except ImportError:
        logger.warning("nats.aio.client not installed; alert path inert")
        return False
    url = os.environ.get("NATS_URL", DEFAULT_NATS_URL)

    async def _do() -> None:
        nc = nats_client.Client()
        await nc.connect(url, connect_timeout=2)
        try:
            await nc.publish(subject, json.dumps(payload).encode())
            await nc.flush()
        finally:
            await nc.close()

    try:
        asyncio.run(_do())
        return True
    except Exception as exc:  # noqa: BLE001 — fail-open
        logger.warning("NATS publish to %s failed: %s", subject, exc)
        return False


def emit_breach(severity: str, path: Path, age_seconds: float, status: str) -> None:
    """Publish a breach to both NATS subjects (elliot inbox + audit)."""
    payload = {
        "kind": "governance_freshness_breach",
        "severity": severity,  # WARN | CRITICAL
        "path": str(path),
        "age_seconds": int(age_seconds),
        "cognee_status": status,  # MISSING | STALE
        "ts": int(time.time()),
        "source": "governance_freshness_probe",
    }
    _publish_nats(NATS_SUBJECT_INBOX, payload)
    _publish_nats(NATS_SUBJECT_AUDIT, payload)


# ---------------------------------------------------------------------------
# Main probe loop.
# ---------------------------------------------------------------------------


def probe_file(repo_root: Path, path: Path) -> dict[str, Any]:
    """Evaluate one file. Returns a result dict suitable for JSON report."""
    age = git_commit_age_seconds(repo_root, path)
    if age is None:
        return {
            "path": str(path.relative_to(repo_root)),
            "age_seconds": None,
            "cognee_status": "UNTRACKED",
            "severity": "OK",
        }
    snippet = probe_snippet(path)
    results = cognee_top_k(snippet, top_k=3)
    try:
        file_text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        file_text = snippet
    status = classify_file(file_text, results)

    if status == "SYNCED":
        severity = "OK"
    elif age >= CRITICAL_THRESHOLD_SECONDS:
        severity = "CRITICAL"
    elif age >= WARN_THRESHOLD_SECONDS:
        severity = "WARN"
    else:
        severity = "OK"  # within SLO grace window — not yet a breach

    return {
        "path": str(path.relative_to(repo_root)),
        "age_seconds": int(age),
        "cognee_status": status,
        "severity": severity,
    }


def run_probe(repo_root: Path) -> list[dict[str, Any]]:
    files = collect_governance_files(repo_root)
    logger.info("probe: scanning %d governance files", len(files))
    report: list[dict[str, Any]] = []
    for p in files:
        entry = probe_file(repo_root, p)
        report.append(entry)
        if entry["severity"] in ("WARN", "CRITICAL"):
            emit_breach(entry["severity"], p, float(entry["age_seconds"]), entry["cognee_status"])
            logger.warning(
                "BREACH: %s age=%ds cognee=%s severity=%s",
                entry["path"],
                entry["age_seconds"],
                entry["cognee_status"],
                entry["severity"],
            )
    return report


def _print_report(report: list[dict[str, Any]], emit_json: bool) -> None:
    if emit_json:
        print(json.dumps(report, indent=2))
        return
    counts: dict[str, int] = {}
    for r in report:
        sev = r["severity"]
        counts[sev] = counts.get(sev, 0) + 1
    print("\nGovernance Freshness Probe — Layered Governance Matrix v1 §FRESHNESS SLO")
    print(f"Files scanned: {len(report)}  Severity: {counts}")
    print("-" * 90)
    print(f"{'severity':<10} {'cognee':<10} {'age':>7}  path")
    for r in sorted(report, key=lambda x: (x["severity"] != "CRITICAL", x["severity"] != "WARN")):
        age_str = "  -" if r["age_seconds"] is None else f"{r['age_seconds'] // 60:>5}m"
        print(f"{r['severity']:<10} {r['cognee_status']:<10} {age_str}  {r['path']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help="Repo root (default: derived from script path)",
    )
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root)
    report = run_probe(repo_root)
    _print_report(report, emit_json=args.json)
    # Exit non-zero on any CRITICAL — surfaces to systemd OnFailure (alerting).
    return 2 if any(r["severity"] == "CRITICAL" for r in report) else 0


if __name__ == "__main__":
    sys.exit(main())
