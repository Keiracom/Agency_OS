"""
Contract: src/engines/proxy_waterfall.py
Purpose: Proxy Waterfall for cost-optimized web scraping
Layer: 3 - engines
Imports: models, integrations
Consumers: orchestration only

FILE: src/engines/proxy_waterfall.py
PURPOSE: Datacenter → ISP → Residential proxy escalation
PHASE: FIXED_COST_OPTIMIZATION_PHASE_1
TASK: ~60% scraping cost reduction via intelligent proxy tiering
DEPENDENCIES:
  - src/engines/base.py
  - src/integrations/webshare.py (existing)
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Cost tracking in $AUD only

GOVERNANCE EVENT: FIXED_COST_OPTIMIZATION_PHASE_1
DESCRIPTION: Proxy waterfall saves ~$11 AUD/month at Ignition tier (1,250 leads)
"""

import asyncio
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

import httpx

from src.engines.base import BaseEngine, EngineResult

logger = logging.getLogger(__name__)


# ============================================
# CONSTANTS & CONFIGURATION
# ============================================

class ProxyTier(str, Enum):
    """Proxy tier levels."""
    DATACENTER = "datacenter"
    ISP = "isp"
    RESIDENTIAL = "residential"


# Cost per request in AUD
PROXY_COSTS_AUD = {
    ProxyTier.DATACENTER: Decimal("0.001"),
    ProxyTier.ISP: Decimal("0.008"),
    ProxyTier.RESIDENTIAL: Decimal("0.015"),
}

# Expected success rates by target
SUCCESS_RATES = {
    "google_maps": {
        ProxyTier.DATACENTER: 0.40,
        ProxyTier.ISP: 0.75,
        ProxyTier.RESIDENTIAL: 0.95,
    },
    "linkedin": {
        ProxyTier.DATACENTER: 0.10,
        ProxyTier.ISP: 0.50,
        ProxyTier.RESIDENTIAL: 0.85,
    },
    "default": {
        ProxyTier.DATACENTER: 0.60,
        ProxyTier.ISP: 0.80,
        ProxyTier.RESIDENTIAL: 0.95,
    },
}

# HTTP status codes that trigger escalation
ESCALATION_CODES = {403, 429, 503, 520, 521, 522, 523, 524}

# Retry configuration
MAX_RETRIES_PER_TIER = 2
REQUEST_TIMEOUT = 30.0


# ============================================
# DATA CLASSES
# ============================================

@dataclass
class ProxyPool:
    """Pool of proxies for a specific tier."""
    tier: ProxyTier
    proxies: list[str] = field(default_factory=list)
    failures: dict[str, int] = field(default_factory=dict)
    
    def get_proxy(self) -> Optional[str]:
        """Get a random proxy, avoiding recent failures."""
        available = [p for p in self.proxies if self.failures.get(p, 0) < 3]
        if not available:
            # Reset failures if all proxies exhausted
            self.failures.clear()
            available = self.proxies
        return random.choice(available) if available else None
    
    def mark_failure(self, proxy: str) -> None:
        """Mark a proxy as failed."""
        self.failures[proxy] = self.failures.get(proxy, 0) + 1
    
    def mark_success(self, proxy: str) -> None:
        """Reset failure count on success."""
        self.failures[proxy] = 0


@dataclass
class WaterfallResult:
    """Result from a waterfall request."""
    success: bool
    status_code: Optional[int] = None
    content: Optional[bytes] = None
    text: Optional[str] = None
    
    # Cost tracking
    tier_used: Optional[ProxyTier] = None
    cost_aud: Decimal = Decimal("0.00")
    
    # Escalation tracking
    tiers_attempted: list[str] = field(default_factory=list)
    total_attempts: int = 0
    
    # Timing
    latency_ms: Optional[int] = None
    
    # Error
    error: Optional[str] = None


# ============================================
# PROXY WATERFALL ENGINE
# ============================================

class ProxyWaterfallEngine(BaseEngine):
    """
    Intelligent proxy waterfall for cost-optimized scraping.
    
    Escalation order: Datacenter ($0.001) → ISP ($0.008) → Residential ($0.015)
    
    - Starts with cheapest proxy tier
    - Auto-escalates on 403/429/503 errors
    - Tracks costs per request
    - Graceful degradation, never fails the flow
    
    Cost Impact:
    - Current (Residential only): $0.015/request
    - With Waterfall: ~$0.006/request (weighted average)
    - Savings: ~60%
    """
    
    def __init__(
        self,
        datacenter_proxies: Optional[list[str]] = None,
        isp_proxies: Optional[list[str]] = None,
        residential_proxies: Optional[list[str]] = None,
    ):
        """
        Initialize with proxy lists.
        
        Args:
            datacenter_proxies: List of datacenter proxy URLs
            isp_proxies: List of ISP proxy URLs
            residential_proxies: List of residential proxy URLs
        """
        self._pools = {
            ProxyTier.DATACENTER: ProxyPool(ProxyTier.DATACENTER, datacenter_proxies or []),
            ProxyTier.ISP: ProxyPool(ProxyTier.ISP, isp_proxies or []),
            ProxyTier.RESIDENTIAL: ProxyPool(ProxyTier.RESIDENTIAL, residential_proxies or []),
        }
        
        self._tier_order = [
            ProxyTier.DATACENTER,
            ProxyTier.ISP,
            ProxyTier.RESIDENTIAL,
        ]
    
    @property
    def name(self) -> str:
        return "proxy_waterfall"
    
    async def fetch(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[dict] = None,
        target_type: str = "default",
        start_tier: Optional[ProxyTier] = None,
        timeout: float = REQUEST_TIMEOUT,
    ) -> EngineResult[WaterfallResult]:
        """
        Fetch URL with automatic proxy escalation.
        
        Args:
            url: URL to fetch
            method: HTTP method
            headers: Optional headers
            target_type: Target type for success rate estimation
            start_tier: Optional starting tier (default: datacenter)
            timeout: Request timeout in seconds
        
        Returns:
            EngineResult with WaterfallResult
        """
        result = WaterfallResult(success=False)
        total_cost = Decimal("0.00")
        start_time = datetime.utcnow()
        
        # Determine starting tier
        start_idx = 0
        if start_tier:
            try:
                start_idx = self._tier_order.index(start_tier)
            except ValueError:
                start_idx = 0
        
        # Waterfall through tiers
        for tier in self._tier_order[start_idx:]:
            pool = self._pools[tier]
            
            if not pool.proxies:
                logger.debug(f"No proxies configured for tier {tier.value}, skipping")
                continue
            
            result.tiers_attempted.append(tier.value)
            
            # Retry within tier
            for attempt in range(MAX_RETRIES_PER_TIER):
                result.total_attempts += 1
                proxy = pool.get_proxy()
                
                if not proxy:
                    logger.warning(f"No available proxies in tier {tier.value}")
                    break
                
                try:
                    async with httpx.AsyncClient(
                        proxy=proxy,
                        timeout=timeout,
                        follow_redirects=True,
                    ) as client:
                        response = await client.request(
                            method=method,
                            url=url,
                            headers=headers or self._default_headers(),
                        )
                    
                    # Track cost regardless of outcome
                    total_cost += PROXY_COSTS_AUD[tier]
                    
                    if response.status_code == 200:
                        # Success!
                        pool.mark_success(proxy)
                        
                        result.success = True
                        result.status_code = response.status_code
                        result.content = response.content
                        result.text = response.text
                        result.tier_used = tier
                        result.cost_aud = total_cost
                        result.latency_ms = int(
                            (datetime.utcnow() - start_time).total_seconds() * 1000
                        )
                        
                        logger.info(
                            f"Waterfall success: {url} via {tier.value} "
                            f"(cost: ${total_cost} AUD, attempts: {result.total_attempts})"
                        )
                        
                        return EngineResult.ok(
                            data=result,
                            metadata={
                                "tier": tier.value,
                                "cost_aud": str(total_cost),
                                "attempts": result.total_attempts,
                            },
                        )
                    
                    elif response.status_code in ESCALATION_CODES:
                        # Blocked, escalate to next tier
                        pool.mark_failure(proxy)
                        logger.info(
                            f"Blocked ({response.status_code}) on {tier.value}, "
                            f"escalating..."
                        )
                        break  # Exit retry loop, try next tier
                    
                    else:
                        # Other error, retry same tier
                        pool.mark_failure(proxy)
                        logger.warning(
                            f"Unexpected status {response.status_code} on {tier.value}"
                        )
                        
                except httpx.TimeoutException:
                    pool.mark_failure(proxy)
                    logger.warning(f"Timeout on {tier.value}, attempt {attempt + 1}")
                    
                except httpx.ProxyError as e:
                    pool.mark_failure(proxy)
                    logger.warning(f"Proxy error on {tier.value}: {e}")
                    
                except Exception as e:
                    pool.mark_failure(proxy)
                    logger.error(f"Unexpected error on {tier.value}: {e}")
        
        # All tiers exhausted
        result.cost_aud = total_cost
        result.error = "All proxy tiers exhausted"
        result.latency_ms = int(
            (datetime.utcnow() - start_time).total_seconds() * 1000
        )
        
        logger.error(
            f"Waterfall failed: {url} (cost: ${total_cost} AUD, "
            f"attempts: {result.total_attempts})"
        )
        
        return EngineResult.error(
            error="All proxy tiers exhausted",
            metadata={
                "tiers_attempted": result.tiers_attempted,
                "cost_aud": str(total_cost),
                "attempts": result.total_attempts,
            },
        )
    
    async def fetch_json(
        self,
        url: str,
        **kwargs,
    ) -> EngineResult[dict]:
        """Fetch and parse JSON response."""
        result = await self.fetch(url, **kwargs)
        
        if not result.success:
            return EngineResult.error(error=result.error)
        
        try:
            import json
            data = json.loads(result.data.text)
            return EngineResult.ok(
                data=data,
                metadata=result.metadata,
            )
        except json.JSONDecodeError as e:
            return EngineResult.error(error=f"JSON decode error: {e}")
    
    def _default_headers(self) -> dict:
        """Default headers for requests."""
        return {
            "User-Agent": self._random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-AU,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    
    def _random_user_agent(self) -> str:
        """Return a random modern user agent."""
        agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        ]
        return random.choice(agents)
    
    def get_cost_estimate(self, target_type: str = "default") -> dict:
        """
        Get cost estimate for a target type.
        
        Returns expected cost based on success rates.
        """
        rates = SUCCESS_RATES.get(target_type, SUCCESS_RATES["default"])
        
        # Calculate weighted cost
        # P(datacenter success) * cost_dc + P(dc fail) * P(isp success) * cost_isp + ...
        
        p_dc = rates[ProxyTier.DATACENTER]
        p_isp = rates[ProxyTier.ISP]
        p_res = rates[ProxyTier.RESIDENTIAL]
        
        cost_dc = PROXY_COSTS_AUD[ProxyTier.DATACENTER]
        cost_isp = PROXY_COSTS_AUD[ProxyTier.ISP]
        cost_res = PROXY_COSTS_AUD[ProxyTier.RESIDENTIAL]
        
        expected_cost = (
            p_dc * cost_dc +
            (1 - p_dc) * p_isp * (cost_dc + cost_isp) +
            (1 - p_dc) * (1 - p_isp) * p_res * (cost_dc + cost_isp + cost_res)
        )
        
        return {
            "target_type": target_type,
            "expected_cost_aud": float(expected_cost),
            "residential_only_cost_aud": float(cost_res),
            "savings_percent": round((1 - float(expected_cost) / float(cost_res)) * 100, 1),
        }


# ============================================
# FACTORY FUNCTION
# ============================================

def get_proxy_waterfall(
    datacenter_proxies: Optional[list[str]] = None,
    isp_proxies: Optional[list[str]] = None,
    residential_proxies: Optional[list[str]] = None,
) -> ProxyWaterfallEngine:
    """Get ProxyWaterfallEngine instance."""
    return ProxyWaterfallEngine(
        datacenter_proxies=datacenter_proxies,
        isp_proxies=isp_proxies,
        residential_proxies=residential_proxies,
    )


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Datacenter → ISP → Residential escalation
# [x] Auto-switch on 403/429/503
# [x] Cost tracking in AUD
# [x] Graceful degradation (never hard fails flow)
# [x] Retry logic per tier
# [x] Proxy failure tracking
# [x] User-agent rotation
# [x] Cost estimation method
