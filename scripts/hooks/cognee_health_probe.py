#!/usr/bin/env python3
"""cognee_health_probe.py — wake-time check that Cognee recall is functional.

Outputs a markdown block to stdout. If degraded, the block calls it out
loudly so the fresh session knows the recall layer is down and works on
the hot tier only.
"""
from __future__ import annotations
import sys

sys.path.insert(0, "/home/elliotbot/clawd/Agency_OS/scripts")
try:
    from cognee_http_client import health, search
except ImportError as e:
    print("## Cognee health probe — IMPORT FAILED")
    print("")
    print(f"- {e}")
    sys.exit(0)

h = health()
print("## Cognee recall layer status")
print("")
if h.get("status") != "ready":
    print(f"- **DEGRADED** — server reports {h}")
    print("- Governance recall not available — operating on hot tier only")
    sys.exit(0)
print(f"- Server healthy: {h.get('version','?')}")
r = search("Sustainable Use License", top_k=1, search_type="GRAPH_COMPLETION")
if isinstance(r, dict) and "error" in r:
    print(f"- **SEARCH DEGRADED** — {r}")
    print("- Token auth or query path broken — recall unreliable")
elif isinstance(r, list) and r:
    print(f"- Search probe ok — returned {len(r)} response(s)")
elif isinstance(r, list):
    print("- Search returned empty — corpus may be empty or query path silent-failing")
else:
    print(f"- Search returned unexpected shape: {type(r).__name__}")
