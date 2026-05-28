"""CRLF / log-injection scrubber for untrusted values headed to a logger.

CodeQL py/log-injection flags user-controlled data reaching a logging call:
embedded CR/LF lets an attacker forge or split log lines. ``scrub`` escapes the
line breaks and bounds length. The ``.replace()`` of ``\\r`` and ``\\n`` is the
barrier CodeQL's taint tracking recognises, so wrapping a tainted value in
``scrub(...)`` at the log sink clears the finding.
"""

from __future__ import annotations

LOG_VALUE_CAP = 200


def scrub(value: object, limit: int = LOG_VALUE_CAP) -> str:
    """Return a single-line, length-bounded string safe to log.

    Coerces to ``str``, escapes CR and LF to their literal two-char forms so a
    crafted value can't inject extra log lines, then truncates to ``limit``.
    """
    return str(value).replace("\r", "\\r").replace("\n", "\\n")[:limit]
