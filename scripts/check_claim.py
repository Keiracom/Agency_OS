#!/usr/bin/env python3
"""scripts/check_claim.py — CLI verification gate for gatekeeper completion claims.

Calls check_completion_claim() from src.governance.gatekeeper against a live OPA
instance. Used by agents before reporting directive completion.

Usage (flags):
    scripts/check_claim.py --callsign elliot --directive-id GOV-PHASE3 \\
      --claim-text "Phase 3 complete" \\
      --evidence "$ pytest -q\\n5 passed" \\
      --target-files "src/foo.py,src/bar.py" \\
      --store-writes '[{"directive_id":"GOV-PHASE3","store":"manual"},...]'

Usage (stdin):
    echo '{...}' | scripts/check_claim.py --stdin

Exit codes:
    0  — ALLOW (claim accepted)
    1  — DENY  (claim rejected, reasons printed to stderr)
    2  — usage / argument error
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

# Repo-root on sys.path so src.governance imports resolve regardless of cwd.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))



def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="check_claim.py",
        description=(
            "Gatekeeper CLI — evaluates a completion claim against the OPA "
            "policy.  Exits 0 on ALLOW, 1 on DENY."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--stdin",
        action="store_true",
        help="Read a JSON payload from stdin instead of using individual flags.",
    )
    p.add_argument("--callsign", help="Agent callsign (e.g. elliot, atlas).")
    p.add_argument("--directive-id", dest="directive_id", help="Directive identifier.")
    p.add_argument("--claim-text", dest="claim_text", help="What the agent claims to have done.")
    p.add_argument("--evidence", help="Raw terminal output proving the claim.")
    p.add_argument(
        "--target-files",
        dest="target_files",
        help="Comma-separated list of files touched by this directive.",
    )
    p.add_argument(
        "--store-writes",
        dest="store_writes",
        help='JSON array of {directive_id, store} objects covering the four-store write.',
    )
    p.add_argument(
        "--frozen-paths",
        dest="frozen_paths",
        default="",
        help="Comma-separated frozen paths (optional; defaults to live registry).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the payload that would be sent to OPA without calling it.",
    )
    return p


def _payload_from_args(args: argparse.Namespace) -> dict:
    """Build the claim payload from CLI flags."""
    missing = []
    for field in ("callsign", "directive_id", "claim_text", "evidence", "target_files", "store_writes"):
        if not getattr(args, field, None):
            missing.append(f"--{field.replace('_', '-')}")
    if missing:
        print(f"error: missing required flags: {', '.join(missing)}", file=sys.stderr)
        sys.exit(2)

    try:
        store_writes = json.loads(args.store_writes)
    except json.JSONDecodeError as exc:
        print(f"error: --store-writes is not valid JSON: {exc}", file=sys.stderr)
        sys.exit(2)

    target_files = [f.strip() for f in args.target_files.split(",") if f.strip()]
    frozen_paths = (
        [p.strip() for p in args.frozen_paths.split(",") if p.strip()]
        if args.frozen_paths
        else None
    )

    return {
        "callsign": args.callsign,
        "directive_id": args.directive_id,
        "claim_text": args.claim_text,
        "evidence": args.evidence,
        "target_files": target_files,
        "store_writes": store_writes,
        "frozen_paths": frozen_paths,
    }


def _payload_from_stdin() -> dict:
    """Read and parse a JSON payload from stdin."""
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"error: stdin is not valid JSON: {exc}", file=sys.stderr)
        sys.exit(2)


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.stdin:
        payload = _payload_from_stdin()
    else:
        payload = _payload_from_args(args)

    if args.dry_run:
        print("DRY-RUN — payload that would be sent to OPA:")
        print(json.dumps(payload, indent=2))
        return 0

    from src.governance.gatekeeper import check_completion_claim

    frozen_paths = payload.pop("frozen_paths", None)

    result = check_completion_claim(
        frozen_paths=frozen_paths,
        **payload,
    )

    claim_text = payload.get("claim_text", "")
    directive_id = payload.get("directive_id", "")
    callsign = payload.get("callsign", "")
    truncated = claim_text[:80] + ("..." if len(claim_text) > 80 else "")

    if result.allow:
        print(f"ALLOW: {truncated}")
        return 0

    reasons_str = "; ".join(result.reasons) if result.reasons else "policy denied (no reasons returned)"
    print(f"DENY: {reasons_str}", file=sys.stderr)

    try:
        from src.governance.tg_alert import alert_on_deny
        claim_hash = hashlib.sha256(claim_text.encode()).hexdigest()[:16]
        alert_on_deny(
            callsign=callsign,
            directive_id=directive_id,
            reasons=result.reasons or [reasons_str],
            claim_text_sha256_16=claim_hash,
        )
    except Exception:
        pass  # Never block the gate on a notification failure

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
