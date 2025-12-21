# FIXED by fixer-agent: added contract comment format
"""
FILE: src/orchestration/tasks/__init__.py
PURPOSE: Prefect tasks package - Reusable task definitions for flows
PHASE: 5 (Orchestration)
TASK: ORC-006 to ORC-009
DEPENDENCIES:
  - src/engines/*
  - src/integrations/*
  - src/models/*
RULES APPLIED:
  - Rule 12: LAYER 4 - Can import from everything below
  - Rule 13: JIT validation in all tasks
  - Rule 11: Session passed as argument

This module contains all Prefect tasks organized by function:
- enrichment_tasks: Lead enrichment via Scout engine
- scoring_tasks: Lead scoring via Scorer engine
- outreach_tasks: Multi-channel outreach (email, SMS, LinkedIn, voice, mail)
- reply_tasks: Reply handling via Closer engine

All tasks include:
- JIT validation (Rule 13)
- Retry logic with exponential backoff
- Proper logging
- Type hints and docstrings
"""

from src.orchestration.tasks.enrichment_tasks import (
    check_enrichment_cache_task,
    enrich_batch_task,
    enrich_lead_task,
)
from src.orchestration.tasks.outreach_tasks import (
    generate_content_task,
    send_email_task,
    send_linkedin_task,
    send_mail_task,
    send_sms_task,
    send_voice_task,
)
from src.orchestration.tasks.reply_tasks import (
    classify_intent_task,
    poll_email_replies_task,
    poll_linkedin_replies_task,
    poll_sms_replies_task,
    process_reply_task,
)
from src.orchestration.tasks.scoring_tasks import (
    get_tier_distribution_task,
    score_batch_task,
    score_lead_task,
)

__all__ = [
    # Enrichment
    "enrich_lead_task",
    "enrich_batch_task",
    "check_enrichment_cache_task",
    # Scoring
    "score_lead_task",
    "score_batch_task",
    "get_tier_distribution_task",
    # Outreach
    "send_email_task",
    "send_sms_task",
    "send_linkedin_task",
    "send_voice_task",
    "send_mail_task",
    "generate_content_task",
    # Reply
    "process_reply_task",
    "classify_intent_task",
    "poll_email_replies_task",
    "poll_sms_replies_task",
    "poll_linkedin_replies_task",
]
