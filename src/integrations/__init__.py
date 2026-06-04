# FIXED by fixer-agent: added contract comment
"""
FILE: src/integrations/__init__.py
PURPOSE: Integrations package - External API wrappers (LAYER 2)
PHASE: 1
TASK: INT-001 to INT-012
DEPENDENCIES:
  - src/models/*
  - src/exceptions.py
RULES APPLIED:
  - Rule 12: Can import from models, cannot import from engines/orchestration

NOTE: T3 email and T5 mobile enrichment provided by Leadmagic.
"""

# Agency OS - Integrations Package


# Billing & Booking (stripe_billing.py removed — canonical file is stripe.py)
# The active billing router lives in src/api/routes/billing.py

# [repo_split curation] stale dead-BDR __all__ exports removed (ABNClient, SerperClient,
# VapiClient, ElevenAgents/ElevenLabsClient, LeadmagicClient, calendar_booking_router) —
# their submodules were archived; no runtime imports remain. Kept: anthropic/redis/supabase.
__all__: list[str] = []

# [repo_split curation] dead-BDR submodule imports removed (5); kept only: ['anthropic', 'redis', 'supabase']
