#!/usr/bin/env python3
"""scripts/governance_router.py — Stop-hook entrypoint.

Wired in .claude/settings.json under hooks.Stop. Receives the assistant's
Stop event payload on stdin; delegates to src.governance.router.main()
which classifies the message and prints a single-line JSON routing
decision to stdout.

The hook MUST never block the assistant — failures exit 0 silently.

GOV-PHASE1-TRACK-B / B1.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.governance.router import main

if __name__ == "__main__":
    raise SystemExit(main())
