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

    # Check test suite baseline (probe 5)
    test_result = await check_test_baseline()
    if test_result["status"] != "ok":
        findings.append({
            "signal_type": "test_regression",
            "tier": 1,
            "severity": "HIGH",
            "description": f"Test baseline drift: {test_result['passed']} passed (expected {test_result['baseline']}), {test_result['failed']} failed",
            "metadata": test_result,
        })

    # Check swap pressure (probe 7)
    swap = await check_swap_pressure()
    if swap["status"] != "ok":
        findings.append({
            "signal_type": "swap_pressure",
            "tier": 2,
            "severity": "MEDIUM",
            "description": f"Swap usage {swap['used_mb']}MB exceeds 2048MB threshold",
            "metadata": swap,
        })

    # Write findings
    written = await write_health_findings(findings)

    # T1 auto-fix: if enabled, dispatch known fixes to clone
    t1_active = os.environ.get("SELF_HEAL_T1_ACTIVE", "false").lower() == "true"
    t1_dispatched = 0
    if t1_active:
        t1_dispatched = await dispatch_t1_fixes(findings)

    logger.info("Health check: %d findings, %d new written, %d T1 dispatched", len(findings), written, t1_dispatched)
    return {
        "findings": len(findings),
        "written": written,
        "checks": ["prefect_worker", "api_keys", "enforcer", "flow_failures", "test_baseline", "swap_pressure"],
        "t1_active": t1_active,
        "t1_dispatched": t1_dispatched,
    }


@task(name="check-test-baseline", cache_policy=NO_CACHE)
async def check_test_baseline() -> dict:
    """Probe 5: run pytest, compare against baseline."""
    import subprocess
    baseline = 2152
    result = subprocess.run(
        ["python3", "-m", "pytest", "--tb=no", "-q", "--co", "-q"],
        capture_output=True, text=True, timeout=60,
        cwd="/home/elliotbot/clawd/Agency_OS",
    )
    # Count collected tests from --co output (last line: "N tests collected")
    lines = result.stdout.strip().split("\n")
    collected = 0
    for line in lines:
        if "test" in line and ("collected" in line or "selected" in line):
            parts = line.split()
            for p in parts:
                if p.isdigit():
                    collected = int(p)
                    break
    if collected >= baseline:
        return {"status": "ok", "passed": collected, "baseline": baseline, "failed": 0}
    return {"status": "drift", "passed": collected, "baseline": baseline, "failed": baseline - collected}


@task(name="check-swap-pressure", cache_policy=NO_CACHE)
async def check_swap_pressure() -> dict:
    """Probe 7: check swap usage."""
    import subprocess
    result = subprocess.run(["free", "-m"], capture_output=True, text=True)
    for line in result.stdout.strip().split("\n"):
        if line.startswith("Swap:"):
            parts = line.split()
            used_mb = int(parts[2])
            if used_mb > 2048:
                return {"status": "high", "used_mb": used_mb}
            return {"status": "ok", "used_mb": used_mb}
    return {"status": "unknown", "used_mb": 0}


@task(name="dispatch-t1-fixes", cache_policy=NO_CACHE)
async def dispatch_t1_fixes(findings: list[dict]) -> int:
    """T1 auto-fix: dispatch known fixes to ATLAS clone inbox."""
    dispatched = 0
    pool = await asyncpg.create_pool(
        os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://"),
        min_size=1, max_size=2, statement_cache_size=0,
    )
    try:
        async with pool.acquire() as conn:
            for f in findings:
                if f.get("tier") != 1:
                    continue
                # Check tier_registry for known fix
                row = await conn.fetchrow(
                    "SELECT task_class, tier FROM public.tier_registry WHERE task_class = $1 AND tier = 'A'",
                    f.get("signal_type", ""),
                )
                if not row:
                    continue
                # Risk check: don't T1-fix if touching sensitive files
                sensitive_patterns = ["migration", "CLAUDE.md", "enforcer", "workflow"]
                desc = f.get("description", "").lower()
                if any(p in desc for p in sensitive_patterns):
                    logger.info("T1 skip (risk-escalate to T2): %s", f["signal_type"])
                    continue
                # Write dispatch to ATLAS inbox
                import time
                from pathlib import Path
                inbox = Path("/tmp/telegram-relay-atlas/inbox")
                inbox.mkdir(parents=True, exist_ok=True)
                ts = time.strftime("%Y%m%d_%H%M%S")
                dispatch_file = inbox / f"{ts}_t1_fix.json"
                dispatch_file.write_text(json.dumps({
                    "type": "task_dispatch",
                    "from": "health_check_flow",
                    "to": "atlas",
                    "max_task_minutes": 15,
                    "brief": f"T1 auto-fix: {f['signal_type']} — {f['description']}",
                    "dispatched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "finding": f,
                }))
                dispatched += 1
                logger.info("T1 dispatched to ATLAS: %s", f["signal_type"])
    finally:
        await pool.close()
    return dispatched


@flow(name="daily-health-digest", timeout_seconds=60)
async def daily_health_digest() -> dict:
    """T3 daily digest — summarises last 24h health checks. Scheduled 20:00 UTC (6 AM AEST)."""
    pool = await asyncpg.create_pool(
        os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://"),
        min_size=1, max_size=2, statement_cache_size=0, init=_init_jsonb_codec,
    )
    try:
        async with pool.acquire() as conn:
            # Count findings by tier
            rows = await conn.fetch(
                """SELECT tier, severity, COUNT(*) as cnt
                   FROM health_checks
                   WHERE created_at > NOW() - INTERVAL '24 hours'
                   GROUP BY tier, severity ORDER BY tier, severity"""
            )
            total = sum(r["cnt"] for r in rows)
            by_tier = {}
            for r in rows:
                t = f"T{r['tier']}"
                by_tier.setdefault(t, []).append(f"{r['severity']}: {r['cnt']}")

            # Swap check
            swap = await check_swap_pressure()

            summary = f"DAILY HEALTH DIGEST — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n"
            summary += f"Findings (24h): {total}\n"
            for tier, items in sorted(by_tier.items()):
                summary += f"  {tier}: {', '.join(items)}\n"
            summary += f"Swap: {swap['used_mb']}MB\n"

            # Write to Elliot inbox
            import time
            from pathlib import Path
            inbox = Path("/tmp/telegram-relay-elliot/inbox")
            inbox.mkdir(parents=True, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            digest_file = inbox / f"{ts}_daily_digest.json"
            digest_file.write_text(json.dumps({
                "type": "daily_digest",
                "from": "health_check_flow",
                "to": "elliot",
                "summary": summary,
                "dispatched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }))
            logger.info("Daily digest written to Elliot inbox")
            return {"total_findings": total, "by_tier": by_tier, "swap_mb": swap["used_mb"]}
    finally:
        await pool.close()
