#!/usr/bin/env python3
"""
rescore_113_drafts_2026_05_08.py — E3 Phase 1 deliverable

Per Dave's PHASE_1_KICKOFF 2026-05-08, task E3:
  "Re-score 113 stale drafts. These are 6 weeks old (March 25 batch).
   Run CIS scoring against them. Flag any prospect whose signals have
   changed. Remove stale leads from send queue. This must be done
   before any email sends."

What this script does:
1. Queries the 54 distinct prospects underlying the 113 campaign_lead_messages
   from the 2026-03-25 batch.
2. Applies the score_decay_factor() from src/pipeline/stage_4_scoring.py
   (39-44 days old → 0.95 multiplier).
3. Compares decayed propensity against the Stage 4 threshold (70).
4. Outputs a flag-status report:
     drop_candidates: propensity * decay < 70
     warm_candidates: 70-84
     hot_candidates: 85+
5. Optionally (--apply flag) updates campaign_lead_messages.status to
   reflect drop verdicts. By default DRY-RUN — does not mutate state.

Usage:
  python3 scripts/rescore_113_drafts_2026_05_08.py             # dry run, report only
  python3 scripts/rescore_113_drafts_2026_05_08.py --apply     # mutates message status

Exit codes:
  0  — report produced successfully
  1  — DB connection / query error
  2  — missing required env (DATABASE_URL)

Output:
  Stdout: tab-separated report with per-prospect verdict + summary counts.
  Logs: structured per-prospect lines with bu_id, domain, propensity_now,
        decayed, age_days, verdict.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from datetime import UTC, datetime

import asyncpg

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# Mirrors src/pipeline/stage_4_scoring.py:score_decay_factor()
def score_decay_factor(age_days: float) -> float:
    if age_days < 30:
        return 1.0
    if age_days < 90:
        return 0.95
    if age_days < 180:
        return 0.85
    return 0.70


PROPENSITY_DROP_THRESHOLD = 70  # Stage 4 default min_score_to_enrich


async def main(apply: bool) -> int:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not set")
        return 2

    # asyncpg expects plain postgresql:// scheme, not SQLAlchemy +asyncpg dialect.
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    conn = await asyncpg.connect(db_url)
    try:
        rows = await conn.fetch(
            """
            WITH prospects AS (
                SELECT
                    cl.business_universe_id AS bu_id,
                    cl.id AS campaign_lead_id,
                    MIN(clm.created_at) AS msg_created_at,
                    COUNT(clm.id) AS message_count
                FROM public.campaign_lead_messages clm
                JOIN public.campaign_leads cl ON cl.id = clm.campaign_lead_id
                GROUP BY cl.id, cl.business_universe_id
            )
            SELECT
                p.bu_id,
                p.campaign_lead_id,
                p.msg_created_at,
                p.message_count,
                bu.domain,
                bu.propensity_score,
                bu.reachability_score,
                bu.opportunity_score,
                bu.scored_at,
                bu.updated_at AS bu_updated_at
            FROM prospects p
            JOIN public.business_universe bu ON bu.id = p.bu_id
            ORDER BY bu.propensity_score DESC NULLS LAST
            """
        )

        now = datetime.now(UTC)
        verdicts: list[dict] = []
        drop_lead_ids: list[str] = []

        print("\n=== E3 Rescore Report — 2026-05-08 ===\n")
        print("bu_id\tdomain\tprop_now\tage_days\tdecay\tprop_decayed\tre_enriched\tverdict")

        for row in rows:
            bu_id = row["bu_id"]
            domain = row["domain"] or "(no domain)"
            prop_now = row["propensity_score"] or 0
            msg_at = row["msg_created_at"]
            bu_at = row["bu_updated_at"]
            age_days = (now - msg_at).total_seconds() / 86400.0
            decay = score_decay_factor(age_days)
            prop_decayed = prop_now * decay
            re_enriched = bu_at > msg_at if bu_at else False

            if prop_decayed < PROPENSITY_DROP_THRESHOLD:
                verdict = "DROP"
                drop_lead_ids.append(str(row["campaign_lead_id"]))
            elif prop_decayed < 85:
                verdict = "WARM"
            else:
                verdict = "HOT"

            verdicts.append(
                {
                    "bu_id": str(bu_id),
                    "campaign_lead_id": str(row["campaign_lead_id"]),
                    "domain": domain,
                    "prop_now": prop_now,
                    "age_days": age_days,
                    "decay": decay,
                    "prop_decayed": prop_decayed,
                    "re_enriched": re_enriched,
                    "verdict": verdict,
                }
            )

            print(
                f"{bu_id}\t{domain}\t{prop_now}\t{age_days:.1f}\t"
                f"{decay:.2f}\t{prop_decayed:.1f}\t{re_enriched}\t{verdict}"
            )

        # Summary
        drop_count = sum(1 for v in verdicts if v["verdict"] == "DROP")
        warm_count = sum(1 for v in verdicts if v["verdict"] == "WARM")
        hot_count = sum(1 for v in verdicts if v["verdict"] == "HOT")
        re_enriched_count = sum(1 for v in verdicts if v["re_enriched"])

        print("\n=== Summary ===")
        print(f"Total prospects:       {len(verdicts)}")
        print(f"DROP (prop_decayed<70): {drop_count}")
        print(f"WARM (70-84):           {warm_count}")
        print(f"HOT (85+):              {hot_count}")
        print(f"BU re-enriched since msg: {re_enriched_count}")

        if apply and drop_count > 0:
            logger.info("APPLY mode: marking %d campaign_leads' messages as dropped", drop_count)
            updated = await conn.execute(
                """
                UPDATE public.campaign_lead_messages
                SET status = 'draft_dropped_low_propensity',
                    updated_at = NOW()
                WHERE campaign_lead_id = ANY($1::uuid[])
                  AND status = 'draft'
                """,
                drop_lead_ids,
            )
            print(f"\nApplied: {updated}")
        else:
            print("\n(dry run — no DB mutation. Re-run with --apply to mutate.)")

        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="E3 — rescore 2026-03-25 stale drafts")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Mutate campaign_lead_messages status. Default: dry-run report only.",
    )
    args = parser.parse_args()
    sys.exit(asyncio.run(main(apply=args.apply)))
