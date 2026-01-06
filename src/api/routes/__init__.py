"""
FILE: src/api/routes/__init__.py
PURPOSE: API routes package - All FastAPI routers
PHASE: 7 (API Routes), modified Phase 16 for Conversion Intelligence
TASK: API-003 to API-008, 16F-002
DEPENDENCIES:
  - src/api/dependencies.py
  - src/engines/*
  - src/models/*
  - src/detectors/* (Phase 16)
RULES APPLIED:
  - Rule 12: LAYER 5 - Top layer, can import from everything below
  - Rule 14: Soft deletes only

This package contains all API routes for Agency OS:
- health: Health check and readiness endpoints
- campaigns: Campaign CRUD with soft delete
- leads: Lead CRUD with enrichment triggers
- webhooks: Inbound webhooks (Postmark, Twilio)
- webhooks_outbound: Outbound webhooks with HMAC signing
- reports: Campaign and client metrics
- patterns: Conversion Intelligence patterns (Phase 16)
"""

from src.api.routes.admin import router as admin_router
from src.api.routes.campaigns import router as campaigns_router
from src.api.routes.crm import router as crm_router
from src.api.routes.customers import router as customers_router
from src.api.routes.health import router as health_router
from src.api.routes.leads import router as leads_router
from src.api.routes.meetings import router as meetings_router
from src.api.routes.patterns import router as patterns_router
from src.api.routes.replies import router as replies_router
from src.api.routes.reports import router as reports_router
from src.api.routes.webhooks import router as webhooks_router
from src.api.routes.webhooks_outbound import router as webhooks_outbound_router
from src.api.routes.linkedin import router as linkedin_router
from src.api.routes.pool import router as pool_router

__all__ = [
    "health_router",
    "campaigns_router",
    "leads_router",
    "webhooks_router",
    "webhooks_outbound_router",
    "reports_router",
    "admin_router",
    "replies_router",
    "meetings_router",
    # Phase 16: Conversion Intelligence
    "patterns_router",
    # Phase 24E: CRM Push
    "crm_router",
    # Phase 24F: Customer Import
    "customers_router",
    # Phase 24H: LinkedIn Connection
    "linkedin_router",
    # Phase 24A: Lead Pool
    "pool_router",
]
