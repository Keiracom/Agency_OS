# Phase 16F: Prefect Flows Specification

## Technical Specification Document

**Version**: 1.0  
**Date**: December 27, 2025  
**Depends On**: Phase 16A-E (All Detectors + Engine Mods)  
**Status**: Ready for Development  
**Estimated Tasks**: 4  

---

## Overview

Phase 16F creates Prefect flows to orchestrate the Conversion Intelligence System:

1. **Pattern Learning Flow** - Weekly batch job that runs all 4 detectors
2. **Pattern Health Check Flow** - Daily validation of pattern quality
3. **Pattern Backfill Flow** - One-time job to analyze historical data
4. **Schedules** - Cron-based scheduling for automated execution

**Key Principle**: Patterns are computed offline in batch, then consumed in real-time by engines.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PREFECT ORCHESTRATION                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      SCHEDULED FLOWS                                 │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                       │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │   │
│  │  │  Pattern        │  │  Pattern        │  │  Pattern            │  │   │
│  │  │  Learning       │  │  Health Check   │  │  Backfill           │  │   │
│  │  │                 │  │                 │  │                     │  │   │
│  │  │  Weekly         │  │  Daily          │  │  On-demand          │  │   │
│  │  │  Sunday 2am     │  │  6am            │  │  Manual trigger     │  │   │
│  │  └────────┬────────┘  └────────┬────────┘  └──────────┬──────────┘  │   │
│  │           │                    │                      │             │   │
│  └───────────┼────────────────────┼──────────────────────┼─────────────┘   │
│              │                    │                      │                 │
│              ▼                    ▼                      ▼                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         SHARED TASKS                                 │   │
│  │                                                                       │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ │   │
│  │  │  Run WHO │ │ Run WHAT │ │ Run WHEN │ │ Run HOW  │ │  Store     │ │   │
│  │  │ Detector │ │ Detector │ │ Detector │ │ Detector │ │  Patterns  │ │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────────┘ │   │
│  │                                                                       │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Pattern Learning Flow

### File: `src/orchestration/flows/pattern_learning_flow.py`

```python
"""
Pattern Learning Flow

Runs weekly to analyze conversion data and update patterns for all clients.
This is the core learning loop of the Conversion Intelligence System.

Schedule: Every Sunday at 2:00 AM UTC
"""

from datetime import datetime, timedelta
from typing import Optional, List
from prefect import flow, task, get_run_logger
from prefect.tasks import task_input_hash
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.models.client import Client
from src.models.conversion_patterns import ConversionPattern, ConversionPatternHistory

from src.algorithms.who_detector import WhoDetector
from src.algorithms.what_detector import WhatDetector
from src.algorithms.when_detector import WhenDetector
from src.algorithms.how_detector import HowDetector


# =============================================================================
# CONFIGURATION
# =============================================================================

PATTERN_VALIDITY_DAYS = 14  # Patterns valid for 2 weeks
MIN_CONFIDENCE_THRESHOLD = 0.3  # Minimum confidence to store pattern
PARALLEL_CLIENTS = 5  # Process clients in parallel batches


# =============================================================================
# TASKS
# =============================================================================

@task(
    name="get-active-clients",
    description="Fetch all active clients for pattern learning",
    retries=2,
    retry_delay_seconds=30,
)
async def get_active_clients() -> List[str]:
    """
    Get list of active client IDs.
    
    Returns clients that:
    - Have active subscription
    - Have at least 1 converted lead (for learning)
    - Are not paused
    """
    logger = get_run_logger()
    
    async with get_async_session() as db:
        query = select(Client.id).where(
            and_(
                Client.subscription_status == "active",
                Client.is_paused == False,
                Client.deleted_at.is_(None),
            )
        )
        result = await db.execute(query)
        client_ids = [row[0] for row in result.fetchall()]
    
    logger.info(f"Found {len(client_ids)} active clients for pattern learning")
    return client_ids


@task(
    name="run-who-detector",
    description="Run WHO Detector for a client",
    retries=1,
    retry_delay_seconds=60,
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(hours=1),
)
async def run_who_detector(client_id: str) -> Optional[dict]:
    """
    Run WHO Detector and return patterns.
    """
    logger = get_run_logger()
    
    try:
        async with get_async_session() as db:
            detector = WhoDetector()
            patterns = await detector.analyze(db, client_id)
            
            if patterns.confidence >= MIN_CONFIDENCE_THRESHOLD:
                logger.info(
                    f"WHO patterns for {client_id}: "
                    f"confidence={patterns.confidence}, "
                    f"samples={patterns.sample_size}"
                )
                return patterns.to_dict() if hasattr(patterns, 'to_dict') else {
                    "type": "who",
                    "recommended_weights": patterns.recommended_weights,
                    "title_rankings": patterns.title_rankings,
                    "industry_rankings": patterns.industry_rankings,
                    "timing_signals": patterns.timing_signals,
                    "sample_size": patterns.sample_size,
                    "confidence": patterns.confidence,
                }
            else:
                logger.info(
                    f"WHO patterns for {client_id} below threshold: "
                    f"confidence={patterns.confidence}"
                )
                return None
                
    except Exception as e:
        logger.error(f"WHO Detector failed for {client_id}: {str(e)}")
        return None


@task(
    name="run-what-detector",
    description="Run WHAT Detector for a client",
    retries=1,
    retry_delay_seconds=60,
)
async def run_what_detector(client_id: str) -> Optional[dict]:
    """
    Run WHAT Detector and return patterns.
    """
    logger = get_run_logger()
    
    try:
        async with get_async_session() as db:
            detector = WhatDetector()
            patterns = await detector.analyze(db, client_id)
            
            if patterns.confidence >= MIN_CONFIDENCE_THRESHOLD:
                logger.info(
                    f"WHAT patterns for {client_id}: "
                    f"confidence={patterns.confidence}, "
                    f"samples={patterns.sample_size}"
                )
                return patterns.to_dict()
            else:
                logger.info(
                    f"WHAT patterns for {client_id} below threshold"
                )
                return None
                
    except Exception as e:
        logger.error(f"WHAT Detector failed for {client_id}: {str(e)}")
        return None


@task(
    name="run-when-detector",
    description="Run WHEN Detector for a client",
    retries=1,
    retry_delay_seconds=60,
)
async def run_when_detector(client_id: str) -> Optional[dict]:
    """
    Run WHEN Detector and return patterns.
    """
    logger = get_run_logger()
    
    try:
        async with get_async_session() as db:
            detector = WhenDetector()
            patterns = await detector.analyze(db, client_id)
            
            if patterns.confidence >= MIN_CONFIDENCE_THRESHOLD:
                logger.info(
                    f"WHEN patterns for {client_id}: "
                    f"confidence={patterns.confidence}, "
                    f"samples={patterns.sample_size}"
                )
                return patterns.to_dict()
            else:
                return None
                
    except Exception as e:
        logger.error(f"WHEN Detector failed for {client_id}: {str(e)}")
        return None


@task(
    name="run-how-detector",
    description="Run HOW Detector for a client",
    retries=1,
    retry_delay_seconds=60,
)
async def run_how_detector(client_id: str) -> Optional[dict]:
    """
    Run HOW Detector and return patterns.
    """
    logger = get_run_logger()
    
    try:
        async with get_async_session() as db:
            detector = HowDetector()
            patterns = await detector.analyze(db, client_id)
            
            if patterns.confidence >= MIN_CONFIDENCE_THRESHOLD:
                logger.info(
                    f"HOW patterns for {client_id}: "
                    f"confidence={patterns.confidence}, "
                    f"samples={patterns.sample_size}"
                )
                return patterns.to_dict()
            else:
                return None
                
    except Exception as e:
        logger.error(f"HOW Detector failed for {client_id}: {str(e)}")
        return None


@task(
    name="store-patterns",
    description="Store patterns in database",
    retries=2,
    retry_delay_seconds=30,
)
async def store_patterns(
    client_id: str,
    who_patterns: Optional[dict],
    what_patterns: Optional[dict],
    when_patterns: Optional[dict],
    how_patterns: Optional[dict],
) -> dict:
    """
    Store all patterns for a client.
    
    - Upserts current patterns in conversion_patterns table
    - Archives to conversion_pattern_history for tracking
    - Updates client.als_learned_weights if WHO patterns available
    """
    logger = get_run_logger()
    stored = {"who": False, "what": False, "when": False, "how": False}
    
    async with get_async_session() as db:
        valid_until = datetime.utcnow() + timedelta(days=PATTERN_VALIDITY_DAYS)
        
        patterns_to_store = [
            ("who", who_patterns),
            ("what", what_patterns),
            ("when", when_patterns),
            ("how", how_patterns),
        ]
        
        for pattern_type, patterns in patterns_to_store:
            if patterns is None:
                continue
            
            try:
                # Upsert current pattern
                existing = await db.execute(
                    select(ConversionPattern).where(
                        and_(
                            ConversionPattern.client_id == client_id,
                            ConversionPattern.pattern_type == pattern_type,
                        )
                    )
                )
                existing_pattern = existing.scalar_one_or_none()
                
                if existing_pattern:
                    # Update existing
                    existing_pattern.patterns = patterns
                    existing_pattern.sample_size = patterns.get("sample_size", 0)
                    existing_pattern.confidence = patterns.get("confidence", 0)
                    existing_pattern.computed_at = datetime.utcnow()
                    existing_pattern.valid_until = valid_until
                else:
                    # Create new
                    new_pattern = ConversionPattern(
                        client_id=client_id,
                        pattern_type=pattern_type,
                        patterns=patterns,
                        sample_size=patterns.get("sample_size", 0),
                        confidence=patterns.get("confidence", 0),
                        computed_at=datetime.utcnow(),
                        valid_until=valid_until,
                    )
                    db.add(new_pattern)
                
                # Archive to history
                history = ConversionPatternHistory(
                    client_id=client_id,
                    pattern_type=pattern_type,
                    patterns=patterns,
                    sample_size=patterns.get("sample_size", 0),
                    computed_at=datetime.utcnow(),
                )
                db.add(history)
                
                stored[pattern_type] = True
                
                # Update client weights if WHO pattern
                if pattern_type == "who" and patterns.get("recommended_weights"):
                    client = await db.get(Client, client_id)
                    if client:
                        client.als_learned_weights = patterns["recommended_weights"]
                        client.als_weights_updated_at = datetime.utcnow()
                        client.conversion_sample_count = patterns.get("sample_size", 0)
                
            except Exception as e:
                logger.error(
                    f"Failed to store {pattern_type} pattern for {client_id}: {str(e)}"
                )
        
        await db.commit()
    
    logger.info(f"Stored patterns for {client_id}: {stored}")
    return stored


@task(
    name="process-client",
    description="Run all detectors for a single client",
)
async def process_client(client_id: str) -> dict:
    """
    Process all detectors for a single client.
    Returns summary of what was learned.
    """
    logger = get_run_logger()
    logger.info(f"Processing client: {client_id}")
    
    # Run all detectors (can be parallelized within client)
    who_patterns = await run_who_detector(client_id)
    what_patterns = await run_what_detector(client_id)
    when_patterns = await run_when_detector(client_id)
    how_patterns = await run_how_detector(client_id)
    
    # Store results
    stored = await store_patterns(
        client_id=client_id,
        who_patterns=who_patterns,
        what_patterns=what_patterns,
        when_patterns=when_patterns,
        how_patterns=how_patterns,
    )
    
    return {
        "client_id": client_id,
        "patterns_stored": stored,
        "has_who": who_patterns is not None,
        "has_what": what_patterns is not None,
        "has_when": when_patterns is not None,
        "has_how": how_patterns is not None,
    }


# =============================================================================
# MAIN FLOW
# =============================================================================

@flow(
    name="pattern-learning-flow",
    description="Weekly pattern learning for all clients",
    version="1.0.0",
    retries=1,
    retry_delay_seconds=300,
)
async def pattern_learning_flow(
    client_ids: Optional[List[str]] = None,
) -> dict:
    """
    Main pattern learning flow.
    
    Args:
        client_ids: Optional list of specific clients to process.
                   If None, processes all active clients.
    
    Returns:
        Summary of pattern learning results.
    """
    logger = get_run_logger()
    logger.info("Starting Pattern Learning Flow")
    start_time = datetime.utcnow()
    
    # Get clients to process
    if client_ids is None:
        client_ids = await get_active_clients()
    
    if not client_ids:
        logger.warning("No clients to process")
        return {"status": "no_clients", "processed": 0}
    
    # Process clients
    results = []
    errors = []
    
    for client_id in client_ids:
        try:
            result = await process_client(client_id)
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to process client {client_id}: {str(e)}")
            errors.append({"client_id": client_id, "error": str(e)})
    
    # Summary
    duration = (datetime.utcnow() - start_time).total_seconds()
    
    summary = {
        "status": "completed",
        "started_at": start_time.isoformat(),
        "duration_seconds": round(duration, 2),
        "clients_processed": len(results),
        "clients_failed": len(errors),
        "patterns_created": {
            "who": sum(1 for r in results if r.get("has_who")),
            "what": sum(1 for r in results if r.get("has_what")),
            "when": sum(1 for r in results if r.get("has_when")),
            "how": sum(1 for r in results if r.get("has_how")),
        },
        "errors": errors,
    }
    
    logger.info(f"Pattern Learning Flow completed: {summary}")
    return summary
```

---

## 2. Pattern Health Check Flow

### File: `src/orchestration/flows/pattern_health_flow.py`

```python
"""
Pattern Health Check Flow

Runs daily to validate pattern quality and alert on issues.

Schedule: Every day at 6:00 AM UTC
"""

from datetime import datetime, timedelta
from typing import List, Optional
from prefect import flow, task, get_run_logger
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.models.client import Client
from src.models.conversion_patterns import ConversionPattern


# =============================================================================
# CONFIGURATION
# =============================================================================

# Thresholds for warnings
MIN_SAMPLE_SIZE = 30
MIN_CONFIDENCE = 0.5
MAX_WEIGHT_VALUE = 0.45
MIN_WEIGHT_VALUE = 0.08
EXPIRING_SOON_DAYS = 3


# =============================================================================
# TASKS
# =============================================================================

@task(name="check-pattern-health")
async def check_pattern_health(client_id: str) -> dict:
    """
    Check health of patterns for a client.
    Returns list of warnings.
    """
    logger = get_run_logger()
    warnings = []
    
    async with get_async_session() as db:
        # Get all patterns for client
        query = select(ConversionPattern).where(
            ConversionPattern.client_id == client_id
        )
        result = await db.execute(query)
        patterns = list(result.scalars().all())
        
        for pattern in patterns:
            pattern_type = pattern.pattern_type
            
            # Check if expired or expiring soon
            if pattern.valid_until < datetime.utcnow():
                warnings.append({
                    "type": "expired",
                    "pattern": pattern_type,
                    "message": f"{pattern_type} pattern has expired",
                    "severity": "high",
                })
            elif pattern.valid_until < datetime.utcnow() + timedelta(days=EXPIRING_SOON_DAYS):
                warnings.append({
                    "type": "expiring_soon",
                    "pattern": pattern_type,
                    "message": f"{pattern_type} pattern expires in {EXPIRING_SOON_DAYS} days",
                    "severity": "medium",
                })
            
            # Check sample size
            if pattern.sample_size < MIN_SAMPLE_SIZE:
                warnings.append({
                    "type": "low_sample",
                    "pattern": pattern_type,
                    "message": f"{pattern_type} has low sample size: {pattern.sample_size}",
                    "severity": "medium",
                })
            
            # Check confidence
            if pattern.confidence < MIN_CONFIDENCE:
                warnings.append({
                    "type": "low_confidence",
                    "pattern": pattern_type,
                    "message": f"{pattern_type} has low confidence: {pattern.confidence}",
                    "severity": "medium",
                })
            
            # Check WHO pattern weights
            if pattern_type == "who" and pattern.patterns:
                weights = pattern.patterns.get("recommended_weights", {})
                for key, value in weights.items():
                    if value > MAX_WEIGHT_VALUE:
                        warnings.append({
                            "type": "extreme_weight",
                            "pattern": pattern_type,
                            "message": f"Extreme high weight for {key}: {value}",
                            "severity": "high",
                        })
                    elif value < MIN_WEIGHT_VALUE:
                        warnings.append({
                            "type": "extreme_weight",
                            "pattern": pattern_type,
                            "message": f"Extreme low weight for {key}: {value}",
                            "severity": "medium",
                        })
        
        # Check for missing patterns
        existing_types = {p.pattern_type for p in patterns}
        for required in ["who", "what", "when", "how"]:
            if required not in existing_types:
                # Check if client has enough data
                client = await db.get(Client, client_id)
                if client and (client.conversion_sample_count or 0) >= 10:
                    warnings.append({
                        "type": "missing_pattern",
                        "pattern": required,
                        "message": f"Missing {required} pattern despite having conversions",
                        "severity": "medium",
                    })
    
    return {
        "client_id": client_id,
        "warnings": warnings,
        "warning_count": len(warnings),
        "high_severity_count": sum(1 for w in warnings if w["severity"] == "high"),
    }


@task(name="get-clients-with-patterns")
async def get_clients_with_patterns() -> List[str]:
    """Get clients that have at least one pattern."""
    async with get_async_session() as db:
        query = select(ConversionPattern.client_id).distinct()
        result = await db.execute(query)
        return [row[0] for row in result.fetchall()]


@task(name="send-health-alerts")
async def send_health_alerts(results: List[dict]) -> dict:
    """
    Send alerts for clients with high severity warnings.
    """
    logger = get_run_logger()
    
    high_severity_clients = [
        r for r in results 
        if r["high_severity_count"] > 0
    ]
    
    if high_severity_clients:
        # Log warnings (in production, send to Slack/email)
        for client in high_severity_clients:
            logger.warning(
                f"Pattern health issues for {client['client_id']}: "
                f"{client['warning_count']} warnings, "
                f"{client['high_severity_count']} high severity"
            )
            for warning in client["warnings"]:
                if warning["severity"] == "high":
                    logger.warning(f"  - {warning['message']}")
    
    return {
        "alerts_sent": len(high_severity_clients),
        "clients_with_issues": [c["client_id"] for c in high_severity_clients],
    }


# =============================================================================
# MAIN FLOW
# =============================================================================

@flow(
    name="pattern-health-flow",
    description="Daily pattern health check",
    version="1.0.0",
)
async def pattern_health_flow() -> dict:
    """
    Daily health check for all client patterns.
    """
    logger = get_run_logger()
    logger.info("Starting Pattern Health Check Flow")
    
    # Get clients with patterns
    client_ids = await get_clients_with_patterns()
    
    if not client_ids:
        logger.info("No clients with patterns to check")
        return {"status": "no_clients", "checked": 0}
    
    # Check each client
    results = []
    for client_id in client_ids:
        result = await check_pattern_health(client_id)
        results.append(result)
    
    # Send alerts
    alert_summary = await send_health_alerts(results)
    
    # Summary
    total_warnings = sum(r["warning_count"] for r in results)
    
    summary = {
        "status": "completed",
        "clients_checked": len(results),
        "total_warnings": total_warnings,
        "clients_healthy": sum(1 for r in results if r["warning_count"] == 0),
        "clients_with_warnings": sum(1 for r in results if r["warning_count"] > 0),
        "alerts_sent": alert_summary["alerts_sent"],
    }
    
    logger.info(f"Pattern Health Check completed: {summary}")
    return summary
```

---

## 3. Pattern Backfill Flow

### File: `src/orchestration/flows/pattern_backfill_flow.py`

```python
"""
Pattern Backfill Flow

One-time or on-demand flow to backfill patterns from historical data.
Use when:
- Onboarding a new client with existing data
- Recovering from data issues
- Re-analyzing after algorithm updates

Trigger: Manual via API or Prefect UI
"""

from datetime import datetime
from typing import Optional, List
from prefect import flow, task, get_run_logger

from src.orchestration.flows.pattern_learning_flow import (
    run_who_detector,
    run_what_detector,
    run_when_detector,
    run_how_detector,
    store_patterns,
)


# =============================================================================
# TASKS
# =============================================================================

@task(name="backfill-content-snapshots")
async def backfill_content_snapshots(client_id: str) -> dict:
    """
    Backfill content_snapshot for historical activities.
    
    For activities that predate the content capture system,
    we can reconstruct partial snapshots from available data.
    """
    logger = get_run_logger()
    
    from sqlalchemy import select, and_
    from src.database import get_async_session
    from src.models.activity import Activity
    from src.engines.content_utils import build_content_snapshot
    
    updated = 0
    skipped = 0
    
    async with get_async_session() as db:
        # Get activities without content_snapshot
        query = select(Activity).where(
            and_(
                Activity.client_id == client_id,
                Activity.content_snapshot.is_(None),
                Activity.action.in_([
                    'email_sent', 'sms_sent', 
                    'linkedin_sent', 'voice_completed'
                ])
            )
        ).limit(1000)
        
        result = await db.execute(query)
        activities = list(result.scalars().all())
        
        for activity in activities:
            # Try to reconstruct from metadata
            if activity.metadata:
                body = activity.metadata.get("body") or activity.metadata.get("message")
                subject = activity.metadata.get("subject")
                
                if body:
                    # Get lead for personalization detection
                    lead = await db.get(Lead, activity.lead_id)
                    if lead:
                        activity.content_snapshot = build_content_snapshot(
                            body=body,
                            lead=lead,
                            subject=subject,
                            touch_number=activity.metadata.get("touch_number", 1),
                            channel=activity.channel,
                        )
                        updated += 1
                        continue
            
            skipped += 1
        
        await db.commit()
    
    logger.info(f"Backfilled {updated} activities, skipped {skipped}")
    return {"updated": updated, "skipped": skipped}


@task(name="backfill-als-components")
async def backfill_als_components(client_id: str) -> dict:
    """
    Backfill als_components for historical leads.
    
    Re-scores leads to populate component snapshots.
    """
    logger = get_run_logger()
    
    from sqlalchemy import select, and_
    from src.database import get_async_session
    from src.models.lead import Lead
    from src.models.client import Client
    from src.engines.scorer import ScorerEngine
    
    updated = 0
    
    async with get_async_session() as db:
        # Get client
        client = await db.get(Client, client_id)
        if not client:
            return {"error": "Client not found"}
        
        # Get leads without als_components
        query = select(Lead).where(
            and_(
                Lead.client_id == client_id,
                Lead.als_components.is_(None),
                Lead.deleted_at.is_(None),
            )
        ).limit(500)
        
        result = await db.execute(query)
        leads = list(result.scalars().all())
        
        scorer = ScorerEngine()
        
        for lead in leads:
            await scorer.score_lead(db, lead, client)
            updated += 1
        
        await db.commit()
    
    logger.info(f"Backfilled als_components for {updated} leads")
    return {"updated": updated}


# =============================================================================
# MAIN FLOW
# =============================================================================

@flow(
    name="pattern-backfill-flow",
    description="Backfill patterns from historical data",
    version="1.0.0",
)
async def pattern_backfill_flow(
    client_id: str,
    backfill_content: bool = True,
    backfill_als: bool = True,
    run_detectors: bool = True,
) -> dict:
    """
    Backfill flow for a specific client.
    
    Args:
        client_id: Client to backfill
        backfill_content: Whether to backfill content_snapshot
        backfill_als: Whether to backfill als_components
        run_detectors: Whether to run detectors after backfill
    """
    logger = get_run_logger()
    logger.info(f"Starting Pattern Backfill for client: {client_id}")
    
    results = {
        "client_id": client_id,
        "started_at": datetime.utcnow().isoformat(),
    }
    
    # Step 1: Backfill content snapshots
    if backfill_content:
        content_result = await backfill_content_snapshots(client_id)
        results["content_backfill"] = content_result
    
    # Step 2: Backfill ALS components
    if backfill_als:
        als_result = await backfill_als_components(client_id)
        results["als_backfill"] = als_result
    
    # Step 3: Run detectors
    if run_detectors:
        who_patterns = await run_who_detector(client_id)
        what_patterns = await run_what_detector(client_id)
        when_patterns = await run_when_detector(client_id)
        how_patterns = await run_how_detector(client_id)
        
        stored = await store_patterns(
            client_id=client_id,
            who_patterns=who_patterns,
            what_patterns=what_patterns,
            when_patterns=when_patterns,
            how_patterns=how_patterns,
        )
        
        results["patterns_stored"] = stored
        results["patterns_created"] = {
            "who": who_patterns is not None,
            "what": what_patterns is not None,
            "when": when_patterns is not None,
            "how": how_patterns is not None,
        }
    
    results["completed_at"] = datetime.utcnow().isoformat()
    
    logger.info(f"Pattern Backfill completed: {results}")
    return results
```

---

## 4. Schedules

### File: `src/orchestration/schedules/pattern_schedules.py`

```python
"""
Pattern Learning Schedules

Defines cron schedules for pattern-related flows.
"""

from prefect.deployments import Deployment
from prefect.server.schemas.schedules import CronSchedule

from src.orchestration.flows.pattern_learning_flow import pattern_learning_flow
from src.orchestration.flows.pattern_health_flow import pattern_health_flow


# =============================================================================
# SCHEDULE DEFINITIONS
# =============================================================================

def create_deployments():
    """
    Create Prefect deployments with schedules.
    
    Run this once to register deployments.
    """
    
    # Weekly Pattern Learning - Sunday 2:00 AM UTC
    pattern_learning_deployment = Deployment.build_from_flow(
        flow=pattern_learning_flow,
        name="weekly-pattern-learning",
        version="1.0.0",
        tags=["conversion-intelligence", "weekly"],
        schedule=CronSchedule(
            cron="0 2 * * 0",  # Sunday at 2:00 AM UTC
            timezone="UTC",
        ),
        parameters={},
        description="Weekly pattern learning for all clients",
    )
    
    # Daily Health Check - 6:00 AM UTC
    health_check_deployment = Deployment.build_from_flow(
        flow=pattern_health_flow,
        name="daily-pattern-health",
        version="1.0.0",
        tags=["conversion-intelligence", "daily"],
        schedule=CronSchedule(
            cron="0 6 * * *",  # Every day at 6:00 AM UTC
            timezone="UTC",
        ),
        parameters={},
        description="Daily pattern health check",
    )
    
    return [
        pattern_learning_deployment,
        health_check_deployment,
    ]


async def register_deployments():
    """Register all deployments with Prefect server."""
    deployments = create_deployments()
    
    for deployment in deployments:
        await deployment.apply()
        print(f"Registered: {deployment.name}")


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import asyncio
    asyncio.run(register_deployments())
```

---

## 5. API Endpoints for Manual Triggers

### File: `src/api/routes/patterns.py`

```python
"""
Pattern API Endpoints

Provides API access to:
- View current patterns
- Trigger pattern learning manually
- Trigger backfill for a client
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.conversion_patterns import ConversionPattern
from src.auth import get_current_user, require_admin
from src.orchestration.flows.pattern_learning_flow import pattern_learning_flow
from src.orchestration.flows.pattern_backfill_flow import pattern_backfill_flow


router = APIRouter(prefix="/patterns", tags=["patterns"])


# =============================================================================
# GET PATTERNS
# =============================================================================

@router.get("/{client_id}")
async def get_patterns(
    client_id: str,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
) -> dict:
    """
    Get all current patterns for a client.
    """
    query = select(ConversionPattern).where(
        ConversionPattern.client_id == client_id
    )
    result = await db.execute(query)
    patterns = list(result.scalars().all())
    
    return {
        "client_id": client_id,
        "patterns": {
            p.pattern_type: {
                "patterns": p.patterns,
                "sample_size": p.sample_size,
                "confidence": p.confidence,
                "computed_at": p.computed_at.isoformat(),
                "valid_until": p.valid_until.isoformat(),
                "is_valid": p.valid_until > datetime.utcnow(),
            }
            for p in patterns
        },
    }


@router.get("/{client_id}/{pattern_type}")
async def get_pattern(
    client_id: str,
    pattern_type: str,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
) -> dict:
    """
    Get a specific pattern for a client.
    """
    if pattern_type not in ["who", "what", "when", "how"]:
        raise HTTPException(400, f"Invalid pattern type: {pattern_type}")
    
    query = select(ConversionPattern).where(
        ConversionPattern.client_id == client_id,
        ConversionPattern.pattern_type == pattern_type,
    )
    result = await db.execute(query)
    pattern = result.scalar_one_or_none()
    
    if not pattern:
        raise HTTPException(404, f"No {pattern_type} pattern found")
    
    return {
        "client_id": client_id,
        "pattern_type": pattern_type,
        "patterns": pattern.patterns,
        "sample_size": pattern.sample_size,
        "confidence": pattern.confidence,
        "computed_at": pattern.computed_at.isoformat(),
        "valid_until": pattern.valid_until.isoformat(),
    }


# =============================================================================
# TRIGGER FLOWS
# =============================================================================

@router.post("/learn")
async def trigger_learning(
    client_ids: Optional[List[str]] = None,
    user = Depends(require_admin),
) -> dict:
    """
    Manually trigger pattern learning.
    
    Admin only. If client_ids not provided, runs for all clients.
    """
    from prefect.deployments import run_deployment
    
    # Trigger the flow
    flow_run = await run_deployment(
        name="pattern-learning-flow/weekly-pattern-learning",
        parameters={"client_ids": client_ids},
    )
    
    return {
        "status": "triggered",
        "flow_run_id": str(flow_run.id),
        "client_ids": client_ids or "all",
    }


@router.post("/backfill/{client_id}")
async def trigger_backfill(
    client_id: str,
    backfill_content: bool = True,
    backfill_als: bool = True,
    run_detectors: bool = True,
    user = Depends(require_admin),
) -> dict:
    """
    Trigger pattern backfill for a specific client.
    
    Admin only.
    """
    from prefect import get_client
    
    async with get_client() as client:
        flow_run = await client.create_flow_run_from_deployment(
            deployment_id="pattern-backfill-flow",
            parameters={
                "client_id": client_id,
                "backfill_content": backfill_content,
                "backfill_als": backfill_als,
                "run_detectors": run_detectors,
            },
        )
    
    return {
        "status": "triggered",
        "flow_run_id": str(flow_run.id),
        "client_id": client_id,
    }
```

---

## File Structure

```
src/orchestration/
├── __init__.py
├── flows/
│   ├── __init__.py
│   ├── pattern_learning_flow.py    # Weekly learning
│   ├── pattern_health_flow.py      # Daily health check
│   └── pattern_backfill_flow.py    # On-demand backfill
└── schedules/
    ├── __init__.py
    └── pattern_schedules.py        # Cron schedules

src/api/routes/
└── patterns.py                     # API endpoints
```

---

## Tasks

| Task | Description | File(s) | Est. Hours |
|------|-------------|---------|------------|
| 16F.1 | Create pattern_learning_flow | `src/orchestration/flows/pattern_learning_flow.py` | 2 |
| 16F.2 | Create pattern_health_flow | `src/orchestration/flows/pattern_health_flow.py` | 1.5 |
| 16F.3 | Create pattern_backfill_flow | `src/orchestration/flows/pattern_backfill_flow.py` | 1.5 |
| 16F.4 | Create schedules + API endpoints | `schedules/`, `api/routes/patterns.py` | 1.5 |

**Total: 4 tasks, ~6.5 hours**

---

## Testing

```python
# tests/orchestration/test_pattern_flows.py

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from src.orchestration.flows.pattern_learning_flow import (
    pattern_learning_flow,
    run_who_detector,
    store_patterns,
)
from src.orchestration.flows.pattern_health_flow import (
    pattern_health_flow,
    check_pattern_health,
)


class TestPatternLearningFlow:
    
    @pytest.mark.asyncio
    async def test_processes_all_clients(self):
        """Flow should process all active clients"""
        with patch("get_active_clients") as mock_clients:
            mock_clients.return_value = ["client-1", "client-2"]
            
            with patch("process_client") as mock_process:
                mock_process.return_value = {
                    "client_id": "test",
                    "has_who": True,
                }
                
                result = await pattern_learning_flow()
                
                assert result["clients_processed"] == 2
    
    @pytest.mark.asyncio
    async def test_stores_valid_patterns(self):
        """Should store patterns above confidence threshold"""
        patterns = {
            "type": "who",
            "confidence": 0.8,
            "sample_size": 100,
            "recommended_weights": {
                "data_quality": 0.20,
                "authority": 0.25,
                "company_fit": 0.25,
                "timing": 0.15,
            },
        }
        
        result = await store_patterns(
            client_id="test-client",
            who_patterns=patterns,
            what_patterns=None,
            when_patterns=None,
            how_patterns=None,
        )
        
        assert result["who"] == True


class TestPatternHealthFlow:
    
    @pytest.mark.asyncio
    async def test_detects_expired_patterns(self):
        """Should warn about expired patterns"""
        # Create mock pattern that's expired
        expired_pattern = MockPattern(
            pattern_type="who",
            valid_until=datetime.utcnow() - timedelta(days=1),
            confidence=0.8,
            sample_size=100,
        )
        
        with patch("get_patterns") as mock_get:
            mock_get.return_value = [expired_pattern]
            
            result = await check_pattern_health("test-client")
            
            assert result["warning_count"] > 0
            assert any(w["type"] == "expired" for w in result["warnings"])
    
    @pytest.mark.asyncio
    async def test_detects_low_confidence(self):
        """Should warn about low confidence patterns"""
        low_conf_pattern = MockPattern(
            pattern_type="who",
            valid_until=datetime.utcnow() + timedelta(days=7),
            confidence=0.2,  # Below threshold
            sample_size=100,
        )
        
        with patch("get_patterns") as mock_get:
            mock_get.return_value = [low_conf_pattern]
            
            result = await check_pattern_health("test-client")
            
            assert any(w["type"] == "low_confidence" for w in result["warnings"])
```

---

## Schedule Summary

| Flow | Schedule | Purpose |
|------|----------|---------|
| Pattern Learning | Sunday 2:00 AM UTC | Run all detectors, update patterns |
| Pattern Health | Daily 6:00 AM UTC | Validate patterns, send alerts |
| Pattern Backfill | Manual trigger | One-time historical analysis |

---

**End of Phase 16F Specification**
