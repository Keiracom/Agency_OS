"""
Services module for Agency OS.

Services provide business logic that operates on models via the database.
Services sit at Layer 3 (same as engines) and can import from:
- models
- integrations

Services are consumed by:
- orchestration (flows)
- API routes

Phase 24A additions:
- LeadPoolService: CRUD for centralised lead pool
- LeadAllocatorService: Assign leads to clients
- JITValidator: Pre-send validation

Phase 24C additions:
- EmailEventsService: Email engagement event ingestion
- TimezoneService: Timezone lookup for leads

Phase 24D additions:
- ThreadService: Conversation thread management
- ReplyAnalyzer: AI-powered reply analysis
- ConversationAnalyticsService: Conversation analytics for CIS

Phase 24E additions:
- CRMPushService: Push meetings to client's CRM (HubSpot, Pipedrive, Close)

Phase 24F additions:
- CustomerImportService: Import customers from CRM/CSV for suppression
- SuppressionService: Check and manage suppression list
- BuyerSignalService: Query platform buyer signals for lead scoring

Phase 21 additions:
- SendLimiter: Daily send limits during TEST_MODE
"""
from src.services.buyer_signal_service import BuyerSignalService, BuyerSignal, BuyerScoreBoost
from src.services.conversation_analytics_service import ConversationAnalyticsService
from src.services.crm_push_service import CRMPushService, CRMPushResult, LeadData, MeetingData
from src.services.customer_import_service import CustomerImportService, ImportResult, ColumnMapping
from src.services.email_events_service import EmailEventsService
from src.services.jit_validator import JITValidator, JITValidationResult
from src.services.lead_allocator_service import LeadAllocatorService
from src.services.lead_pool_service import LeadPoolService
from src.services.reply_analyzer import ReplyAnalyzer
from src.services.send_limiter import SendLimiter, send_limiter
from src.services.suppression_service import SuppressionService, SuppressionResult
from src.services.thread_service import ThreadService
from src.services.timezone_service import TimezoneService
from src.services.resource_assignment_service import (
    assign_resources_to_client,
    release_client_resources,
    get_client_resources,
    get_client_resource_values,
    get_pool_stats,
    check_buffer_and_alert,
    add_resource_to_pool,
    retire_resource,
    start_warmup,
    complete_warmup,
    record_resource_usage,
)

__all__ = [
    "LeadPoolService",
    "LeadAllocatorService",
    "JITValidator",
    "JITValidationResult",
    "EmailEventsService",
    "TimezoneService",
    "ThreadService",
    "ReplyAnalyzer",
    "ConversationAnalyticsService",
    "CRMPushService",
    "CRMPushResult",
    "LeadData",
    "MeetingData",
    # Phase 24F
    "CustomerImportService",
    "ImportResult",
    "ColumnMapping",
    "SuppressionService",
    "SuppressionResult",
    "BuyerSignalService",
    "BuyerSignal",
    "BuyerScoreBoost",
    # Phase 21
    "SendLimiter",
    "send_limiter",
    # Resource Pool
    "assign_resources_to_client",
    "release_client_resources",
    "get_client_resources",
    "get_client_resource_values",
    "get_pool_stats",
    "check_buffer_and_alert",
    "add_resource_to_pool",
    "retire_resource",
    "start_warmup",
    "complete_warmup",
    "record_resource_usage",
]
