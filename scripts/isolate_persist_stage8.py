"""Isolation test for persist_stage8_to_db against production schema.
Zero pipeline spend. Fabricated input. Cleanup after test.
"""
import asyncio
import os
import sys
import uuid
import logging

# Ensure repo root is on path when run as `python3 scripts/isolate_persist_stage8.py`
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

from dotenv import dotenv_values
env = dotenv_values("/home/elliotbot/.config/agency-os/.env")
for k, v in env.items():
    if v is not None:
        os.environ.setdefault(k, v)


def fabricate_pipeline() -> list[dict]:
    """Build a fake pipeline list matching Stage 8 output shape."""
    return [{
        "domain": "test-persist-isolation.example.com",
        "category": "dental",
        "dropped_at": None,
        "cost_usd": 0.05,
        "errors": [],
        "timings": {},
        "stage3": {
            "business_name": "Test Dental Clinic",
            "company_name": "Test Dental Clinic Pty Ltd",
            "dm_candidate": {
                "name": "Dr Test Person",
                "linkedin_url": "https://linkedin.com/in/test-persist-isolation",
                "_dm_verified": True,
            },
        },
        "stage4": {"dfs_signals": {}},
        "stage5": {"composite_score": 65},
        "stage7": {"outreach_draft": "test outreach"},
        "stage8_contacts": {
            "email": {"email": "test@example.com", "source": "test"},
            "linkedin": {"linkedin_url": "https://linkedin.com/in/test-persist-isolation"},
        },
        "stage9": {},
        "stage10": {"messages": {"email": {"body": "test email body"}}},
        "stage11": {"lead_pool_eligible": True},
    }]


async def test_persist():
    """Run persist_stage8_to_db with fabricated data, then clean up."""
    import asyncpg
    from src.orchestration.flows.pipeline_f_master_flow import persist_stage8_to_db

    pipeline = fabricate_pipeline()

    logger.info("Calling persist_stage8_to_db with fabricated pipeline...")
    try:
        bdm_ids = await persist_stage8_to_db.fn(pipeline)
        logger.info("SUCCESS: persist returned %d BDM IDs: %s", len(bdm_ids), bdm_ids)
    except Exception as e:
        logger.error("FAILED: %s: %s", type(e).__name__, e)
        import traceback
        traceback.print_exc()
        return False

    # Verify rows exist then clean up
    db_url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    pool = await asyncpg.create_pool(db_url, min_size=1, max_size=2, statement_cache_size=0)
    success = False
    try:
        async with pool.acquire() as conn:
            bu_row = await conn.fetchrow(
                "SELECT * FROM business_universe WHERE domain = $1",
                "test-persist-isolation.example.com",
            )
            if bu_row:
                logger.info(
                    "BU row found: id=%s, display_name=%s, pipeline_stage=%s",
                    bu_row["id"], bu_row["display_name"], bu_row["pipeline_stage"],
                )
            else:
                logger.error("BU row NOT FOUND after persist")
                return False

            if bdm_ids:
                bdm_uuid = uuid.UUID(bdm_ids[0]) if isinstance(bdm_ids[0], str) else bdm_ids[0]
                bdm_row = await conn.fetchrow(
                    "SELECT * FROM business_decision_makers WHERE id = $1",
                    bdm_uuid,
                )
                if bdm_row:
                    logger.info(
                        "BDM row found: id=%s, name=%s, linkedin=%s",
                        bdm_row["id"], bdm_row["name"], bdm_row["linkedin_url"],
                    )
                else:
                    logger.error("BDM row NOT FOUND after persist")
                    return False

            success = True

            # Cleanup
            for bid in bdm_ids:
                bid_uuid = uuid.UUID(bid) if isinstance(bid, str) else bid
                await conn.execute(
                    "DELETE FROM business_decision_makers WHERE id = $1", bid_uuid
                )
            await conn.execute(
                "DELETE FROM business_universe WHERE domain = $1",
                "test-persist-isolation.example.com",
            )
            logger.info("Cleanup: test rows deleted")
    finally:
        await pool.close()

    return success


if __name__ == "__main__":
    result = asyncio.run(test_persist())
    if result:
        print("\nPERSIST ISOLATION TEST PASSED")
    else:
        print("\nPERSIST ISOLATION TEST FAILED")
    raise SystemExit(0 if result else 1)
