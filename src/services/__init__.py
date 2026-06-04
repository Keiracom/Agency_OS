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
- WhoRefinementService: Apply WHO conversion patterns to refine ICP search criteria

Phase 22 additions (Content QA):
- ContentQAService: Pre-send content quality validation (placeholders, length, spam)

Phase H additions (Client Transparency):
- DigestService: Daily digest email generation and delivery (Item 44)

Voice Retry additions:
- VoiceRetryService: Schedule voice call retries (busy=2hr, no_answer=next business day)

Phone Provisioning additions:
- PhoneProvisioningService: Automated phone number provisioning via Twilio
"""


# Note: CampaignConfigBuilder not exported here to avoid circular import with enrichment module
# Import directly: from src.services.campaign_config_builder import CampaignConfigBuilder

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
    # Voice Retry
    "VoiceRetryService",
    "get_voice_retry_service",
    "RETRY_DELAYS",
    "MAX_RETRIES",
    "RETRYABLE_OUTCOMES",
    # Email Signature
    "generate_signature_text",
    "generate_signature_html",
    "get_display_name",
    "get_signature_for_persona",
    "get_signature_for_client",
    "get_display_name_for_persona",
    "append_signature_to_body",
    # Phone Provisioning
    "PhoneProvisioningService",
    "get_phone_provisioning_service",
    "get_voice_daily_limit",
    "VOICE_WARMUP_SCHEDULE",
]

# [repo_split curation] dead-BDR submodule imports removed (24); kept only: ['sdk_usage_service']
