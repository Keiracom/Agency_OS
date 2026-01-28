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

Phase 19 additions (ICP Refinement from CIS):
- WhoRefinementService: Apply WHO conversion patterns to refine Apollo search criteria

Phase 22 additions (Content QA):
- ContentQAService: Pre-send content quality validation (placeholders, length, spam)

Phase H additions (Client Transparency):
- DigestService: Daily digest email generation and delivery (Item 44)

Voice Retry additions (TODO.md #3):
- VoiceRetryService: Schedule voice call retries (busy=2hr, no_answer=next business day)

Phone Provisioning additions (TODO.md #13):
- PhoneProvisioningService: Automated phone number provisioning via Twilio
"""

from src.services.buyer_signal_service import BuyerScoreBoost, BuyerSignal, BuyerSignalService
from src.services.content_qa_service import (
    ContentChannel,
    ContentQAService,
    QAIssue,
    QAResult,
    QAStatus,
    get_content_qa_service,
    validate_email_content,
    validate_linkedin_content,
    validate_sms_content,
    validate_voice_script,
)
from src.services.conversation_analytics_service import ConversationAnalyticsService
from src.services.crm_push_service import CRMPushResult, CRMPushService, LeadData, MeetingData
from src.services.customer_import_service import ColumnMapping, CustomerImportService, ImportResult
from src.services.digest_service import DigestService
from src.services.domain_capacity_service import (
    DomainCapacityResult,
    DomainCapacityService,
    get_domain_capacity_service,
)
from src.services.domain_health_service import (
    DomainHealthResult,
    DomainHealthService,
    get_domain_health_service,
)
from src.services.email_events_service import EmailEventsService
from src.services.email_signature_service import (
    append_signature_to_body,
    generate_signature_html,
    generate_signature_text,
    get_display_name,
    get_display_name_for_persona,
    get_signature_for_client,
    get_signature_for_persona,
)
from src.services.jit_validator import JITValidationResult, JITValidator
from src.services.lead_allocator_service import LeadAllocatorService
from src.services.lead_pool_service import LeadPoolService
from src.services.phone_provisioning_service import (
    VOICE_WARMUP_SCHEDULE,
    PhoneProvisioningService,
    get_phone_provisioning_service,
    get_voice_daily_limit,
)
from src.services.reply_analyzer import ReplyAnalyzer
from src.services.resource_assignment_service import (
    add_resource_to_pool,
    assign_resources_to_client,
    check_buffer_and_alert,
    complete_warmup,
    get_client_resource_values,
    get_client_resources,
    get_pool_stats,
    record_resource_usage,
    release_client_resources,
    retire_resource,
    start_warmup,
)
from src.services.response_timing_service import (
    BUSINESS_HOURS_DELAY_MAX,
    BUSINESS_HOURS_DELAY_MIN,
    DEFAULT_TIMEZONE,
    OUTSIDE_HOURS_DELAY_MAX,
    OUTSIDE_HOURS_DELAY_MIN,
    ResponseTimingService,
    calculate_response_delay,
    calculate_send_time,
    is_business_hours,
)
from src.services.send_limiter import SendLimiter, send_limiter
from src.services.sequence_generator_service import (
    SequenceGeneratorService,
    get_sequence_generator_service,
)
from src.services.suppression_service import SuppressionResult, SuppressionService
from src.services.thread_service import ThreadService
from src.services.timezone_service import (
    AUSTRALIAN_STATE_TIMEZONES,
    TimezoneService,
    detect_australian_timezone,
    get_optimal_send_time,
    get_timezone_service,
)
from src.services.voice_retry_service import (
    MAX_RETRIES,
    RETRY_DELAYS,
    RETRYABLE_OUTCOMES,
    VoiceRetryService,
    get_voice_retry_service,
)
from src.services.who_refinement_service import (
    MIN_CONFIDENCE_THRESHOLD,
    WhoRefinementService,
    get_who_refined_criteria,
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
    # Phase 19 - ICP Refinement from CIS
    "WhoRefinementService",
    "get_who_refined_criteria",
    "MIN_CONFIDENCE_THRESHOLD",
    # Phase 22 - Content QA
    "ContentQAService",
    "QAResult",
    "QAStatus",
    "QAIssue",
    "ContentChannel",
    "get_content_qa_service",
    "validate_email_content",
    "validate_sms_content",
    "validate_linkedin_content",
    "validate_voice_script",
    # Phase H - Daily Digest
    "DigestService",
    # Voice Retry (TODO.md #3)
    "VoiceRetryService",
    "get_voice_retry_service",
    "RETRY_DELAYS",
    "MAX_RETRIES",
    "RETRYABLE_OUTCOMES",
    # Email Signature (TODO.md #20)
    "generate_signature_text",
    "generate_signature_html",
    "get_display_name",
    "get_signature_for_persona",
    "get_signature_for_client",
    "get_display_name_for_persona",
    "append_signature_to_body",
    # Phone Provisioning (TODO.md #13)
    "PhoneProvisioningService",
    "get_phone_provisioning_service",
    "get_voice_daily_limit",
    "VOICE_WARMUP_SCHEDULE",
]
