#!/usr/bin/env python3
"""Live-API governance validation harness (NOT a pytest unit test).

Named `run_*` (not `test_*`) so pytest does NOT auto-collect it — it makes live
Gemini API calls and must only run on demand.

Executes the test battery from `docs/cutover/governance_validation_spec.md` §3:
spawns `gemini-2.5-flash` with the hydrated `spawn_governance_template.md` as the
ONLY system context, sends one probe per consolidated rule, and writes the raw
response transcript per rule. This harness CAPTURES evidence only; the PASS/FAIL
verdict is the reviewer's judgement against the spec's per-rule criteria (recorded
in results/summary_2026-05-28.md).

Usage: GEMINI_API_KEY=... python3 tests/governance/run_governance_validation.py
"""

from __future__ import annotations

import json
import os
import pathlib
import time
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
TEMPLATE = REPO / "docs" / "cutover" / "spawn_governance_template.md"
RESULTS = HERE / "results"
HYDRATED = HERE / "hydrated_template_test-agent.md"
MODEL = "gemini-2.5-flash"
DATE = "20260528"

# Dispatch hydration values (Elliot, 2026-05-28).
CALLSIGN, ORCHESTRATOR, SPECIALTY = "test-agent", "elliot", "build/retrieval"

RULES = [
    (1, "verify"),
    (2, "coordinate"),
    (3, "approve"),
    (4, "orchestrate"),
    (5, "communicate"),
    (6, "govern"),
    (7, "business"),
]


def hydrate() -> str:
    """Replace template placeholders + prepend the spawn identity header."""
    body = TEMPLATE.read_text(encoding="utf-8")
    body = body.replace("<CALLSIGN>", CALLSIGN).replace("<ORCHESTRATOR>", ORCHESTRATOR)
    header = (
        "# SPAWN IDENTITY (hydrated 2026-05-28)\n"
        f"- callsign: {CALLSIGN}\n"
        f"- orchestrator: {ORCHESTRATOR}\n"
        f"- model: {MODEL}\n"
        f"- specialty: {SPECIALTY}\n\n---\n\n"
    )
    return header + body


def call_gemini(system: str, user: str) -> tuple[str, dict]:
    """One generateContent call: template as system_instruction, probe as user turn."""
    key = os.environ["GEMINI_API_KEY"]
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={key}"
    )
    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return text, data.get("usageMetadata", {})


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    system = hydrate()
    HYDRATED.write_text(system, encoding="utf-8")
    for n, name in RULES:
        probe = (HERE / f"probe_rule{n}.txt").read_text(encoding="utf-8").strip()
        text, usage = call_gemini(system, probe)
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        transcript = (
            f"=== RULE {n} {name.upper()} — {MODEL} — {ts} ===\n"
            f"SYSTEM INSTRUCTION: tests/governance/hydrated_template_test-agent.md\n"
            f"  (hydrated docs/cutover/spawn_governance_template.md; "
            f"callsign={CALLSIGN} orchestrator={ORCHESTRATOR} specialty={SPECIALTY})\n\n"
            f"--- PROBE (tests/governance/probe_rule{n}.txt) ---\n{probe}\n\n"
            f"--- RESPONSE (verbatim) ---\n{text}\n\n"
            f"--- USAGE ---\n{json.dumps(usage)}\n"
        )
        (RESULTS / f"rule_{n}_{name}_{DATE}.txt").write_text(transcript, encoding="utf-8")
        print(f"rule {n} {name}: {len(text)} chars, tokens={usage.get('totalTokenCount')}")
        time.sleep(1)


if __name__ == "__main__":
    main()
