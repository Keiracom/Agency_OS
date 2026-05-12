#!/usr/bin/env python3
"""heartbeat_generator.py — emit per-callsign HEARTBEAT.md from one template.

Task 1B 20-item roadmap #2: Aiden's PR #751 shipped HEARTBEAT.md as a
shared BASE template. This generator reads the BASE + config/
heartbeat_callsigns.yaml and writes six customised instances
(HEARTBEAT.<callsign>.md) so each agent sees its own budget, file-path
lanes, prohibited actions, and escalation trigger at session start.

Usage:
    python3 scripts/heartbeat_generator.py
    python3 scripts/heartbeat_generator.py --output-dir /tmp/heartbeats
    python3 scripts/heartbeat_generator.py \
        --template HEARTBEAT.md \
        --config config/heartbeat_callsigns.yaml \
        --output-dir build/heartbeats

Exit codes: 0 on success, 1 on config / template error. The generator is
deterministic — same inputs produce byte-identical output.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE = REPO_ROOT / "HEARTBEAT.md"
DEFAULT_CONFIG = REPO_ROOT / "config" / "heartbeat_callsigns.yaml"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "build" / "heartbeats"

REQUIRED_FIELDS = (
    "role",
    "max_token_budget",
    "allowed_paths",
    "prohibited_actions",
    "escalation_trigger",
)

SECTION_HEADER = "## Per-Callsign Context"


def load_config(path: Path) -> dict[str, dict[str, Any]]:
    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict) or "callsigns" not in raw:
        raise ValueError(f"{path}: missing top-level 'callsigns' key")
    callsigns = raw["callsigns"]
    if not isinstance(callsigns, dict) or not callsigns:
        raise ValueError(f"{path}: 'callsigns' must be a non-empty mapping")
    for name, spec in callsigns.items():
        if not isinstance(spec, dict):
            raise ValueError(f"{path}: callsign {name!r} must be a mapping")
        missing = [f for f in REQUIRED_FIELDS if f not in spec]
        if missing:
            raise ValueError(
                f"{path}: callsign {name!r} missing required fields: {missing}"
            )
    return callsigns


def render_section(callsign: str, spec: dict[str, Any]) -> str:
    allowed = "\n".join(f"  - `{p}`" for p in spec["allowed_paths"])
    prohibited = "\n".join(f"  - {a}" for a in spec["prohibited_actions"])
    escalation = " ".join(spec["escalation_trigger"].split())
    return (
        f"\n{SECTION_HEADER}\n\n"
        f"- **Callsign:** `{callsign}`\n"
        f"- **Role:** {spec['role']}\n"
        f"- **Max token budget:** {spec['max_token_budget']:,}\n"
        f"- **Allowed paths:**\n{allowed}\n"
        f"- **Prohibited actions:**\n{prohibited}\n"
        f"- **Escalation trigger:** {escalation}\n"
    )


def generate(
    template: Path,
    config: Path,
    output_dir: Path,
) -> list[Path]:
    base = template.read_text()
    callsigns = load_config(config)
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name in sorted(callsigns):
        body = base.rstrip() + "\n" + render_section(name, callsigns[name])
        out = output_dir / f"HEARTBEAT.{name}.md"
        out.write_text(body)
        written.append(out)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    for label, p in [("template", args.template), ("config", args.config)]:
        if not p.is_file():
            print(f"error: {label} not found at {p}", file=sys.stderr)
            return 1
    try:
        written = generate(args.template, args.config, args.output_dir)
    except (ValueError, yaml.YAMLError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for p in written:
        print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
