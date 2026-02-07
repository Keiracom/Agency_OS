"""
Contract: src/services/spending_guard.py
Purpose: Spending safeguards for domain provisioning - prevents runaway purchases
Layer: 3 - services
Consumers: domain_provisioning_service.py

SAFEGUARDS:
- MAX_DOMAINS_PER_CALL: 10 (prevents single runaway call)
- MAX_DOMAINS_PER_DAY: 30 (prevents loop bugs)
- MAX_SPEND_PER_DAY_AUD: 500 (hard dollar cap)
"""

import logging
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)

# ============================================
# HARD LIMITS - Change with caution
# ============================================

MAX_DOMAINS_PER_CALL = 10      # Single API call limit
MAX_DOMAINS_PER_DAY = 30       # Daily ceiling
MAX_SPEND_PER_DAY_AUD = 500    # Dollar cap (~40 domains)
DOMAIN_COST_AUD = 12           # Average domain cost

# ============================================
# DAILY TRACKING
# In production, consider using Redis for persistence
# across service restarts
# ============================================

_daily_stats = {
    "date": None,
    "domains_purchased": 0,
    "spend_aud": 0.0,
}


class SpendingLimitExceeded(Exception):
    """Raised when any spending limit would be exceeded."""
    pass


def _reset_if_new_day() -> None:
    """Reset counters at midnight."""
    today = date.today().isoformat()
    if _daily_stats["date"] != today:
        logger.info(f"New day detected, resetting spending counters (was: {_daily_stats})")
        _daily_stats["date"] = today
        _daily_stats["domains_purchased"] = 0
        _daily_stats["spend_aud"] = 0.0


def get_daily_stats() -> dict:
    """Get current daily spending stats."""
    _reset_if_new_day()
    return {
        "date": _daily_stats["date"],
        "domains_purchased": _daily_stats["domains_purchased"],
        "spend_aud": _daily_stats["spend_aud"],
        "domains_remaining": MAX_DOMAINS_PER_DAY - _daily_stats["domains_purchased"],
        "spend_remaining_aud": MAX_SPEND_PER_DAY_AUD - _daily_stats["spend_aud"],
    }


def check_can_purchase(domain_count: int) -> bool:
    """
    Check if purchase is allowed within limits.
    
    Args:
        domain_count: Number of domains to purchase
        
    Returns:
        True if purchase is allowed
        
    Raises:
        SpendingLimitExceeded: If any limit would be exceeded
    """
    _reset_if_new_day()
    
    # Check per-call limit
    if domain_count > MAX_DOMAINS_PER_CALL:
        msg = (
            f"BLOCKED: Requested {domain_count} domains exceeds "
            f"per-call limit of {MAX_DOMAINS_PER_CALL}"
        )
        logger.error(msg)
        raise SpendingLimitExceeded(msg)
    
    # Check daily domain limit
    projected_domains = _daily_stats["domains_purchased"] + domain_count
    if projected_domains > MAX_DOMAINS_PER_DAY:
        msg = (
            f"BLOCKED: Would exceed daily limit of {MAX_DOMAINS_PER_DAY} domains "
            f"(today: {_daily_stats['domains_purchased']}, requested: {domain_count})"
        )
        logger.error(msg)
        raise SpendingLimitExceeded(msg)
    
    # Check daily spend limit
    projected_spend = domain_count * DOMAIN_COST_AUD
    if _daily_stats["spend_aud"] + projected_spend > MAX_SPEND_PER_DAY_AUD:
        msg = (
            f"BLOCKED: Would exceed daily spend limit of ${MAX_SPEND_PER_DAY_AUD} "
            f"(today: ${_daily_stats['spend_aud']:.2f}, requested: ${projected_spend})"
        )
        logger.error(msg)
        raise SpendingLimitExceeded(msg)
    
    logger.info(
        f"Spending check passed: {domain_count} domains, "
        f"${projected_spend} (daily total will be: "
        f"{projected_domains} domains, ${_daily_stats['spend_aud'] + projected_spend:.2f})"
    )
    return True


def record_purchase(domain_count: int, spend_aud: Optional[float] = None) -> None:
    """
    Record a successful purchase against daily limits.
    
    Args:
        domain_count: Number of domains purchased
        spend_aud: Actual spend (defaults to domain_count * DOMAIN_COST_AUD)
    """
    _reset_if_new_day()
    
    actual_spend = spend_aud if spend_aud is not None else (domain_count * DOMAIN_COST_AUD)
    
    _daily_stats["domains_purchased"] += domain_count
    _daily_stats["spend_aud"] += actual_spend
    
    logger.info(
        f"Recorded purchase: {domain_count} domains, ${actual_spend:.2f} "
        f"(daily totals: {_daily_stats['domains_purchased']} domains, "
        f"${_daily_stats['spend_aud']:.2f})"
    )


# ============================================
# APPROVAL QUEUE (Layer 3 - for large operations)
# ============================================

APPROVAL_THRESHOLD = 5  # Require approval for more than 5 domains

_pending_approvals: list[dict] = []


def requires_approval(domain_count: int) -> bool:
    """Check if operation requires manual approval."""
    return domain_count > APPROVAL_THRESHOLD


def queue_for_approval(
    domain_count: int,
    domains: list[str],
    persona_id: Optional[str] = None,
    reason: str = "buffer_replenishment",
) -> str:
    """
    Queue a large purchase for approval.
    
    Returns:
        Approval request ID
    """
    import uuid
    
    request_id = str(uuid.uuid4())[:8]
    
    _pending_approvals.append({
        "request_id": request_id,
        "domain_count": domain_count,
        "domains": domains[:10],  # First 10 for preview
        "persona_id": persona_id,
        "reason": reason,
        "created_at": date.today().isoformat(),
    })
    
    logger.warning(
        f"Large purchase queued for approval: {domain_count} domains "
        f"(request_id: {request_id})"
    )
    
    return request_id


def get_pending_approvals() -> list[dict]:
    """Get all pending approval requests."""
    return _pending_approvals.copy()


def approve_request(request_id: str) -> Optional[dict]:
    """Approve a pending request, return the request details."""
    for i, req in enumerate(_pending_approvals):
        if req["request_id"] == request_id:
            return _pending_approvals.pop(i)
    return None


def reject_request(request_id: str) -> bool:
    """Reject and remove a pending request."""
    for i, req in enumerate(_pending_approvals):
        if req["request_id"] == request_id:
            _pending_approvals.pop(i)
            logger.info(f"Rejected approval request: {request_id}")
            return True
    return False
