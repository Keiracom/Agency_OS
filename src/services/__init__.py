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

Phase D additions:
- Australian state-level timezone mapping
- 9-11 AM email send window functions
- DomainHealthService: Domain health monitoring (bounce/complaint rates)
- DomainCapacityService: Domain capacity with health-based reduction

Phase E additions:
- SequenceGeneratorService: Auto-generate default 5-step sequences

Phase 16 additions (Reply Handling):
- ResponseTimingService: Calculate response delays and schedule reply sending
"""
from src.services.buyer_signal_service import BuyerSignalService, BuyerSignal, BuyerScoreBoost
from src.services.domain_health_service import (
    DomainHealthService,
    DomainHealthResult,
    get_domain_health_service,
)
from src.services.domain_capacity_service import (
    DomainCapacityService,
    DomainCapacityResult,
    get_domain_capacity_service,
)
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
from src.services.timezone_service import (
    TimezoneService,
    AUSTRALIAN_STATE_TIMEZONES,
    detect_australian_timezone,
    get_optimal_send_time,
    get_timezone_service,
)
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
from src.services.sequence_generator_service import (
    SequenceGeneratorService,
    get_sequence_generator_service,
)
from src.services.response_timing_service import (
    ResponseTimingService,
    is_business_hours,
    calculate_response_delay,
    calculate_send_time,
    DEFAULT_TIMEZONE,
    BUSINESS_HOURS_DELAY_MIN,
    BUSINESS_HOURS_DELAY_MAX,
    OUTSIDE_HOURS_DELAY_MIN,
    OUTSIDE_HOURS_DELAY_MAX,
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
    # Phase D - Timezone
    "AUSTRALIAN_STATE_TIMEZONES",
    "detect_australian_timezone",
    "get_optimal_send_time",
    "get_timezone_service",
    # Phase D - Domain Health
    "DomainHealthService",
    "DomainHealthResult",
    "get_domain_health_service",
    "DomainCapacityService",
    "DomainCapacityResult",
    "get_domain_capacity_service",
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
    # Phase E - Sequence Generator
    "SequenceGeneratorService",
    "get_sequence_generator_service",
    # Phase 16 - Reply Handling
    "ResponseTimingService",
    "is_business_hours",
    "calculate_response_delay",
    "calculate_send_time",
    "DEFAULT_TIMEZONE",
    "BUSINESS_HOURS_DELAY_MIN",
    "BUSINESS_HOURS_DELAY_MAX",
    "OUTSIDE_HOURS_DELAY_MIN",
    "OUTSIDE_HOURS_DELAY_MAX",
]
