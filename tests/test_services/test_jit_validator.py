"""
FILE: tests/test_services/test_jit_validator.py
PURPOSE: Unit tests for JIT Validator Service
PHASE: 24A (Lead Pool Architecture)
TASK: POOL-015
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.services.jit_validator import JITValidator, JITValidationResult


@pytest.fixture
def mock_session():
    """Create mock async session."""
    session = AsyncMock()
    return session


@pytest.fixture
def jit_validator(mock_session):
    """Create JITValidator with mock session."""
    return JITValidator(mock_session)


@pytest.fixture
def valid_pool_lead():
    """Sample valid pool lead."""
    return {
        "id": uuid4(),
        "email": "valid@example.com",
        "email_status": "verified",
        "pool_status": "assigned",
        "is_bounced": False,
        "is_unsubscribed": False,
    }


@pytest.fixture
def valid_assignment():
    """Sample valid assignment."""
    return {
        "id": uuid4(),
        "status": "active",
        "total_touches": 3,
        "max_touches": 10,
        "cooling_until": None,
        "has_replied": False,
        "reply_intent": None,
        "last_contacted_at": datetime.now() - timedelta(days=5),
        "channels_used": ["email"],
    }


class TestJITValidationResult:
    """Tests for JITValidationResult dataclass."""

    def test_ok_result(self):
        """Test creating a passing result."""
        assignment_id = uuid4()
        pool_id = uuid4()

        result = JITValidationResult.ok(assignment_id, pool_id)

        assert result.is_valid is True
        assert result.assignment_id == assignment_id
        assert result.lead_pool_id == pool_id
        assert result.block_reason is None
        assert result.block_code is None

    def test_fail_result(self):
        """Test creating a failing result."""
        pool_id = uuid4()

        result = JITValidationResult.fail(
            reason="Email has bounced globally",
            code="bounced_globally",
            lead_pool_id=pool_id,
        )

        assert result.is_valid is False
        assert result.block_reason == "Email has bounced globally"
        assert result.block_code == "bounced_globally"
        assert result.lead_pool_id == pool_id


class TestJITValidatorPoolChecks:
    """Tests for pool-level validation checks."""

    @pytest.mark.asyncio
    async def test_validate_bounced_lead(self, jit_validator, mock_session):
        """Test validation fails for bounced lead."""
        pool_id = uuid4()
        client_id = uuid4()

        # Mock bounced pool lead
        pool_result = MagicMock()
        pool_result.fetchone.return_value = MagicMock(_mapping={
            "id": pool_id,
            "email": "bounced@example.com",
            "email_status": "invalid",
            "pool_status": "bounced",
            "is_bounced": True,
            "is_unsubscribed": False,
        })
        mock_session.execute.return_value = pool_result

        result = await jit_validator.validate(pool_id, client_id, "email")

        assert result.is_valid is False
        assert result.block_code == "bounced_globally"

    @pytest.mark.asyncio
    async def test_validate_unsubscribed_lead(self, jit_validator, mock_session):
        """Test validation fails for unsubscribed lead."""
        pool_id = uuid4()
        client_id = uuid4()

        # Mock unsubscribed pool lead
        pool_result = MagicMock()
        pool_result.fetchone.return_value = MagicMock(_mapping={
            "id": pool_id,
            "email": "unsub@example.com",
            "email_status": "verified",
            "pool_status": "unsubscribed",
            "is_bounced": False,
            "is_unsubscribed": True,
        })
        mock_session.execute.return_value = pool_result

        result = await jit_validator.validate(pool_id, client_id, "email")

        assert result.is_valid is False
        assert result.block_code == "unsubscribed_globally"

    @pytest.mark.asyncio
    async def test_validate_lead_not_found(self, jit_validator, mock_session):
        """Test validation fails when lead not in pool."""
        pool_id = uuid4()
        client_id = uuid4()

        # Mock empty result
        pool_result = MagicMock()
        pool_result.fetchone.return_value = None
        mock_session.execute.return_value = pool_result

        result = await jit_validator.validate(pool_id, client_id, "email")

        assert result.is_valid is False
        assert result.block_code == "lead_not_found"


class TestJITValidatorAssignmentChecks:
    """Tests for assignment-level validation checks."""

    @pytest.mark.asyncio
    async def test_validate_not_assigned(self, jit_validator, mock_session, valid_pool_lead):
        """Test validation fails when lead not assigned to client."""
        pool_id = uuid4()
        client_id = uuid4()

        # Mock valid pool lead
        pool_result = MagicMock()
        pool_result.fetchone.return_value = MagicMock(_mapping=valid_pool_lead)

        # Mock no assignment
        assign_result = MagicMock()
        assign_result.fetchone.return_value = None

        mock_session.execute.side_effect = [pool_result, assign_result]

        result = await jit_validator.validate(pool_id, client_id, "email")

        assert result.is_valid is False
        assert result.block_code == "not_assigned"

    @pytest.mark.asyncio
    async def test_validate_max_touches_reached(self, jit_validator, mock_session, valid_pool_lead):
        """Test validation fails when max touches reached."""
        pool_id = uuid4()
        client_id = uuid4()

        # Mock valid pool lead
        pool_result = MagicMock()
        pool_result.fetchone.return_value = MagicMock(_mapping=valid_pool_lead)

        # Mock assignment at max touches
        assign_result = MagicMock()
        assign_result.fetchone.return_value = MagicMock(_mapping={
            "id": uuid4(),
            "status": "active",
            "total_touches": 10,
            "max_touches": 10,
            "cooling_until": None,
            "has_replied": False,
            "reply_intent": None,
            "last_contacted_at": datetime.now() - timedelta(days=5),
            "channels_used": ["email"],
        })

        mock_session.execute.side_effect = [pool_result, assign_result]

        result = await jit_validator.validate(pool_id, client_id, "email")

        assert result.is_valid is False
        assert result.block_code == "max_touches_reached"

    @pytest.mark.asyncio
    async def test_validate_negative_reply(self, jit_validator, mock_session, valid_pool_lead):
        """Test validation fails for lead with negative reply intent."""
        pool_id = uuid4()
        client_id = uuid4()

        # Mock valid pool lead
        pool_result = MagicMock()
        pool_result.fetchone.return_value = MagicMock(_mapping=valid_pool_lead)

        # Mock assignment with negative reply
        assign_result = MagicMock()
        assign_result.fetchone.return_value = MagicMock(_mapping={
            "id": uuid4(),
            "status": "active",
            "total_touches": 3,
            "max_touches": 10,
            "cooling_until": None,
            "has_replied": True,
            "reply_intent": "not_interested",
            "last_contacted_at": datetime.now() - timedelta(days=5),
            "channels_used": ["email"],
        })

        mock_session.execute.side_effect = [pool_result, assign_result]

        result = await jit_validator.validate(pool_id, client_id, "email")

        assert result.is_valid is False
        assert "replied_not_interested" in result.block_code


class TestJITValidatorTimingChecks:
    """Tests for timing validation checks."""

    @pytest.mark.asyncio
    async def test_validate_in_cooling_period(self, jit_validator, mock_session, valid_pool_lead):
        """Test validation fails during cooling period."""
        pool_id = uuid4()
        client_id = uuid4()

        # Mock valid pool lead
        pool_result = MagicMock()
        pool_result.fetchone.return_value = MagicMock(_mapping=valid_pool_lead)

        # Mock assignment in cooling
        assign_result = MagicMock()
        assign_result.fetchone.return_value = MagicMock(_mapping={
            "id": uuid4(),
            "status": "active",
            "total_touches": 3,
            "max_touches": 10,
            "cooling_until": datetime.now() + timedelta(days=5),
            "has_replied": False,
            "reply_intent": None,
            "last_contacted_at": datetime.now() - timedelta(days=10),
            "channels_used": ["email"],
        })

        mock_session.execute.side_effect = [pool_result, assign_result]

        result = await jit_validator.validate(pool_id, client_id, "email")

        assert result.is_valid is False
        assert result.block_code == "cooling_period"

    @pytest.mark.asyncio
    async def test_validate_too_recent(self, jit_validator, mock_session, valid_pool_lead):
        """Test validation fails when contacted too recently."""
        pool_id = uuid4()
        client_id = uuid4()

        # Mock valid pool lead
        pool_result = MagicMock()
        pool_result.fetchone.return_value = MagicMock(_mapping=valid_pool_lead)

        # Mock assignment contacted yesterday
        assign_result = MagicMock()
        assign_result.fetchone.return_value = MagicMock(_mapping={
            "id": uuid4(),
            "status": "active",
            "total_touches": 3,
            "max_touches": 10,
            "cooling_until": None,
            "has_replied": False,
            "reply_intent": None,
            "last_contacted_at": datetime.now() - timedelta(days=1),  # Too recent
            "channels_used": ["email"],
        })

        mock_session.execute.side_effect = [pool_result, assign_result]

        result = await jit_validator.validate(pool_id, client_id, "email")

        assert result.is_valid is False
        assert result.block_code == "too_recent"


class TestJITValidatorSuccess:
    """Tests for successful validation."""

    @pytest.mark.asyncio
    async def test_validate_success(self, jit_validator, mock_session, valid_pool_lead, valid_assignment):
        """Test successful validation passes all checks."""
        pool_id = uuid4()
        client_id = uuid4()
        assignment_id = uuid4()

        # Mock valid pool lead
        pool_result = MagicMock()
        pool_result.fetchone.return_value = MagicMock(_mapping=valid_pool_lead)

        # Mock valid assignment
        valid_assignment["id"] = assignment_id
        assign_result = MagicMock()
        assign_result.fetchone.return_value = MagicMock(_mapping=valid_assignment)

        # Mock rate limit check (under limit)
        rate_result = MagicMock()
        rate_result.fetchone.return_value = MagicMock(count=10)

        # Mock warmup check (client active for 14+ days)
        warmup_result = MagicMock()
        warmup_result.fetchone.return_value = MagicMock(
            created_at=datetime.now() - timedelta(days=30)
        )

        mock_session.execute.side_effect = [pool_result, assign_result, rate_result, warmup_result]

        result = await jit_validator.validate(pool_id, client_id, "email")

        assert result.is_valid is True
        assert result.assignment_id == assignment_id


class TestJITValidatorByEmail:
    """Tests for email-based validation."""

    @pytest.mark.asyncio
    async def test_validate_by_email(self, jit_validator, mock_session, valid_pool_lead, valid_assignment):
        """Test validation by email address."""
        client_id = uuid4()
        email = "test@example.com"
        pool_id = uuid4()

        # Mock email lookup
        email_result = MagicMock()
        email_result.fetchone.return_value = MagicMock(id=pool_id)

        # Mock rest of validation (would be multiple calls)
        valid_pool_lead["id"] = pool_id
        pool_result = MagicMock()
        pool_result.fetchone.return_value = MagicMock(_mapping=valid_pool_lead)

        assign_result = MagicMock()
        assign_result.fetchone.return_value = MagicMock(_mapping=valid_assignment)

        rate_result = MagicMock()
        rate_result.fetchone.return_value = MagicMock(count=5)

        warmup_result = MagicMock()
        warmup_result.fetchone.return_value = MagicMock(
            created_at=datetime.now() - timedelta(days=30)
        )

        mock_session.execute.side_effect = [email_result, pool_result, assign_result, rate_result, warmup_result]

        result = await jit_validator.validate_by_email(email, client_id, "email")

        # First call should be email lookup
        assert mock_session.execute.call_count >= 1

    @pytest.mark.asyncio
    async def test_validate_by_email_not_found(self, jit_validator, mock_session):
        """Test validation fails when email not in pool."""
        client_id = uuid4()
        email = "nonexistent@example.com"

        # Mock email not found
        email_result = MagicMock()
        email_result.fetchone.return_value = None
        mock_session.execute.return_value = email_result

        result = await jit_validator.validate_by_email(email, client_id, "email")

        assert result.is_valid is False
        assert result.block_code == "lead_not_found"


class TestJITValidatorBatch:
    """Tests for batch validation."""

    @pytest.mark.asyncio
    async def test_batch_validate(self, jit_validator, mock_session, valid_pool_lead, valid_assignment):
        """Test batch validation of multiple leads."""
        client_id = uuid4()
        leads = [
            {"lead_pool_id": uuid4()},
            {"lead_pool_id": uuid4()},
            {"lead_pool_id": uuid4()},
        ]

        # Mock all validations passing
        pool_result = MagicMock()
        pool_result.fetchone.return_value = MagicMock(_mapping=valid_pool_lead)

        assign_result = MagicMock()
        assign_result.fetchone.return_value = MagicMock(_mapping=valid_assignment)

        rate_result = MagicMock()
        rate_result.fetchone.return_value = MagicMock(count=5)

        warmup_result = MagicMock()
        warmup_result.fetchone.return_value = MagicMock(
            created_at=datetime.now() - timedelta(days=30)
        )

        # Each lead needs 4 db calls
        mock_session.execute.side_effect = [
            pool_result, assign_result, rate_result, warmup_result,
            pool_result, assign_result, rate_result, warmup_result,
            pool_result, assign_result, rate_result, warmup_result,
        ]

        results = await jit_validator.batch_validate(leads, client_id, "email")

        assert len(results) == 3
        for lead_id, result in results.items():
            assert isinstance(result, JITValidationResult)
