# FIXED by fixer-agent: added contract comment
"""
FILE: src/orchestration/flows/__init__.py
PURPOSE: Prefect flows package - Campaign activation, enrichment, outreach flows
PHASE: 5 (Orchestration), modified Phase 16, 24A for Lead Pool
TASK: ORC-002 to ORC-005, 16F-001, POOL-011
DEPENDENCIES:
  - src/engines/*
  - src/integrations/*
  - src/models/*
  - src/detectors/* (Phase 16)
  - src/services/* (Phase 24A)
RULES APPLIED:
  - Rule 12: LAYER 4 - Can import from everything below
  - Rule 13: JIT validation in all flows
  - Rule 20: Webhook-first architecture
"""

from src.orchestration.flows.campaign_flow import campaign_activation_flow
from src.orchestration.flows.daily_digest_flow import (
    daily_digest_flow,
    send_client_digest_flow,
)
from src.orchestration.flows.enrichment_flow import daily_enrichment_flow
from src.orchestration.flows.outreach_flow import hourly_outreach_flow as outreach_flow
from src.orchestration.flows.pattern_backfill_flow import (
    pattern_backfill_flow,
    single_client_backfill_flow,
)
from src.orchestration.flows.pattern_learning_flow import (
    single_client_pattern_learning_flow,
    weekly_pattern_learning_flow,
)
from src.orchestration.flows.pool_assignment_flow import (
    jit_validate_outreach_batch_flow,
    pool_campaign_assignment_flow,
    pool_daily_allocation_flow,
)
from src.orchestration.flows.reply_recovery_flow import reply_recovery_flow
from src.orchestration.flows.stale_lead_refresh_flow import (
    daily_outreach_prep_flow,
    refresh_stale_leads_flow,
)

__all__ = [
    # Core flows
    "campaign_activation_flow",
    "daily_enrichment_flow",
    "outreach_flow",
    "reply_recovery_flow",
    # Phase 16: Conversion Intelligence
    "weekly_pattern_learning_flow",
    "single_client_pattern_learning_flow",
    "pattern_backfill_flow",
    "single_client_backfill_flow",
    # Phase 24A: Lead Pool
    "pool_campaign_assignment_flow",
    "pool_daily_allocation_flow",
    "jit_validate_outreach_batch_flow",
    # SDK Architecture Phase 3: Data Freshness
    "refresh_stale_leads_flow",
    "daily_outreach_prep_flow",
    # Phase H, Item 44: Daily Digest
    "daily_digest_flow",
    "send_client_digest_flow",
]
