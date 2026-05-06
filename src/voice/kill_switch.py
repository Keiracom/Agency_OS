"""Elliot Voice — kill switch processor.

Listens for trigger phrases in transcribed text and mutes/unmutes the
TTS output. Dave says "Elliot pause" → instant mute. Dave says "Elliot
go ahead" → resume.

Spec: docs/voice/elliot_voice_build_spec_v1.md Section 4.1.
"""

from __future__ import annotations

import logging
import re
from enum import Enum

logger = logging.getLogger(__name__)

# Trigger phrases — case-insensitive partial match on transcribed text
_MUTE_PATTERNS = [
    re.compile(r"elliot[\s,]+pause", re.IGNORECASE),
    re.compile(r"elliot[\s,]+stop", re.IGNORECASE),
    re.compile(r"elliot[\s,]+hold", re.IGNORECASE),
]

_RESUME_PATTERNS = [
    re.compile(r"elliot[\s,]+go\s+ahead", re.IGNORECASE),
    re.compile(r"elliot[\s,]+continue", re.IGNORECASE),
]


class KillSwitchState(Enum):
    ACTIVE = "active"
    MUTED = "muted"


class KillSwitch:
    """Monitors transcripts for kill switch trigger phrases.

    Usage:
        ks = KillSwitch()
        # On each transcript update:
        ks.check(transcript_text)
        if ks.is_muted:
            # suppress TTS output
    """

    def __init__(self) -> None:
        self._state = KillSwitchState.ACTIVE

    @property
    def is_muted(self) -> bool:
        return self._state == KillSwitchState.MUTED

    @property
    def state(self) -> KillSwitchState:
        return self._state

    def check(self, text: str) -> KillSwitchState:
        """Check transcript text for kill switch triggers.

        Returns the current state after processing.
        """
        if not text:
            return self._state

        # Check mute triggers first (higher priority)
        for pattern in _MUTE_PATTERNS:
            if pattern.search(text):
                if self._state != KillSwitchState.MUTED:
                    logger.warning("KILL SWITCH ACTIVATED: '%s'", text.strip()[:80])
                    self._state = KillSwitchState.MUTED
                return self._state

        # Check resume triggers
        for pattern in _RESUME_PATTERNS:
            if pattern.search(text):
                if self._state != KillSwitchState.ACTIVE:
                    logger.info("KILL SWITCH DEACTIVATED: '%s'", text.strip()[:80])
                    self._state = KillSwitchState.ACTIVE
                return self._state

        return self._state

    def reset(self) -> None:
        """Reset to active state."""
        self._state = KillSwitchState.ACTIVE
