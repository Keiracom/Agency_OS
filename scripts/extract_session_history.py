#!/usr/bin/env python3
"""
D1.8.2 — Session History Extraction
Extracts 8 categories of structured data from 5 JSONL session files (Apr 8-15).
Deterministic: running twice produces identical output.
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

# ── Input / Output paths ──────────────────────────────────────────────────────
SESSION_DIR = Path(
    os.path.expanduser(
        "~/.claude/projects/-home-elliotbot-clawd-Agency-OS"
    )
)

TARGET_FILES = [
    "4298ba10-a9f2-4816-b3cf-c6b781eb9dd1.jsonl",
    "936ac7a2-9bd9-4624-bef4-4a11263acd63.jsonl",
    "4625e05a-5aec-4265-8fe5-41e7214dc167.jsonl",
    "5d6fea3c-a6ab-4ccf-bf99-6e676e070c2d.jsonl",
    "1561a09a-23af-48c1-9f26-f45c134f2750.jsonl",
]

OUT_DIR = Path("/home/elliotbot/clawd/Agency_OS/research/d1_8_2_extraction")

# ── Redaction patterns ─────────────────────────────────────────────────────────
# Pattern order matters: more-specific first
REDACTION_PATTERNS = [
    # OpenAI keys
    (re.compile(r"sk-[A-Za-z0-9_-]{20,}"), "[REDACTED]"),
    # Apify tokens
    (re.compile(r"apify_api_[A-Za-z0-9_-]{20,}"), "[REDACTED]"),
    # Bearer auth tokens
    (re.compile(r"Bearer [A-Za-z0-9._-]{20,}"), "[REDACTED]"),
    # JWTs
    (re.compile(r"eyJ[A-Za-z0-9._-]{20,}"), "[REDACTED]"),
    # Telnyx API keys (KEY0...)
    (re.compile(r"KEY0[A-Za-z0-9_-]{20,}"), "[REDACTED]"),
    # Twilio Account SID (ACxxxxxxxx...)
    (re.compile(r"\bAC[a-f0-9]{32}\b"), "[REDACTED]"),
    # Twilio/generic auth tokens — 32-char hex
    (re.compile(r"\b[a-f0-9]{32}\b"), "[REDACTED]"),
    # UUID-format secrets (8-4-4-4-12) — API keys in UUID form
    (re.compile(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"
    ), "[REDACTED]"),
    # Generic env var assignment: VAR_NAME=<value>=<20+ non-space chars>
    (re.compile(
        r"(?m)^([A-Z][A-Z0-9_]+=)([A-Za-z0-9_\-+/=.@!#$%^&*]{20,})\s*$"
    ), r"\1[REDACTED]"),
]


def redact(text: str) -> str:
    for pattern, replacement in REDACTION_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


# ── Text extraction from message content ─────────────────────────────────────
def extract_text(content: Any) -> str:
    """Extract text from content field (string or list of content blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
                # Skip tool_use blocks
        return "\n".join(parts)
    return ""


# ── Category matchers ─────────────────────────────────────────────────────────

def is_dave_directive(role: str, text: str) -> bool:
    if role != "user":
        return False
    if "DIRECTIVE" in text:
        return True
    if "Context:" in text and "Constraint:" in text:
        return True
    if "Action:" in text and "Output:" in text:
        return True
    return False


def is_step0_restate(role: str, text: str) -> bool:
    if role != "assistant":
        return False
    return "Step 0" in text and ("Objective:" in text or "RESTATE" in text)


def is_pr_creation(role: str, text: str) -> bool:
    if role != "assistant":
        return False
    has_pr_ref = bool(re.search(r"PR\s*#\d+", text))
    has_context = any(kw in text for kw in ["github.com", "pull request", "gh pr create"])
    return has_pr_ref and has_context


def is_verification_output(role: str, text: str) -> bool:
    if role != "assistant":
        return False
    t = text.lower()
    if "pytest" in t:
        return True
    if "passed" in t and ("failed" in t or "skipped" in t):
        return True
    if re.search(r"\bPASS\b", text) and re.search(r"\bFAIL\b", text):
        return True
    return False


CEO_RATIFY_KW = re.compile(
    r"\b(merge|ship|ratified|approved|go ahead|send it|confirmed)\b",
    re.IGNORECASE,
)


def is_ceo_ratification(role: str, text: str) -> bool:
    if role != "user":
        return False
    for m in CEO_RATIFY_KW.finditer(text):
        start = max(0, m.start() - 10)
        end = min(len(text), m.end() + 10)
        context = text[start:end]
        if len(context.strip()) >= 10:
            return True
    return False


GOVERNANCE_KW = re.compile(
    r"\b(rule|law|always|never|going forward|from now on|verify.before.claim|"
    r"optimistic completion|cost.authorization|pre.directive check|"
    r"verify before|must always|hard block|hard rule|governance)\b",
    re.IGNORECASE,
)


def is_governance_language(role: str, text: str) -> bool:
    return bool(GOVERNANCE_KW.search(text))


COST_KW = re.compile(
    r"(\$\d+[\.,]\d{2}|\bAUD\b|\bUSD\b)",
    re.IGNORECASE,
)
COST_CONTEXT_KW = re.compile(
    r"\b(spend|cost|budget|per card|per domain|conversion rate|economics)\b",
    re.IGNORECASE,
)


def is_cost_report(role: str, text: str) -> bool:
    return bool(COST_KW.search(text)) and bool(COST_CONTEXT_KW.search(text))


BUG_KW = re.compile(
    r"\b(bug|broken|regression|fix required)\b|issue\s*#\d+|\bmiss\b",
    re.IGNORECASE,
)
BUG_EXCLUDE = re.compile(r"\bmissing\b", re.IGNORECASE)
CODE_CONTEXT_KW = re.compile(
    r"\b(code|script|function|pipeline|stage|test|error|traceback|exception|"
    r"import|module|assert|raise|TypeError|ValueError|KeyError|AttributeError)\b",
    re.IGNORECASE,
)


def is_bug_discovery(role: str, text: str) -> bool:
    m = BUG_KW.search(text)
    if not m:
        return False
    # Exclude "missing" as a standalone word (generic)
    if m.group(0).lower() == "miss":
        return False
    if not CODE_CONTEXT_KW.search(text):
        return False
    return True


# ── Entry container ────────────────────────────────────────────────────────────

class Entry:
    def __init__(self, timestamp: str, session_file: str, text: str):
        self.timestamp = timestamp or "no timestamp"
        self.session_file = session_file
        self.text = redact(text)


# ── Parse a single JSONL file ─────────────────────────────────────────────────

def parse_file(filepath: Path) -> list[dict]:
    """Return list of dicts with keys: timestamp, role, text (already extracted)."""
    records = []
    basename = filepath.name
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        for lineno, raw in enumerate(f, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = obj.get("type", "")
            # Only process user/assistant messages
            if msg_type not in ("user", "assistant"):
                continue

            msg = obj.get("message")
            if not msg:
                continue

            role = msg.get("role", msg_type)
            content = msg.get("content")
            if content is None:
                continue

            text = extract_text(content)
            if not text.strip():
                continue

            timestamp = obj.get("timestamp", "")

            records.append(
                {
                    "timestamp": timestamp,
                    "session_file": basename,
                    "role": role,
                    "text": text,
                }
            )
    return records


# ── Build category buckets ─────────────────────────────────────────────────────

CATEGORIES = {
    "dave_directives": is_dave_directive,
    "step0_restates": is_step0_restate,
    "pr_creations": is_pr_creation,
    "verification_outputs": is_verification_output,
    "ceo_ratifications": is_ceo_ratification,
    "governance_language": is_governance_language,
    "cost_reports": is_cost_report,
    "bug_discoveries": is_bug_discovery,
}


def classify(record: dict) -> list[str]:
    role = record["role"]
    text = record["text"]
    matched = []
    for cat, fn in CATEGORIES.items():
        if fn(role, text):
            matched.append(cat)
    return matched


# ── Markdown output helpers ────────────────────────────────────────────────────

CATEGORY_TITLES = {
    "dave_directives": "Dave Directives",
    "step0_restates": "Elliottbot Step 0 RESTATE",
    "pr_creations": "PR Creations",
    "verification_outputs": "Verification Outputs",
    "ceo_ratifications": "CEO Ratifications",
    "governance_language": "Governance Language",
    "cost_reports": "Cost Reports",
    "bug_discoveries": "Bug Discoveries",
}

CATEGORY_FILES = {
    "dave_directives": "01_dave_directives.md",
    "step0_restates": "02_elliottbot_restates.md",
    "pr_creations": "03_pr_creations.md",
    "verification_outputs": "04_verification_outputs.md",
    "ceo_ratifications": "05_ceo_ratifications.md",
    "governance_language": "06_governance_language.md",
    "cost_reports": "07_cost_reports.md",
    "bug_discoveries": "08_bug_discoveries.md",
}


def write_category(cat: str, entries: list[Entry]) -> None:
    title = CATEGORY_TITLES[cat]
    outpath = OUT_DIR / CATEGORY_FILES[cat]
    lines = [f"# {title}\n"]
    for i, entry in enumerate(entries, 1):
        lines.append(
            f"## Entry {i} — {entry.timestamp} — {entry.session_file}\n"
        )
        lines.append("```")
        lines.append(entry.text)
        lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")
    outpath.write_text("\n".join(lines), encoding="utf-8")


def write_index(
    buckets: dict[str, list[Entry]],
    files_processed: list[str],
    date_range: str,
) -> None:
    outpath = OUT_DIR / "00_index.md"
    lines = [
        "# D1.8.2 Session History Extraction — Index",
        "",
        f"**Date range:** {date_range}",
        f"**Files processed:** {len(files_processed)}",
        "",
        "## Files",
        "",
    ]
    for f in files_processed:
        lines.append(f"- {f}")
    lines += ["", "## Category Counts", ""]
    total = 0
    for cat, entries in buckets.items():
        count = len(entries)
        total += count
        lines.append(f"- **{CATEGORY_TITLES[cat]}**: {count} entries ({CATEGORY_FILES[cat]})")
    lines += ["", f"**Total entries:** {total}", ""]
    outpath.write_text("\n".join(lines), encoding="utf-8")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    buckets: dict[str, list[Entry]] = {cat: [] for cat in CATEGORIES}

    for fname in TARGET_FILES:
        fpath = SESSION_DIR / fname
        if not fpath.exists():
            print(f"WARNING: {fname} not found, skipping", file=sys.stderr)
            continue
        print(f"Processing {fname} ...", file=sys.stderr)
        records = parse_file(fpath)
        print(f"  {len(records)} messages parsed", file=sys.stderr)
        for rec in records:
            for cat in classify(rec):
                buckets[cat].append(
                    Entry(
                        timestamp=rec["timestamp"],
                        session_file=rec["session_file"],
                        text=rec["text"],
                    )
                )

    # Write category files
    for cat, entries in buckets.items():
        write_category(cat, entries)
        print(f"  {CATEGORY_TITLES[cat]}: {len(entries)} entries", file=sys.stderr)

    date_range = "2026-04-08 to 2026-04-15"
    write_index(buckets, TARGET_FILES, date_range)

    print("Done. Output written to:", OUT_DIR, file=sys.stderr)


if __name__ == "__main__":
    main()
