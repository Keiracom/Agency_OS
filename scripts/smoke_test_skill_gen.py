#!/usr/bin/env python3
"""smoke_test_skill_gen.py — empirical acceptance test for src.skill_gen.

Workflow (post-merge of PR #720):
    1. Parse Max's manual reference (14 patterns: 8 HOW + 6 AVOID).
    2. Invoke skill_gen.generator.generate(...) on a captured session_id.
    3. Substring-match each reference pattern against the generated SKILL.md.
    4. Report: matched / total, hard-req matched / missing.
    5. Exit 0 if >= 10/14 total AND all 5 hard-req patterns captured; else 1.

The parser + match_patterns + evaluate functions are PURE — covered by unit
tests in tests/scripts/test_smoke_test_skill_gen.py. The `--run` CLI path is
e2e and intentionally deferred: do NOT invoke against real data until ~2-3
directive cycles have accumulated in turn_logs (per Elliot dispatch 2026-05-11).

Reference: /tmp/max_session_skill_notes_c322aa37.md (session c322aa37).
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

# Repo-root on sys.path so src.skill_gen imports resolve regardless of cwd.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Hard-requirement keyword tags. Each entry must appear (substring match,
# case-insensitive) in at least one matched pattern for the overall test to
# pass. Sourced from Elliot dispatch 2026-05-11: the 5 patterns Max flagged
# as non-negotiable for an empirical skill-gen pass.
_HARD_REQ_KEYWORDS: list[tuple[str, str]] = [
    ("verify_pr", "verify_pr.sh usage pattern"),
    ("git cat-file", "git cat-file commit verification"),
    ("sonarcloud", "SonarCloud bot comment retrieval"),
    ("tg -g", "tg -g env sourcing pattern"),
    ("fabricat", "fabrication avoidance (covers fabricate/fabrication/fabricated)"),
]

_HOW_HEADING = "## HOW"
_AVOID_HEADING = "## AVOID"


@dataclass(frozen=True)
class Pattern:
    kind: str  # "HOW" | "AVOID"
    text: str
    is_hard_req: bool
    hard_req_label: str | None  # populated when is_hard_req


@dataclass(frozen=True)
class MatchReport:
    matched: list[Pattern]
    missed: list[Pattern]
    hard_req_matched: list[str]
    hard_req_missing: list[str]

    @property
    def total(self) -> int:
        return len(self.matched) + len(self.missed)

    @property
    def matched_count(self) -> int:
        return len(self.matched)


def _is_hard_req(text: str) -> tuple[bool, str | None]:
    low = text.lower()
    for kw, label in _HARD_REQ_KEYWORDS:
        if kw.lower() in low:
            return True, label
    return False, None


def parse_reference(path: Path) -> list[Pattern]:
    """Read Max's reference markdown, return all HOW + AVOID dash-bullet patterns."""
    lines = path.read_text().splitlines()
    patterns: list[Pattern] = []
    current_kind: str | None = None
    for raw in lines:
        line = raw.rstrip()
        if line.startswith(_HOW_HEADING):
            current_kind = "HOW"
            continue
        if line.startswith(_AVOID_HEADING):
            current_kind = "AVOID"
            continue
        if line.startswith("## "):
            current_kind = None  # any other H2 ends pattern collection
            continue
        if current_kind and line.startswith("- "):
            text = line[2:].strip()
            if not text:
                continue
            hard, label = _is_hard_req(text)
            patterns.append(
                Pattern(kind=current_kind, text=text, is_hard_req=hard, hard_req_label=label)
            )
    return patterns


def match_patterns(generated_md: str, reference: list[Pattern]) -> MatchReport:
    """Substring-match each reference pattern (case-insensitive) against generated_md.

    A pattern matches if at least one ~3-word keyphrase from its text appears
    verbatim in the generated SKILL.md, OR for hard-req patterns if the
    hard-req keyword itself appears. Simple, deterministic — no LLM.
    """
    body = generated_md.lower()
    matched: list[Pattern] = []
    missed: list[Pattern] = []
    seen_hard: set[str] = set()
    for p in reference:
        keys = _candidate_keys(p)
        hit = any(k in body for k in keys)
        if hit:
            matched.append(p)
            if p.is_hard_req and p.hard_req_label:
                seen_hard.add(p.hard_req_label)
        else:
            missed.append(p)
    all_hard = {label for _, label in _HARD_REQ_KEYWORDS}
    return MatchReport(
        matched=matched,
        missed=missed,
        hard_req_matched=sorted(seen_hard),
        hard_req_missing=sorted(all_hard - seen_hard),
    )


def _candidate_keys(p: Pattern) -> list[str]:
    """Generate lowercase substring keys for a pattern. Always includes any
    hard-req keyword tag plus the first few words of the pattern."""
    keys: list[str] = []
    if p.is_hard_req:
        for kw, _ in _HARD_REQ_KEYWORDS:
            if kw.lower() in p.text.lower():
                keys.append(kw.lower())
    words = p.text.lower().split()
    if len(words) >= 3:
        keys.append(" ".join(words[:3]))
    return keys


def evaluate(report: MatchReport) -> tuple[bool, str]:
    """Apply Dave's acceptance rule: >=10/14 total AND all 5 hard-reqs hit."""
    passed = report.matched_count >= 10 and not report.hard_req_missing
    lines = [
        f"matched={report.matched_count}/{report.total}",
        f"hard_req_matched={len(report.hard_req_matched)}/5",
    ]
    if report.hard_req_missing:
        lines.append("hard_req_missing: " + ", ".join(report.hard_req_missing))
    if report.missed:
        lines.append("missed_patterns:")
        for m in report.missed:
            lines.append(f"  - [{m.kind}] {m.text[:120]}")
    return passed, "\n".join(lines)


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument(
        "--reference",
        default="/tmp/max_session_skill_notes_c322aa37.md",
        help="Path to Max's manual reference file",
    )
    p.add_argument("--session-id", help="Captured session_id (UUID) to run skill_gen against")
    p.add_argument("--start-ts", help="Window start (ISO8601)")
    p.add_argument("--end-ts", help="Window end (ISO8601)")
    p.add_argument("--directive-ref", default="smoke-test", help="Directive label for PR title")
    p.add_argument(
        "--run",
        action="store_true",
        help="Actually invoke skill_gen.generate (e2e). Default: parse-only dry-run.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv if argv is not None else sys.argv[1:])
    ref_path = Path(args.reference)
    if not ref_path.exists():
        print(f"reference file not found: {ref_path}", file=sys.stderr)
        return 2
    reference = parse_reference(ref_path)
    print(f"parsed {len(reference)} patterns from {ref_path}")
    print(f"  - HOW: {sum(1 for p in reference if p.kind == 'HOW')}")
    print(f"  - AVOID: {sum(1 for p in reference if p.kind == 'AVOID')}")
    categories_covered = {p.hard_req_label for p in reference if p.is_hard_req}
    categories_covered.discard(None)
    print(f"  - patterns flagged is_hard_req: {sum(1 for p in reference if p.is_hard_req)}")
    print(f"  - hard-req categories covered: {len(categories_covered)}/5")
    if not args.run:
        print("parse-only mode; pass --run plus --session-id/--start-ts/--end-ts to evaluate")
        return 0
    if not (args.session_id and args.start_ts and args.end_ts):
        print("--run requires --session-id, --start-ts, --end-ts", file=sys.stderr)
        return 2
    from src.skill_gen.generator import generate  # imported lazily for parse-only dry-run

    result = generate(
        repo_root=_REPO_ROOT,
        session_id=args.session_id,
        start_ts=args.start_ts,
        end_ts=args.end_ts,
        directive_ref=args.directive_ref,
    )
    body = result.skill_path.read_text()
    report = match_patterns(body, reference)
    passed, summary = evaluate(report)
    print(summary, file=sys.stderr)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
