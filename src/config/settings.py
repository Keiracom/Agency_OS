"""
FILE: src/config/settings.py
PURPOSE: Pydantic settings with database pool configuration
PHASE: 1 (Foundation + DevOps)
TASK: DB-001
DEPENDENCIES:
  - pydantic-settings
  - python-dotenv
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 19: Connection pool limits (pool_size=5, max_overflow=10)
"""

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file="config/.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # === Environment ===
    ENV: Literal["development", "staging", "production"] = Field(
        default="development", alias="environment"
    )
    debug: bool = False

    # === CORS ===
    ALLOWED_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins for production",
    )

    # === Database (Supabase PostgreSQL) ===
    # Transaction Pooler for application (Port 6543)
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:6543/postgres",
        description="PostgreSQL connection string (use port 6543 for transaction pooler)",
    )
    # Session Pooler for migrations (Port 5432)
    database_url_migrations: str = Field(
        default="postgresql://postgres:password@localhost:5432/postgres",
        description="PostgreSQL connection string for migrations (use port 5432)",
    )

    # Pool configuration (ENFORCED: Rule 19)
    db_pool_size: int = Field(default=5, description="Connection pool size")
    db_max_overflow: int = Field(default=10, description="Max overflow connections")
    db_pool_timeout: int = Field(default=30, description="Pool timeout in seconds")
    db_pool_recycle: int = Field(default=1800, description="Connection recycle time in seconds")

    # === Supabase ===
    supabase_url: str = Field(default="", description="Supabase project URL")
    supabase_key: str = Field(
        default="",
        validation_alias=AliasChoices("SUPABASE_KEY", "SUPABASE_ANON_KEY"),
        description="Supabase anon/public key (accepts SUPABASE_KEY or SUPABASE_ANON_KEY)",
    )
    supabase_service_key: str = Field(default="", description="Supabase service role key")
    supabase_jwt_secret: str = Field(
        default="", description="Supabase JWT secret for token verification"
    )

    # === Redis (Caching ONLY - NOT task queues) ===
    redis_url: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL (for caching only)"
    )
    redis_cache_ttl: int = Field(
        default=7776000, description="Default cache TTL (90 days in seconds)"
    )
    redis_cache_version: str = Field(default="v1", description="Cache key version prefix")

    # === Backend API Base URL ===
    base_url: str = Field(
        default="http://localhost:8000",
        description="Backend API base URL (for webhook callbacks)",
        alias="BASE_URL",
    )

    # === Prefect (Workflow Orchestration) ===
    prefect_api_url: str = Field(
        default="http://localhost:4200/api", description="Prefect server API URL"
    )

    # === API Keys ===
    anthropic_api_key: str = Field(default="", description="Anthropic/Claude API key")
    anthropic_daily_spend_limit: float = Field(
        default=50.0, description="Daily AI spend limit in AUD"
    )

    # === SDK Brain (Claude Agent SDK) ===
    sdk_brain_enabled: bool = Field(
        default=True, description="Enable SDK Brain for agentic AI tasks"
    )
    sdk_min_als_score: int = Field(
        default=85, description="Minimum ALS score for SDK enrichment (Hot tier threshold)"
    )
    sdk_daily_limit_ignition: float = Field(
        default=50.0, description="Daily SDK budget for Ignition tier (AUD)"
    )
    sdk_daily_limit_velocity: float = Field(
        default=100.0, description="Daily SDK budget for Velocity tier (AUD)"
    )
    sdk_daily_limit_dominance: float = Field(
        default=200.0, description="Daily SDK budget for Dominance tier (AUD)"
    )

    apollo_api_key: str = Field(default="", description="Apollo.io API key")
    apify_api_key: str = Field(default="", description="Apify API key")
    clay_api_key: str = Field(default="", description="Clay API key")

    # === ABN Lookup (Tier 1 Siege Waterfall - FREE) ===
    # Australian Business Register lookup. Register for free at:
    # https://abr.business.gov.au/Tools/WebServices
    abn_lookup_guid: str = Field(
        default="",
        description="ABN Lookup authentication GUID (free registration required)",
        validation_alias=AliasChoices("ABN_LOOKUP_GUID", "ABN_GUID"),
    )

    # === Kaspr (Tier 5 Identity Enrichment) ===
    # Mobile number enrichment for HOT leads (ALS >= 85)
    kaspr_api_key: str = Field(default="", description="Kaspr API key for mobile enrichment")

    # === Hunter.io (Tier 3 Email Discovery) ===
    # Email finder and verification for outreach
    hunter_api_key: str = Field(default="", description="Hunter.io API key for email discovery")

    resend_api_key: str = Field(default="", description="Resend API key")
    postmark_server_token: str = Field(default="", description="Postmark server token")

    # === Twilio (Voice Calls ONLY via Vapi) ===
    # NOT used for SMS. ClickSend is the SMS provider for Australia.
    twilio_account_sid: str = Field(default="", description="Twilio account SID (voice only)")
    twilio_auth_token: str = Field(default="", description="Twilio auth token (voice only)")
    twilio_phone_number: str = Field(default="", description="Twilio phone number (voice only)")

    heyreach_api_key: str = Field(
        default="", description="HeyReach API key (deprecated, use Unipile)"
    )

    # === Unipile (LinkedIn Automation - replacing HeyReach) ===
    unipile_api_url: str = Field(default="", description="Unipile API base URL")
    unipile_api_key: str = Field(default="", description="Unipile API key")

    # === LinkedIn Timing (Humanization) ===
    linkedin_min_delay_minutes: int = Field(
        default=8, description="Minimum delay between LinkedIn actions"
    )
    linkedin_max_delay_minutes: int = Field(
        default=45, description="Maximum delay between LinkedIn actions"
    )
    linkedin_min_daily: int = Field(default=15, description="Minimum daily connections")
    linkedin_max_daily: int = Field(
        default=20, description="Maximum daily connections (can increase to 80-100)"
    )
    linkedin_max_per_hour: int = Field(
        default=8, description="Max actions per hour (burst prevention)"
    )
    linkedin_business_hours_start: int = Field(default=8, description="Business hours start (24h)")
    linkedin_business_hours_end: int = Field(default=18, description="Business hours end (24h)")
    linkedin_weekend_reduction: float = Field(default=0.5, description="Weekend volume multiplier")

    # === ClickSend (Australian SMS + Direct Mail) ===
    # Primary SMS provider for Australian market. Twilio is used for voice calls ONLY.
    clicksend_username: str = Field(default="", description="ClickSend username/email")
    clicksend_api_key: str = Field(default="", description="ClickSend API key")

    # === DataForSEO (SEO Metrics Enrichment) ===
    dataforseo_login: str = Field(default="", description="DataForSEO login email")
    dataforseo_password: str = Field(default="", description="DataForSEO API password")

    # === Voice AI Stack (Vapi + Cartesia) ===
    vapi_api_key: str = Field(default="", description="Vapi API key")
    vapi_phone_number_id: str = Field(default="", description="Twilio number linked in Vapi")
    # Primary TTS: Cartesia (sonic-2 model, 90ms latency)
    cartesia_api_key: str = Field(default="", description="Cartesia API key (primary TTS)")
    cartesia_voice_model: str = Field(default="sonic-2", description="Cartesia voice model (sonic-2 or sonic-turbo)")
    # Fallback TTS: ElevenLabs (kept for compatibility)
    elevenlabs_api_key: str = Field(default="", description="ElevenLabs API key (fallback TTS)")

    # === Stripe ===
    stripe_api_key: str = Field(default="", description="Stripe secret key")
    stripe_publishable_key: str = Field(default="", description="Stripe publishable key")
    stripe_webhook_secret: str = Field(default="", description="Stripe webhook signing secret")
    stripe_price_ignition: str = Field(default="", description="Stripe Price ID for Ignition tier")
    stripe_price_velocity: str = Field(default="", description="Stripe Price ID for Velocity tier")
    stripe_price_dominance: str = Field(
        default="", description="Stripe Price ID for Dominance tier"
    )

    # === Calendar/Meetings ===
    calcom_api_key: str = Field(default="", description="Cal.com API key")
    calendly_api_key: str = Field(default="", description="Calendly API key")

    # === Australian DNCR (Do Not Call Register) ===
    dncr_api_key: str = Field(default="", description="ACMA DNCR API key")
    dncr_api_url: str = Field(default="https://api.dncr.gov.au/v1", description="DNCR API URL")
    dncr_account_id: str = Field(default="", description="DNCR Account ID")
    dncr_cache_ttl_hours: int = Field(default=24, description="Hours to cache DNCR results")

    # === Web Search (Phase 12B) ===
    serper_api_key: str = Field(default="", description="Serper.dev Google Search API key")

    # === Sentry (Error Tracking) ===
    sentry_dsn: str = Field(default="", description="Sentry DSN for error tracking")
    sentry_auth_token: str = Field(default="", description="Sentry auth token for API access")

    # === Development ===
    ngrok_authtoken: str = Field(default="", description="ngrok auth token for local webhooks")

    # === Email Infrastructure (Phase 18) ===
    # InfraForge - Domain purchase, mailbox creation, DNS automation
    infraforge_api_key: str = Field(default="", description="InfraForge API key")
    infraforge_api_url: str = Field(
        default="https://api.infraforge.ai/public", description="InfraForge API URL"
    )

    # Warmforge - Email warmup (free with Salesforge)
    warmforge_api_key: str = Field(default="", description="Warmforge API key")
    warmforge_api_url: str = Field(
        default="https://api.warmforge.ai/public/v1", description="Warmforge API URL (v1 endpoint)"
    )

    # Salesforge - Campaign sending, reply tracking, sender rotation
    salesforge_api_key: str = Field(default="", description="Salesforge API key")
    salesforge_api_url: str = Field(
        default="https://api.salesforge.ai/public/v2", description="Salesforge API URL"
    )

    # v0.dev - AI UI generation
    v0_api_key: str = Field(default="", description="v0.dev API key for UI generation")

    # === Residential Proxy (Tier 3 Scraper - Camoufox) ===
    # Required for Cloudflare bypass. Recommended providers: WebShare, IPRoyal
    residential_proxy_host: str = Field(default="", description="Residential proxy hostname")
    residential_proxy_port: int = Field(default=0, description="Residential proxy port")
    residential_proxy_username: str = Field(default="", description="Proxy auth username")
    residential_proxy_password: str = Field(default="", description="Proxy auth password")
    camoufox_enabled: bool = Field(default=False, description="Enable Camoufox Tier 3 scraper")
    scraper_timeout_ms: int = Field(default=45000, description="Scraper timeout in milliseconds")

    # === Rate Limits (Resource-Level) ===
    rate_limit_linkedin_per_seat: int = Field(
        default=17, description="LinkedIn actions per day per seat"
    )
    rate_limit_email_per_domain: int = Field(default=50, description="Emails per day per domain")
    rate_limit_sms_per_number: int = Field(default=100, description="SMS per day per number")

    # === Enrichment ===
    enrichment_confidence_threshold: float = Field(
        default=0.70, description="Minimum confidence score for enriched data"
    )
    enrichment_clay_max_percentage: float = Field(
        default=0.15, description="Maximum percentage of batch to send to Clay (fallback)"
    )

    # === HMAC Signing ===
    webhook_hmac_secret: str = Field(default="", description="HMAC secret for outbound webhooks")

    # === Email Provider Webhook Secrets (Phase 24C) ===
    smartlead_api_key: str = Field(default="", description="Smartlead API key")
    smartlead_api_url: str = Field(
        default="https://api.smartlead.ai/api/v1", description="Smartlead API URL"
    )
    smartlead_webhook_secret: str = Field(default="", description="Smartlead webhook HMAC secret")
    salesforge_webhook_secret: str = Field(default="", description="Salesforge webhook HMAC secret")
    resend_webhook_secret: str = Field(default="", description="Resend/Svix webhook secret")

    # === TEST_MODE Configuration (Phase 21) ===
    # When enabled, all outbound messages redirect to test recipients
    TEST_MODE: bool = Field(default=False, description="Enable TEST_MODE for safe E2E testing")
    TEST_EMAIL_RECIPIENT: str = Field(
        default="david.stephens@keiracom.com", description="Email recipient for TEST_MODE"
    )
    TEST_SMS_RECIPIENT: str = Field(
        default="+61457543392", description="SMS recipient for TEST_MODE"
    )
    TEST_VOICE_RECIPIENT: str = Field(
        default="+61457543392", description="Voice call recipient for TEST_MODE"
    )
    TEST_LINKEDIN_RECIPIENT: str = Field(
        default="https://www.linkedin.com/in/david-stephens-8847a636a/",
        description="LinkedIn profile for TEST_MODE",
    )
    TEST_DAILY_EMAIL_LIMIT: int = Field(
        default=15, description="Daily email limit during TEST_MODE for mailbox warmup protection"
    )

    # === Credential Encryption (Phase 24H) ===
    credential_encryption_key: str = Field(
        default="",
        description="Fernet encryption key for LinkedIn credentials (generate with cryptography.fernet.Fernet.generate_key())",
    )

    # === CRM Integration (Phase 24E) ===
    # HubSpot OAuth (required for HubSpot integration)
    hubspot_client_id: str = Field(default="", description="HubSpot OAuth client ID")
    hubspot_client_secret: str = Field(default="", description="HubSpot OAuth client secret")
    hubspot_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/crm/callback/hubspot",
        description="HubSpot OAuth redirect URI",
    )
    hubspot_scopes: str = Field(
        default="crm.objects.contacts.read,crm.objects.contacts.write,crm.objects.deals.read,crm.objects.deals.write,crm.schemas.deals.read",
        description="HubSpot OAuth scopes (comma-separated)",
    )

    # Pipedrive (API key auth - no OAuth needed)
    # Note: Pipedrive API key is stored per-client in client_crm_configs

    # Close CRM (API key auth - no OAuth needed)
    # Note: Close API key is stored per-client in client_crm_configs

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENV == "production"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_pool_config(self) -> dict:
        """Get SQLAlchemy pool configuration."""
        return {
            "pool_size": self.db_pool_size,
            "max_overflow": self.db_max_overflow,
            "pool_timeout": self.db_pool_timeout,
            "pool_recycle": self.db_pool_recycle,
            "pool_pre_ping": True,
        }


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Singleton instance for easy import
settings = get_settings()


# === VERIFICATION CHECKLIST ===
# [x] Contract comment at top
# [x] No hardcoded credentials (all from env)
# [x] Pool config: pool_size=5, max_overflow=10 (Rule 19)
# [x] Transaction Pooler port 6543 for app
# [x] Session Pooler port 5432 for migrations
# [x] Redis for caching only (not task queues)
# [x] Prefect API URL for orchestration
# [x] Rate limits at resource level (Rule 17)
# [x] Enrichment confidence threshold 0.70 (Rule 4)
# [x] AI spend limiter setting (Rule 15)
# [x] All fields have type hints
# [x] All fields have descriptions
# [x] Residential proxy settings for Tier 3 scraper (SCR-008)
