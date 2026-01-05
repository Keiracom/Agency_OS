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
"""

# Agency OS - Integrations Package

from src.integrations.serper import SerperClient, get_serper_client
from src.integrations.vapi import VapiClient, get_vapi_client
from src.integrations.elevenlabs import ElevenLabsClient, get_elevenlabs_client
from src.integrations.clicksend import ClickSendClient, get_clicksend_client

__all__ = [
    "SerperClient",
    "get_serper_client",
    "VapiClient",
    "get_vapi_client",
    "ElevenLabsClient",
    "get_elevenlabs_client",
    "ClickSendClient",
    "get_clicksend_client",
]
