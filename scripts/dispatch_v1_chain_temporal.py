"""dispatch_v1_chain_temporal.py — CLI to start a V1ChainWorkflow on Temporal.

Usage:
    python scripts/dispatch_v1_chain_temporal.py \\
        --task-id <id> --brief <text> [--dry-run] [--chain-id <id>]

Env:
    TEMPORAL_ADDR   — required (e.g. 45.76.114.137:7233)
    ANTHROPIC_API_KEY — required for live runs (not checked here; worker uses it)
"""

from __future__ import annotations

import argparse
import asyncio
import sys


def _load_env() -> None:
    try:
        from dotenv import load_dotenv  # noqa: PLC0415

        load_dotenv("/home/elliotbot/.config/agency-os/.env")
    except ImportError:
        pass


async def _dispatch(task_id: str, chain_id: str, brief: str, dry_run: bool) -> int:
    from src.keiracom_system.temporal.client import from_env  # noqa: PLC0415
    from src.keiracom_system.temporal.v1_chain_workflow import (  # noqa: PLC0415
        ChainWorkflowInput,
    )

    try:
        client = await from_env()
    except OSError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    workflow_id = f"v1-chain-{task_id}"
    try:
        handle = await client.start_workflow(
            "V1ChainWorkflow",
            ChainWorkflowInput(
                task_id=task_id,
                chain_id=chain_id,
                brief=brief,
                dry_run=dry_run,
            ),
            id=workflow_id,
            task_queue="keiracom-default",
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: start_workflow failed: {exc}", file=sys.stderr)
        return 1

    print(f"workflow_id={handle.id}")
    print(f"run_id={handle.result_run_id}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Start a V1ChainWorkflow on Temporal."
    )
    parser.add_argument("--task-id", required=True, help="Unique task identifier")
    parser.add_argument("--brief", required=True, help="Task brief passed to each chain hop")
    parser.add_argument("--chain-id", default="", help="Chain ID (defaults to task-id)")
    parser.add_argument("--dry-run", action="store_true", help="Skip Anthropic API; return fake atom_ids")
    args = parser.parse_args()

    _load_env()
    chain_id = args.chain_id or args.task_id
    return asyncio.run(_dispatch(args.task_id, chain_id, args.brief, args.dry_run))


if __name__ == "__main__":
    raise SystemExit(main())
