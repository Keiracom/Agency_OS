#!/usr/bin/env python3
"""hydrate_spawn_template.py — stamp spawn parameters into the governance template.

Reads `docs/cutover/spawn_governance_template.md` and replaces its hydration
placeholders with the values for ONE spawn, emitting a ready-to-use system
prompt on stdout. Stdlib only — no third-party dependencies.

Hydration placeholders (UPPERCASE — stamped once at spawn time):
    <CALLSIGN>      agent identity (orion, atlas, scout, aiden, max, elliot)
    <ORCHESTRATOR>  who dispatched this spawn (e.g. elliot)
    <MODEL>         the LLM model for this spawn (Viktor's requirement: model
                    selection is hydrated in the same pass as identity/role)
    <ROLE_LENS>     deliberators only (impl-feasibility / governance / code-quality)
    <SPECIALTY>     workers only (build/retrieval, memory/research, ...)

`<ROLE_LENS>` and `<SPECIALTY>` are mutually exclusive (deliberator XOR worker).
A line carrying a placeholder whose value is empty is **omitted entirely** —
so a worker's prompt has no dangling "Deliberation lens:" line and vice-versa.

NOT hydrated (deliberately): lowercase / runtime placeholders inside the
governance text such as `[CLAIM:<callsign>]`, `<path>`, `<min>` — those are
filled by the agent itself when it posts a claim. Matching is case-sensitive
so they survive hydration untouched.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE = REPO_ROOT / "docs" / "cutover" / "spawn_governance_template.md"

SCALAR_PLACEHOLDERS = ("<CALLSIGN>", "<ORCHESTRATOR>", "<MODEL>")
CONDITIONAL_PLACEHOLDERS = ("<ROLE_LENS>", "<SPECIALTY>")


def hydrate(
    template: str,
    *,
    callsign: str,
    orchestrator: str,
    model: str,
    role_lens: str = "",
    specialty: str = "",
) -> str:
    """Return `template` with every hydration placeholder stamped.

    Conditional lines (those bearing <ROLE_LENS> / <SPECIALTY>) are dropped when
    their value is empty, so the unused role/specialty line never reaches the
    prompt.
    """
    out_lines: list[str] = []
    skip_continuation = False
    for line in template.splitlines():
        # An omitted conditional bullet may wrap onto indented continuation
        # lines; drop those too (until the next bullet / blank / unindented line)
        # so no orphan fragment leaks into the prompt.
        is_continuation = bool(line[:1].isspace() and line.strip())
        if skip_continuation and is_continuation:
            continue
        skip_continuation = False
        if "<ROLE_LENS>" in line and not role_lens:
            skip_continuation = True
            continue
        if "<SPECIALTY>" in line and not specialty:
            skip_continuation = True
            continue
        line = line.replace("<CALLSIGN>", callsign)
        line = line.replace("<ORCHESTRATOR>", orchestrator)
        line = line.replace("<MODEL>", model)
        line = line.replace("<ROLE_LENS>", role_lens)
        line = line.replace("<SPECIALTY>", specialty)
        out_lines.append(line)
    rendered = "\n".join(out_lines)
    if template.endswith("\n"):
        rendered += "\n"
    return rendered


def _assert_fully_hydrated(rendered: str) -> None:
    """Fail loudly if any hydration placeholder survived (catches template drift
    — e.g. a new <FOO> added to the doc but not wired here)."""
    leftover = [p for p in SCALAR_PLACEHOLDERS + CONDITIONAL_PLACEHOLDERS if p in rendered]
    if leftover:
        raise SystemExit(f"hydration incomplete — placeholders remain: {', '.join(leftover)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hydrate the spawn governance template.")
    parser.add_argument("--callsign", required=True)
    parser.add_argument("--orchestrator", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument(
        "--role-lens", default="", help="deliberators only; mutually exclusive with --specialty"
    )
    parser.add_argument(
        "--specialty", default="", help="workers only; mutually exclusive with --role-lens"
    )
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    args = parser.parse_args(argv)

    if args.role_lens and args.specialty:
        raise SystemExit(
            "--role-lens and --specialty are mutually exclusive (a spawn is a deliberator XOR a worker)"
        )
    template_path = Path(args.template)
    if not template_path.is_file():
        raise SystemExit(f"template not found: {template_path}")

    rendered = hydrate(
        template_path.read_text(encoding="utf-8"),
        callsign=args.callsign,
        orchestrator=args.orchestrator,
        model=args.model,
        role_lens=args.role_lens,
        specialty=args.specialty,
    )
    _assert_fully_hydrated(rendered)
    sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
