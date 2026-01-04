"""
Tests for Vapi voice AI integration.

Tests the VapiClient class and VoiceEngine integration with Vapi.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.integrations.vapi import (
    VapiClient,
    VapiAssistantConfig,
    VapiCallRequest,
    VapiCallResult,
)
from src.exceptions import IntegrationError


# ============================================
# Fixtures
# ============================================


@pytest.fixture
def mock_vapi_client():
    """Create a mock Vapi client."""
    with patch.object(VapiClient, '__init__', lambda self, api_key=None: None):
        client = VapiClient()
        client.api_key = "test_vapi_key"
        client.headers = {
            "Authorization": "Bearer test_vapi_key",
            "Content-Type": "application/json"
        }
        return client


@pytest.fixture
def assistant_config():
    """Create a test assistant config."""
    return VapiAssistantConfig(
        name="Test Assistant",
        first_message="Hello! How can I help you today?",
        system_prompt="You are a helpful assistant.",
        voice_id="pNInz6obpgDQGcFmaJgB",
    )


@pytest.fixture
def call_request():
    """Create a test call request."""
    return VapiCallRequest(
        assistant_id="asst_123456",
        phone_number="+61412345678",
        customer_name="Test User",
        metadata={"lead_id": str(uuid4())},
    )


# ============================================
# VapiClient Tests
# ============================================


class TestVapiClient:
    """Tests for VapiClient."""

    @pytest.mark.asyncio
    async def test_create_assistant_success(self, mock_vapi_client, assistant_config):
        """Test successful assistant creation."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "asst_new_123"}

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await mock_vapi_client.create_assistant(assistant_config)

            assert result["id"] == "asst_new_123"

    @pytest.mark.asyncio
    async def test_create_assistant_failure(self, mock_vapi_client, assistant_config):
        """Test assistant creation failure."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(IntegrationError) as exc_info:
                await mock_vapi_client.create_assistant(assistant_config)

            assert "Vapi create_assistant failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_start_outbound_call_success(self, mock_vapi_client, call_request):
        """Test successful outbound call initiation."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "call_789",
            "status": "queued"
        }

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            with patch('src.integrations.vapi.settings') as mock_settings:
                mock_settings.vapi_phone_number_id = "phone_123"

                result = await mock_vapi_client.start_outbound_call(call_request)

                assert result["id"] == "call_789"
                assert result["status"] == "queued"

    @pytest.mark.asyncio
    async def test_start_outbound_call_failure(self, mock_vapi_client, call_request):
        """Test outbound call initiation failure."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid phone number"

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            with patch('src.integrations.vapi.settings') as mock_settings:
                mock_settings.vapi_phone_number_id = "phone_123"

                with pytest.raises(IntegrationError) as exc_info:
                    await mock_vapi_client.start_outbound_call(call_request)

                assert "Vapi start_outbound_call failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_call_success(self, mock_vapi_client):
        """Test successful call retrieval."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "call_789",
            "status": "ended",
            "duration": 120,
            "transcript": "Hello, this is a test call.",
            "recordingUrl": "https://example.com/recording.mp3",
            "cost": 0.25,
            "endedReason": "hangup",
        }

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await mock_vapi_client.get_call("call_789")

            assert isinstance(result, VapiCallResult)
            assert result.call_id == "call_789"
            assert result.status == "ended"
            assert result.duration_seconds == 120
            assert result.transcript == "Hello, this is a test call."
            assert result.cost == 0.25

    @pytest.mark.asyncio
    async def test_get_call_not_found(self, mock_vapi_client):
        """Test call retrieval for non-existent call."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Call not found"

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(IntegrationError) as exc_info:
                await mock_vapi_client.get_call("call_nonexistent")

            assert "Vapi get_call failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_calls_success(self, mock_vapi_client):
        """Test successful call listing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "call_1", "status": "ended"},
            {"id": "call_2", "status": "ended"},
        ]

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await mock_vapi_client.list_calls(limit=10)

            assert len(result) == 2
            assert result[0]["id"] == "call_1"

    @pytest.mark.asyncio
    async def test_end_call_success(self, mock_vapi_client):
        """Test successful call termination."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ended"}

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await mock_vapi_client.end_call("call_active")

            assert result["status"] == "ended"

    def test_parse_webhook_call_ended(self, mock_vapi_client):
        """Test parsing call-ended webhook payload."""
        payload = {
            "message": {
                "type": "call-ended",
                "call": {
                    "id": "call_123",
                    "status": "ended",
                    "duration": 60,
                    "transcript": "Test transcript",
                    "recordingUrl": "https://example.com/rec.mp3",
                    "endedReason": "hangup",
                    "cost": 0.15,
                    "metadata": {"lead_id": "lead_456"},
                }
            }
        }

        result = mock_vapi_client.parse_webhook(payload)

        assert result["call_id"] == "call_123"
        assert result["event"] == "call-ended"
        assert result["status"] == "ended"
        assert result["duration"] == 60
        assert result["transcript"] == "Test transcript"
        assert result["ended_reason"] == "hangup"
        assert result["metadata"]["lead_id"] == "lead_456"

    def test_parse_webhook_end_of_call_report(self, mock_vapi_client):
        """Test parsing end-of-call-report webhook payload."""
        payload = {
            "message": {
                "type": "end-of-call-report",
                "call": {
                    "id": "call_789",
                    "status": "ended",
                    "duration": 180,
                    "transcript": "Full conversation transcript...",
                    "endedReason": "customer-ended-call",
                    "cost": 0.45,
                    "metadata": {},
                }
            }
        }

        result = mock_vapi_client.parse_webhook(payload)

        assert result["call_id"] == "call_789"
        assert result["event"] == "end-of-call-report"
        assert result["duration"] == 180


# ============================================
# VapiAssistantConfig Tests
# ============================================


class TestVapiAssistantConfig:
    """Tests for VapiAssistantConfig model."""

    def test_default_values(self):
        """Test default configuration values."""
        config = VapiAssistantConfig(
            name="Test",
            first_message="Hello",
            system_prompt="Be helpful",
        )

        assert config.voice_id == "pNInz6obpgDQGcFmaJgB"
        assert config.model == "claude-sonnet-4-20250514"
        assert config.temperature == 0.7
        assert config.max_duration_seconds == 300
        assert config.language == "en-AU"

    def test_custom_values(self):
        """Test custom configuration values."""
        config = VapiAssistantConfig(
            name="Custom Assistant",
            first_message="G'day!",
            system_prompt="You are an Australian sales rep.",
            voice_id="custom_voice_id",
            model="claude-sonnet-4-20250514",
            temperature=0.5,
            max_duration_seconds=600,
            language="en-AU",
        )

        assert config.name == "Custom Assistant"
        assert config.voice_id == "custom_voice_id"
        assert config.temperature == 0.5
        assert config.max_duration_seconds == 600


# ============================================
# VapiCallRequest Tests
# ============================================


class TestVapiCallRequest:
    """Tests for VapiCallRequest model."""

    def test_valid_request(self):
        """Test valid call request."""
        request = VapiCallRequest(
            assistant_id="asst_123",
            phone_number="+61412345678",
            customer_name="John Smith",
        )

        assert request.assistant_id == "asst_123"
        assert request.phone_number == "+61412345678"
        assert request.customer_name == "John Smith"
        assert request.metadata == {}

    def test_request_with_metadata(self):
        """Test call request with metadata."""
        request = VapiCallRequest(
            assistant_id="asst_456",
            phone_number="+61400000000",
            customer_name="Jane Doe",
            metadata={
                "lead_id": "lead_789",
                "campaign_id": "campaign_abc",
            },
        )

        assert request.metadata["lead_id"] == "lead_789"
        assert request.metadata["campaign_id"] == "campaign_abc"


# ============================================
# VapiCallResult Tests
# ============================================


class TestVapiCallResult:
    """Tests for VapiCallResult model."""

    def test_minimal_result(self):
        """Test minimal call result."""
        result = VapiCallResult(
            call_id="call_123",
            status="ended",
        )

        assert result.call_id == "call_123"
        assert result.status == "ended"
        assert result.duration_seconds == 0
        assert result.transcript is None
        assert result.recording_url is None
        assert result.cost is None
        assert result.ended_reason is None

    def test_full_result(self):
        """Test full call result."""
        result = VapiCallResult(
            call_id="call_456",
            status="ended",
            duration_seconds=120.5,
            transcript="Hello, world!",
            recording_url="https://example.com/rec.mp3",
            cost=0.30,
            ended_reason="customer-hangup",
        )

        assert result.duration_seconds == 120.5
        assert result.transcript == "Hello, world!"
        assert result.recording_url == "https://example.com/rec.mp3"
        assert result.cost == 0.30
        assert result.ended_reason == "customer-hangup"
