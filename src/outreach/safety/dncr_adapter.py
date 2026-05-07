"""
Contract: src/outreach/safety/dncr_adapter.py
Purpose: Bridge DNCRClient (integration layer) to ComplianceGuard's
         injectable dncr_lookup callable. Handles the three-state result
         (registered=True/False/None) and applies the AU business-interest
         rule for degraded API responses.
Layer:   3 - engines
Imports: stdlib + src.integrations.dncr_client
Consumers: src/outreach/safety/compliance_guard.py (as dncr_lookup arg)
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from src.integrations.dncr import DNCRResult
from src.integrations.dncr import SyncDNCRClient as DNCRClient

logger = logging.getLogger(__name__)


def build_dncr_lookup(
    client: DNCRClient | None = None,
    *,
    log_degraded: bool = True,
) -> Callable[[str], bool]:
    """Return a callable(phone) -> bool suitable for ComplianceGuard.

    Returns True only when registered=True. Degraded API results
    (registered=None) return False with a warning log so the send is
    ALLOWED under the AU business-interest B2B exemption. This matches
    Dave's ratified policy: unknown state is a caution signal, not a block.

    If client is None, constructs a default DNCRClient() (reads env vars).
    """
    dncr = client or DNCRClient()

    def _lookup(phone: str) -> bool:
        if not phone:
            return False
        result: DNCRResult = dncr.lookup(phone)
        if result.registered is True:
            return True
        if result.registered is None and log_degraded:
            logger.warning(
                "DNCR degraded for %s (status=%s) — allowing send under "
                "AU business-interest B2B exemption. Operator audit required.",
                phone,
                result.status,
            )
        return False

    return _lookup
