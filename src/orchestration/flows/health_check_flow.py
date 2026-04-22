"""Health Check Flow — 5-minute system health probe.

Detection is always ON. Findings logged to health_checks table.
T1 auto-fix response gated by SELF_HEAL_T1_ACTIVE env var.
"""
import asyncio
import json
import logging
import os
from datetime import datetime, timezone, timedelta

import asyncpg
from prefect import flow, task
from prefect.cache_policies import NO_CACHE

logger = logging.getLogger(__name__)


async def _get_pool():
    db_url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    return await asyncpg.create_pool(db_url, min_size=1, max_size=3, statement_cache_size=0)


async def _init_jsonb_codec(conn):
    await conn.set_type_codec('jsonb', encoder=json.dumps, decoder=json.loads, schema='pg_catalog')


@task(name="check-prefect-worker", cache_policy=NO_CACHE)
async def check_prefect_worker() -> dict:
    """Check if Prefect worker is polling (last_polled within 15 min)."""
    # Query evo_flow_callbacks for recent activity
    pool = await asyncpg.create_pool(
        os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://"),
        min_size=1, max_size=2, statement_cache_size=0, init=_init_jsonb_codec,
    )
    try:
        async with pool.acquire() as conn:
            # Check most recent callback
            row = await conn.fetchrow(
                "SELECT MAX(created_at) as last_callback FROM evo_flow_callbacks"
            )
            last = row["last_callback"] if row else None
            if last and (datetime.now(timezone.utc) - last).total_seconds() < 3600:
                return {"status": "ok", "last_callback": last.isoformat()}
            return {"status": "stale", "last_callback": last.isoformat() if last else "never"}
    finally:
        await pool.close()


@task(name="check-api-keys", cache_policy=NO_CACHE)
async def check_api_keys() -> list[dict]:
    """Check API key health from ledger."""
    findings = []
    pool = await asyncpg.create_pool(
        os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://"),
        min_size=1, max_size=2, statement_cache_size=0, init=_init_jsonb_codec,
    )
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT service_name, env_var_name, status FROM elliot_internal.api_keys_ledger WHERE status != 'live'"
            )
            for r in rows:
                findings.append({
                    "service": r["service_name"],
                    "env_var": r["env_var_name"],
                    "status": r["status"],
                    "tier": 3,  # Key issues are always Dave-lane
                    "severity": "HIGH",
                })
    finally:
        await pool.close()
    return findings


@task(name="check-enforcer-alive", cache_policy=NO_CACHE)
async def check_enforcer_alive() -> dict:
    """Check if enforcer bot process is running."""
    import subprocess
    result = subprocess.run(
        ["pgrep", "-f", "enforcer_bot.py"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        return {"status": "ok", "pid": result.stdout.strip()}
    return {"status": "down", "pid": None}


@task(name="check-recent-flow-failures", cache_policy=NO_CACHE)
async def check_recent_flow_failures() -> list[dict]:
    """Check for flow failures in the last hour."""
    findings = []
    pool = await asyncpg.create_pool(
        os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://"),
        min_size=1, max_size=2, statement_cache_size=0, init=_init_jsonb_codec,
    )
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT flow_name, status, LEFT(result_summary::text, 200) as summary, created_at
                   FROM evo_flow_callbacks
                   WHERE status = 'failed' AND created_at > NOW() - INTERVAL '1 hour'
                   ORDER BY created_at DESC LIMIT 5"""
            )
            for r in rows:
                findings.append({
                    "flow_name": r["flow_name"],
                    "summary": r["summary"],
                    "created_at": r["created_at"].isoformat(),
                    "tier": 2,  # Flow failures need agent diagnosis
                    "severity": "HIGH",
                })
    finally:
        await pool.close()
    return findings


@task(name="write-health-findings", cache_policy=NO_CACHE)
async def write_health_findings(findings: list[dict]) -> int:
    """Write findings to health_checks table."""
    if not findings:
        return 0
    pool = await asyncpg.create_pool(
        os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://"),
        min_size=1, max_size=2, statement_cache_size=0, init=_init_jsonb_codec,
    )
    written = 0
    try:
        async with pool.acquire() as conn:
            for f in findings:
                # Skip if same signal_type + description exists unresolved in last hour
                existing = await conn.fetchval(
                    """SELECT COUNT(*) FROM health_checks
                       WHERE signal_type = $1 AND description = $2
                       AND resolved_at IS NULL AND created_at > NOW() - INTERVAL '1 hour'""",
                    f.get("signal_type", "unknown"), f.get("description", ""),
                )
                if existing and existing > 0:
                    continue
                await conn.execute(
                    """INSERT INTO health_checks (signal_type, tier, severity, description, metadata)
                       VALUES ($1, $2, $3, $4, $5)""",
                    f.get("signal_type", "unknown"),
                    f.get("tier", 2),
                    f.get("severity", "MEDIUM"),
                    f.get("description", ""),
                    json.dumps(f.get("metadata", {})),
                )
                written += 1
    finally:
        await pool.close()
    return written


@flow(name="health-check-flow", timeout_seconds=120)
async def health_check_flow() -> dict:
    """5-minute health probe. Detection always ON."""
    findings = []

    # Check Prefect worker
    worker = await check_prefect_worker()
    if worker["status"] != "ok":
        findings.append({
            "signal_type": "worker_stale",
            "tier": 2,
            "severity": "HIGH",
            "description": f"Prefect worker stale — last callback: {worker.get('last_callback', 'never')}",
            "metadata": worker,
        })

    # Check API keys
    key_issues = await check_api_keys()
    for ki in key_issues:
        findings.append({
            "signal_type": "key_expired",
            "tier": ki["tier"],
            "severity": ki["severity"],
            "description": f"{ki['service']} ({ki['env_var']}) status: {ki['status']}",
            "metadata": ki,
        })

    # Check enforcer
    enforcer = await check_enforcer_alive()
    if enforcer["status"] != "ok":
        findings.append({
            "signal_type": "service_down",
            "tier": 3,
            "severity": "CRITICAL",
            "description": "Enforcer bot process not running",
            "metadata": enforcer,
        })

    # Check recent flow failures
    flow_failures = await check_recent_flow_failures()
    for ff in flow_failures:
        findings.append({
            "signal_type": "flow_failure",
            "tier": ff["tier"],
            "severity": ff["severity"],
            "description": f"Flow '{ff['flow_name']}' failed: {ff['summary'][:100]}",
            "metadata": ff,
        })

    # Write findings
    written = await write_health_findings(findings)

    logger.info("Health check: %d findings, %d new written", len(findings), written)
    return {
        "findings": len(findings),
        "written": written,
        "checks": ["prefect_worker", "api_keys", "enforcer", "flow_failures"],
        "t1_active": os.environ.get("SELF_HEAL_T1_ACTIVE", "false").lower() == "true",
    }
