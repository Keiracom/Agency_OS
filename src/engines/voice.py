"""
FILE: src/engines/voice.py
PURPOSE: DEPRECATED - Vapi voice engine stub
STATUS: DEPRECATED as of 2026-02-25 (CEO Directive)

Voice stack is now: ElevenAgents + Twilio AU
Active implementation: src/integrations/elevenagets_client.py
Active flow: src/orchestration/flows/voice_flow.py

This file exists only to prevent import errors from legacy code.
Original Vapi implementation archived to: src/engines/deprecated/voice_vapi.py
"""

import warnings
from typing import Any


def _deprecated_warning():
    warnings.warn(
        "voice.py (Vapi) is deprecated. Use elevenagets_client.py instead. "
        "Voice stack: ElevenAgents + Twilio AU.",
        DeprecationWarning,
        stacklevel=3,
    )


class VoiceEngine:
    """DEPRECATED: Vapi voice engine. Use ElevenAgents via elevenagets_client.py"""

    def __init__(self, *args, **kwargs):
        _deprecated_warning()
        raise NotImplementedError(
            "VoiceEngine (Vapi) is deprecated. "
            "Use ElevenAgentsClient from src/integrations/elevenagets_client.py"
        )


def get_voice_engine(*args, **kwargs) -> VoiceEngine:
    """DEPRECATED: Returns Vapi voice engine. Use get_elevenagets_client() instead."""
    _deprecated_warning()
    raise NotImplementedError(
        "get_voice_engine() is deprecated. "
        "Use get_elevenagets_client() from src/integrations/elevenagets_client.py"
    )
