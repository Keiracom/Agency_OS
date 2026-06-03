"""verify_temporal_dispatch.py — proof-gate checker for V1ChainWorkflow.

Exit 0 when workflow=COMPLETED AND keiracom_spawn_attribution has 5 rows
for the chain (or 0 with --dry-run-ok). Exit 1 otherwise.
Live schema uses task_type + ts (not chain_step / created_at named in spec).
"""

from __future__ import annotations

import argparse
import asyncio
import sys

EXPECTED = ("aiden", "max", "nova", "orion", "atlas")


def _load_env() -> None:
    try:
        from dotenv import load_dotenv  # noqa: PLC0415

        load_dotenv("/home/elliotbot/.config/agency-os/.env")
    except ImportError:
        pass


async def _verify(workflow_id: str, dry_run_ok: bool) -> int:
    from src.keiracom_system.temporal.client import from_env  # noqa: PLC0415

    try:
        client = await from_env()
    except OSError as exc:
        print(f"ERROR: Temporal connect failed: {exc}", file=sys.stderr)
        return 1
    desc = await client.get_workflow_handle(workflow_id).describe()
    status = desc.status.name if desc.status is not None else "UNKNOWN"
    print(f"workflow_id : {workflow_id}")
    print(f"status      : {status}")
    print(f"start_time  : {desc.start_time.isoformat() if desc.start_time else '-'}")
    print(f"close_time  : {desc.close_time.isoformat() if desc.close_time else '-'}\n")

    chain_id = workflow_id.removeprefix("v1-chain-")
    print(f"DB rows (keiracom_spawn_attribution, chain_id={chain_id}):")
    from src.keiracom_system.vault.agent_cold_start import _connect  # noqa: PLC0415

    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT callsign, task_type, cost_aud, latency_ms "
            "FROM public.keiracom_spawn_attribution "
            "WHERE chain_id = %s ORDER BY ts",
            (chain_id,),
        )
        rows = cur.fetchall()
    for cs, tt, cost, lat in rows:
        cost_s = f"${cost:.4f} AUD" if cost is not None else "$- AUD"
        lat_s = f"{int(lat)}ms" if lat is not None else "-ms"
        print(f"  {cs:<8}{tt:<16}{cost_s:<14}{lat_s}")
    print(f"row_count={len(rows)}\n")

    fails: list[str] = []
    if status != "COMPLETED":
        fails.append(f"workflow status={status}, expected COMPLETED")
    if len(rows) == 5:
        missing = [c for c in EXPECTED if c not in {r[0] for r in rows}]
        if missing:
            fails.append(f"missing callsigns: {missing}")
    elif not (dry_run_ok and len(rows) == 0):
        fails.append(f"row_count={len(rows)}, expected 5 (or 0 with --dry-run-ok)")
    if fails:
        print("FAIL: " + "; ".join(fails))
        return 1
    tail = "5 attribution rows" if len(rows) == 5 else "dry-run accepted (0 rows)"
    print(f"PASS: workflow completed + {tail}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("workflow_id", help="Temporal workflow id (e.g. v1-chain-proof-001)")
    p.add_argument(
        "--dry-run-ok",
        action="store_true",
        help="accept 0 DB rows as pass (for dry-run proof runs)",
    )
    args = p.parse_args()
    _load_env()
    return asyncio.run(_verify(args.workflow_id, args.dry_run_ok))


if __name__ == "__main__":
    sys.exit(main())
