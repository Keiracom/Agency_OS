"""GOV-PHASE3 — TG alert helper for Gatekeeper deny verdicts.

Wraps the `tg -g` relay CLI used by both bots. Used by scripts/check_claim.py
to surface deny verdicts to the supergroup so peer + Dave see them in real
time, not just buried in governance_events.

Contract:
    alert_on_deny(callsign, directive_id, reasons, claim_text_sha256_16) -> bool

Returns True if relay write succeeded, False otherwise. Wrapped — never raises.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from collections.abc import Iterable

logger = logging.getLogger(__name__)

_TG_BIN = "tg"
_TIMEOUT_S = 5


def alert_on_deny(
    callsign: str,
    directive_id: str,
    reasons: Iterable[str],
    claim_text_sha256_16: str,
) -> bool:
    """Post a Gatekeeper deny verdict to the TG supergroup via `tg -g`.

    Returns True on subprocess exit 0, False on any failure.
    """
    if shutil.which(_TG_BIN) is None:
        logger.warning("alert_on_deny: tg binary not on PATH; skipping")
        return False

    reason_lines = "\n".join(f"  - {r}" for r in reasons) or "  (no reasons reported)"
    msg = (
        f"[GATEKEEPER-DENY:{callsign}] directive={directive_id} "
        f"claim_hash={claim_text_sha256_16}\n"
        f"deny_reasons:\n{reason_lines}"
    )
    try:
        result = subprocess.run(
            [_TG_BIN, "-g", msg],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_S,
            check=False,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("alert_on_deny: subprocess failed: %s", exc)
        return False
