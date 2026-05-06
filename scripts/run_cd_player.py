"""
CD Player v1 — CLI dev entrypoint.

Instantiates PipelineOrchestrator with real clients and calls run_streaming().

Usage:
    python scripts/run_cd_player.py --categories dental,plumbing --target-cards 5
    python scripts/run_cd_player.py --categories legal --target-cards 10 --budget 30
    python scripts/run_cd_player.py --categories accounting --target-cards 3 --dry-run

This script is the canonical local dev/test runner for the CD Player v1 pipeline.
It does NOT use cohort_runner.run_cohort() — it exercises the streaming
orchestrator path directly so integration issues surface early.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, "/home/elliotbot/clawd/Agency_OS")

from dotenv import dotenv_values

env = dotenv_values("/home/elliotbot/.config/agency-os/.env")
for _k, _v in env.items():
    if _v is not None:
        os.environ.setdefault(_k, _v)

from src.clients.dfs_labs_client import DFSLabsClient
from src.integrations.bright_data_client import BrightDataClient
from src.integrations.leadmagic import LeadmagicClient
from src.intelligence.gemini_client import GeminiClient
from src.pipeline.pipeline_orchestrator import PipelineOrchestrator, ProspectCard

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("cd_player_cli")


# ---------------------------------------------------------------------------
# Discovery adapter — wraps DFSLabsClient for pull_batch interface
# ---------------------------------------------------------------------------


class DFSDiscoveryAdapter:
    """
    Minimal discovery adapter that implements pull_batch() using
    DFSLabsClient.domain_metrics_by_categories().
    """

    def __init__(self, dfs: DFSLabsClient) -> None:
        self._dfs = dfs

    async def pull_batch(
        self,
        category_code: str,
        location_name: str = "Australia",
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        try:
            rows = await self._dfs.domain_metrics_by_categories(
                category_codes=[int(category_code)],
                location_name=location_name,
                paid_etv_min=0.0,
                limit=limit,
                offset=offset,
            )
            return rows or []
        except Exception as exc:
            logger.warning("DFSDiscoveryAdapter.pull_batch error: %s", exc)
            return []


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="CD Player v1 — streaming pipeline CLI")
    p.add_argument(
        "--categories",
        default="dental,plumbing",
        help="Comma-separated category names (default: dental,plumbing)",
    )
    p.add_argument(
        "--target-cards",
        type=int,
        default=5,
        help="Stop after N cards emitted (default: 5)",
    )
    p.add_argument(
        "--budget",
        type=float,
        default=50.0,
        help="Hard budget cap in AUD (default: 50.0)",
    )
    p.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Parallel worker coroutines (default: 4)",
    )
    p.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Discovery batch size per pull (default: 50)",
    )
    p.add_argument(
        "--output-dir",
        default=None,
        help="Directory to write results JSON (default: scripts/output/cd_player_<ts>)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Set DRY_RUN=1 — all API clients return empty responses, no spend",
    )
    # T4 — tier-aware runtime params (forwarded to run_streaming.tier_config)
    p.add_argument(
        "--tier",
        default="ignition",
        choices=["spark", "ignition", "velocity", "demo"],
        help="Pricing tier profile (default: ignition)",
    )
    p.add_argument(
        "--demo-mode",
        action="store_true",
        help="Force minimal-spend demo profile regardless of tier",
    )
    p.add_argument(
        "--client-id",
        default=None,
        help="Logical client identifier carried through tier_config",
    )
    return p.parse_args()


async def main() -> None:
    args = _parse_args()

    if args.dry_run:
        os.environ["DRY_RUN"] = "1"
        logger.info("[DRY-RUN] No API calls will be made. No spend.")

    categories = [c.strip() for c in args.categories.split(",") if c.strip()]
    logger.info(
        "CD Player v1 starting — categories=%s target_cards=%d budget=$%.2f AUD workers=%d",
        categories,
        args.target_cards,
        args.budget,
        args.workers,
    )

    # Init clients
    dfs = DFSLabsClient(
        login=env.get("DATAFORSEO_LOGIN", ""),
        password=env.get("DATAFORSEO_PASSWORD", ""),
    )
    gemini = GeminiClient(api_key=env.get("GEMINI_API_KEY"))
    bd = BrightDataClient(api_key=env.get("BRIGHTDATA_API_KEY", ""))
    lm = LeadmagicClient()
    discovery = DFSDiscoveryAdapter(dfs)

    cards_collected: list[dict] = []

    def on_card(card: ProspectCard) -> None:
        d = asdict(card)
        cards_collected.append(d)
        logger.info(
            "CARD #%d: %s (%s) — %s — dm=%s email=%s",
            len(cards_collected),
            card.company_name,
            card.domain,
            card.location_display or card.location,
            card.dm_name,
            card.dm_email,
        )

    orchestrator = PipelineOrchestrator(
        dfs_client=dfs,
        gemini_client=gemini,
        bd_client=bd,
        lm_client=lm,
        discovery=discovery,
        on_card=on_card,
    )

    t0 = time.monotonic()
    result = await orchestrator.run_streaming(
        categories=categories,
        target_cards=args.target_cards,
        budget_cap_aud=args.budget,
        num_workers=args.workers,
        batch_size=args.batch_size,
        tier_config={
            "tier": args.tier,
            "demo_mode": args.demo_mode,
            "client_id": args.client_id,
        },
    )
    elapsed = time.monotonic() - t0

    await dfs.close()

    # Write outputs
    ts = int(time.time())
    out_dir = (
        Path(args.output_dir) if args.output_dir else Path("scripts/output") / f"cd_player_{ts}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cards.json").write_text(json.dumps(cards_collected, indent=2, default=str))

    summary = {
        "cards_emitted": len(result.prospects),
        "domains_discovered": result.stats.discovered,
        "total_cost_usd": round(result.stats.total_cost_usd, 4),
        "total_cost_aud": round(result.stats.total_cost_usd * 1.55, 4),
        "elapsed_s": round(elapsed, 1),
        "categories": categories,
        "target_cards": args.target_cards,
        "budget_cap_aud": args.budget,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))

    logger.info("CD Player complete. Summary: %s", json.dumps(summary))
    logger.info("Output written to: %s", out_dir)

    if args.dry_run:
        os.environ.pop("DRY_RUN", None)


if __name__ == "__main__":
    asyncio.run(main())
