"""
Contract: src/api/routes/tiers.py
Purpose: Expose tier configuration as API endpoint
Layer: API
"""
from fastapi import APIRouter
from src.config.tiers import TIER_CONFIG

router = APIRouter(prefix="/tiers", tags=["tiers"])


@router.get("")
async def list_tiers():
    """Return all active tier configurations."""
    return {
        "tiers": [
            {
                "name": cfg.name,
                "price_aud": cfg.price_aud,
                "founding_price_aud": cfg.founding_price_aud,
                "leads_per_month": cfg.leads_per_month,
                "max_campaigns": cfg.max_campaigns,
                "daily_outreach": cfg.daily_outreach,
            }
            for name, cfg in TIER_CONFIG.items()
        ]
    }
