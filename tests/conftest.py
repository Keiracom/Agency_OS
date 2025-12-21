"""
FILE: tests/conftest.py
PURPOSE: Pytest configuration and shared fixtures for all tests
PHASE: 9 (Integration Testing)
TASK: TST-001
"""

import asyncio
import os
import uuid
from datetime import datetime, timedelta
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Set test environment before importing app modules
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test_db"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["SUPABASE_URL"] = "https://test.supabase.co"
os.environ["SUPABASE_KEY"] = "test-key"
os.environ["SUPABASE_SERVICE_KEY"] = "test-service-key"
os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"
os.environ["APOLLO_API_KEY"] = "test-apollo-key"
os.environ["RESEND_API_KEY"] = "test-resend-key"
os.environ["TWILIO_ACCOUNT_SID"] = "test-twilio-sid"
os.environ["TWILIO_AUTH_TOKEN"] = "test-twilio-token"
os.environ["HEYREACH_API_KEY"] = "test-heyreach-key"
os.environ["LOB_API_KEY"] = "test-lob-key"
os.environ["SYNTHFLOW_API_KEY"] = "test-synthflow-key"


# ============================================================================
# Event Loop Configuration
# ============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncMock, None]:
    """
    Mock database session for unit tests.
    For integration tests, use a real test database.
    """
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.delete = MagicMock()

    yield session


@pytest_asyncio.fixture
async def real_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Real database session for integration tests.
    Requires a running test database.
    """
    # Skip if no real database is configured
    db_url = os.environ.get("TEST_DATABASE_URL")
    if not db_url:
        pytest.skip("TEST_DATABASE_URL not configured")

    engine = create_async_engine(db_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session
        await session.rollback()

    await engine.dispose()


# ============================================================================
# Redis Fixtures
# ============================================================================

@pytest.fixture
def mock_redis() -> MagicMock:
    """Mock Redis client for testing."""
    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.setex = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    redis.ttl = AsyncMock(return_value=3600)
    redis.exists = AsyncMock(return_value=0)
    redis.pipeline = MagicMock()

    return redis


# ============================================================================
# API Client Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def api_client() -> AsyncGenerator[AsyncClient, None]:
    """
    HTTP client for API testing.
    Uses httpx AsyncClient with the FastAPI test client.
    """
    from src.api.main import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


# ============================================================================
# Authentication Fixtures
# ============================================================================

@pytest.fixture
def mock_user() -> dict:
    """Mock authenticated user."""
    return {
        "id": str(uuid.uuid4()),
        "email": "test@example.com",
        "full_name": "Test User",
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def mock_client() -> dict:
    """Mock client (tenant)."""
    return {
        "id": str(uuid.uuid4()),
        "name": "Test Agency",
        "tier": "velocity",
        "subscription_status": "active",
        "credits_remaining": 5000,
        "credits_reset_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        "default_permission_mode": "co_pilot",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "deleted_at": None,
    }


@pytest.fixture
def mock_membership(mock_user: dict, mock_client: dict) -> dict:
    """Mock membership linking user to client."""
    return {
        "id": str(uuid.uuid4()),
        "user_id": mock_user["id"],
        "client_id": mock_client["id"],
        "role": "admin",
        "accepted_at": datetime.utcnow().isoformat(),
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def auth_headers(mock_user: dict) -> dict:
    """Mock authentication headers."""
    return {
        "Authorization": f"Bearer test-token-{mock_user['id']}",
        "X-Client-ID": str(uuid.uuid4()),
    }


# ============================================================================
# Campaign Fixtures
# ============================================================================

@pytest.fixture
def mock_campaign(mock_client: dict) -> dict:
    """Mock campaign for testing."""
    return {
        "id": str(uuid.uuid4()),
        "client_id": mock_client["id"],
        "name": "Test Campaign Q1 2025",
        "description": "Tech startups in Australia",
        "status": "active",
        "permission_mode": "co_pilot",
        "daily_limit": 50,
        "allocation_email": 60,
        "allocation_sms": 20,
        "allocation_linkedin": 20,
        "allocation_voice": 0,
        "allocation_mail": 0,
        "sequence_steps": [],
        "target_settings": {
            "industries": ["Technology", "SaaS"],
            "titles": ["CEO", "CTO", "Founder"],
            "company_sizes": ["10-50", "51-200"],
            "locations": ["Sydney", "Melbourne"],
        },
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "deleted_at": None,
    }


# ============================================================================
# Lead Fixtures
# ============================================================================

@pytest.fixture
def mock_lead(mock_client: dict, mock_campaign: dict) -> dict:
    """Mock lead for testing."""
    return {
        "id": str(uuid.uuid4()),
        "client_id": mock_client["id"],
        "campaign_id": mock_campaign["id"],
        "email": "lead@techcompany.io",
        "first_name": "Jane",
        "last_name": "Smith",
        "title": "Chief Technology Officer",
        "company_name": "TechCompany",
        "company_domain": "techcompany.io",
        "phone": "+61412345678",
        "linkedin_url": "https://linkedin.com/in/janesmith",
        "status": "enriched",
        "als_score": 82,
        "als_tier": "warm",
        "als_data_quality": 90,
        "als_authority": 85,
        "als_company_fit": 80,
        "als_timing": 75,
        "als_risk": 80,
        "enrichment_data": {
            "industry": "Technology",
            "company_size": "51-200",
            "funding": "Series A",
            "location": "Sydney, Australia",
        },
        "sequence_step": 1,
        "last_contacted_at": None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "deleted_at": None,
    }


@pytest.fixture
def mock_lead_hot(mock_lead: dict) -> dict:
    """Mock hot lead (ALS 85+)."""
    lead = mock_lead.copy()
    lead["id"] = str(uuid.uuid4())
    lead["als_score"] = 92
    lead["als_tier"] = "hot"
    lead["als_data_quality"] = 95
    lead["als_authority"] = 95
    lead["als_company_fit"] = 90
    lead["als_timing"] = 88
    lead["als_risk"] = 92
    return lead


@pytest.fixture
def mock_lead_cold(mock_lead: dict) -> dict:
    """Mock cold lead (ALS 20-34)."""
    lead = mock_lead.copy()
    lead["id"] = str(uuid.uuid4())
    lead["als_score"] = 28
    lead["als_tier"] = "cold"
    lead["als_data_quality"] = 40
    lead["als_authority"] = 30
    lead["als_company_fit"] = 25
    lead["als_timing"] = 20
    lead["als_risk"] = 25
    return lead


# ============================================================================
# Activity Fixtures
# ============================================================================

@pytest.fixture
def mock_activity(mock_lead: dict) -> dict:
    """Mock activity for testing."""
    return {
        "id": str(uuid.uuid4()),
        "lead_id": mock_lead["id"],
        "channel": "email",
        "direction": "outbound",
        "action": "sent",
        "subject": "Quick question about TechCompany",
        "body": "Hi Jane, I noticed TechCompany is expanding...",
        "provider_message_id": f"msg_{uuid.uuid4().hex[:12]}",
        "metadata": {
            "template_id": "intro_email_v2",
            "personalization_score": 0.85,
        },
        "created_at": datetime.utcnow().isoformat(),
    }


# ============================================================================
# Integration Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_apollo_client() -> MagicMock:
    """Mock Apollo API client."""
    client = MagicMock()
    client.enrich_person = AsyncMock(return_value={
        "person": {
            "first_name": "Jane",
            "last_name": "Smith",
            "title": "CTO",
            "email": "jane@techcompany.io",
            "linkedin_url": "https://linkedin.com/in/janesmith",
        },
        "organization": {
            "name": "TechCompany",
            "website_url": "https://techcompany.io",
            "industry": "Technology",
            "estimated_num_employees": 75,
        },
    })
    client.enrich_company = AsyncMock(return_value={
        "organization": {
            "name": "TechCompany",
            "website_url": "https://techcompany.io",
            "industry": "Technology",
            "estimated_num_employees": 75,
            "founded_year": 2019,
        },
    })
    return client


@pytest.fixture
def mock_resend_client() -> MagicMock:
    """Mock Resend email client."""
    client = MagicMock()
    client.send = AsyncMock(return_value={
        "id": f"email_{uuid.uuid4().hex[:12]}",
        "from": "sender@agency.com",
        "to": ["recipient@example.com"],
        "created_at": datetime.utcnow().isoformat(),
    })
    return client


@pytest.fixture
def mock_twilio_client() -> MagicMock:
    """Mock Twilio SMS client."""
    client = MagicMock()
    message = MagicMock()
    message.sid = f"SM{uuid.uuid4().hex[:32]}"
    message.status = "queued"
    message.date_created = datetime.utcnow()
    client.messages.create = MagicMock(return_value=message)
    client.check_dncr = AsyncMock(return_value=False)  # Not on DNCR
    return client


@pytest.fixture
def mock_heyreach_client() -> MagicMock:
    """Mock HeyReach LinkedIn client."""
    client = MagicMock()
    client.send_connection_request = AsyncMock(return_value={
        "id": f"conn_{uuid.uuid4().hex[:12]}",
        "status": "pending",
    })
    client.send_message = AsyncMock(return_value={
        "id": f"msg_{uuid.uuid4().hex[:12]}",
        "status": "sent",
    })
    client.get_daily_usage = AsyncMock(return_value={"requests_today": 5, "limit": 17})
    return client


@pytest.fixture
def mock_anthropic_client() -> MagicMock:
    """Mock Anthropic AI client."""
    client = MagicMock()
    response = MagicMock()
    response.content = [MagicMock(text="Generated content here")]
    response.usage = MagicMock(input_tokens=100, output_tokens=50)
    client.messages.create = AsyncMock(return_value=response)
    client.check_daily_budget = AsyncMock(return_value=True)  # Under budget
    return client


# ============================================================================
# Rate Limiting Fixtures
# ============================================================================

@pytest.fixture
def mock_rate_limiter(mock_redis: MagicMock) -> MagicMock:
    """Mock rate limiter for testing."""
    limiter = MagicMock()
    limiter.check_rate_limit = AsyncMock(return_value=True)  # Within limits
    limiter.increment_counter = AsyncMock(return_value=1)
    limiter.get_remaining = AsyncMock(return_value=45)  # 45 remaining
    limiter.reset_time = AsyncMock(return_value=3600)  # 1 hour
    return limiter


# ============================================================================
# Engine Fixtures
# ============================================================================

@pytest.fixture
def mock_scout_engine() -> MagicMock:
    """Mock Scout engine for enrichment."""
    engine = MagicMock()
    engine.enrich = AsyncMock(return_value={
        "success": True,
        "data": {
            "first_name": "Jane",
            "last_name": "Smith",
            "title": "CTO",
            "company_name": "TechCompany",
            "industry": "Technology",
        },
        "source": "apollo",
        "cached": False,
    })
    return engine


@pytest.fixture
def mock_scorer_engine() -> MagicMock:
    """Mock Scorer engine for ALS calculation."""
    engine = MagicMock()
    engine.score = AsyncMock(return_value={
        "als_score": 82,
        "als_tier": "warm",
        "components": {
            "data_quality": 90,
            "authority": 85,
            "company_fit": 80,
            "timing": 75,
            "risk": 80,
        },
    })
    return engine


@pytest.fixture
def mock_allocator_engine() -> MagicMock:
    """Mock Allocator engine for channel selection."""
    engine = MagicMock()
    engine.allocate = AsyncMock(return_value={
        "channel": "email",
        "resource_id": "email_account_1",
        "within_limits": True,
    })
    return engine


@pytest.fixture
def mock_content_engine() -> MagicMock:
    """Mock Content engine for AI generation."""
    engine = MagicMock()
    engine.generate_email = AsyncMock(return_value={
        "subject": "Quick question about TechCompany",
        "body": "Hi Jane, I noticed TechCompany is expanding...",
        "personalization_score": 0.85,
    })
    engine.generate_sms = AsyncMock(return_value={
        "body": "Hi Jane, quick Q about TechCompany expansion. Worth 5 min chat?",
        "personalization_score": 0.80,
    })
    return engine


@pytest.fixture
def mock_closer_engine() -> MagicMock:
    """Mock Closer engine for intent classification."""
    engine = MagicMock()
    engine.classify_intent = AsyncMock(return_value={
        "intent": "interested",
        "confidence": 0.92,
        "suggested_action": "schedule_meeting",
    })
    return engine


# ============================================================================
# Webhook Fixtures
# ============================================================================

@pytest.fixture
def postmark_inbound_payload() -> dict:
    """Sample Postmark inbound webhook payload."""
    return {
        "MessageID": f"msg_{uuid.uuid4().hex[:12]}",
        "From": "lead@techcompany.io",
        "FromName": "Jane Smith",
        "To": "campaign@agency.com",
        "Subject": "Re: Quick question about TechCompany",
        "TextBody": "Thanks for reaching out! I'd love to learn more. Can we schedule a call?",
        "HtmlBody": "<p>Thanks for reaching out! I'd love to learn more. Can we schedule a call?</p>",
        "Date": datetime.utcnow().isoformat(),
        "OriginalRecipient": "campaign@agency.com",
        "Tag": "campaign_123",
    }


@pytest.fixture
def twilio_inbound_payload() -> dict:
    """Sample Twilio inbound SMS webhook payload."""
    return {
        "MessageSid": f"SM{uuid.uuid4().hex[:32]}",
        "From": "+61412345678",
        "To": "+61499999999",
        "Body": "Yes, interested! Can we chat tomorrow?",
        "NumMedia": "0",
    }


@pytest.fixture
def heyreach_inbound_payload() -> dict:
    """Sample HeyReach LinkedIn reply webhook payload."""
    return {
        "event_type": "message_received",
        "message_id": f"msg_{uuid.uuid4().hex[:12]}",
        "conversation_id": f"conv_{uuid.uuid4().hex[:12]}",
        "sender_linkedin_url": "https://linkedin.com/in/janesmith",
        "message_text": "Thanks for connecting! I'd be interested to learn more about your offering.",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ============================================================================
# Utility Functions
# ============================================================================

def generate_uuid() -> str:
    """Generate a random UUID string."""
    return str(uuid.uuid4())


def generate_email() -> str:
    """Generate a random email address."""
    return f"test_{uuid.uuid4().hex[:8]}@example.com"


def generate_phone() -> str:
    """Generate a random Australian phone number."""
    return f"+614{uuid.uuid4().int % 100000000:08d}"


# ============================================================================
# Verification Checklist
# ============================================================================
# [x] Contract comment at top
# [x] No hardcoded credentials (test values only)
# [x] Session fixtures for unit and integration tests
# [x] All integration client mocks (Apollo, Resend, Twilio, etc.)
# [x] All engine mocks (Scout, Scorer, Allocator, etc.)
# [x] Webhook payload fixtures (Postmark, Twilio, HeyReach)
# [x] Authentication fixtures (user, client, membership)
# [x] Lead fixtures with ALS tiers (hot, warm, cold)
# [x] Rate limiting fixtures
# [x] Utility functions for test data generation
