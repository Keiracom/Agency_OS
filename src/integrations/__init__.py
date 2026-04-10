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

from src.integrations.abn_client import ABNClient, get_abn_client
from src.integrations.calendar_booking import router as calendar_booking_router
from src.integrations.elevenagets_client import ElevenAgentsClient, get_elevenagets_client
from src.integrations.elevenlabs import ElevenLabsClient, get_elevenlabs_client
from src.integrations.leadmagic import LeadmagicClient, get_leadmagic_client
from src.integrations.serper import SerperClient, get_serper_client
from src.integrations.siege_waterfall import SiegeWaterfall, get_siege_waterfall

# Billing & Booking (stripe_billing.py removed — canonical file is stripe.py)
# The active billing router lives in src/api/routes/billing.py
from src.integrations.vapi import VapiClient, get_vapi_client

__all__ = [
    "ABNClient",
    "get_abn_client",
    "SerperClient",
    "get_serper_client",
    "VapiClient",
    "get_vapi_client",
    "ElevenAgentsClient",
    "get_elevenagets_client",
    "ElevenLabsClient",
    "get_elevenlabs_client",
    "LeadmagicClient",
    "get_leadmagic_client",
    "SiegeWaterfall",
    "get_siege_waterfall",
    # Routers for FastAPI
    "calendar_booking_router",
]
