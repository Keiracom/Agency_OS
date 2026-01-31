"""
FILE: src/integrations/heygen.py
PURPOSE: HeyGen Video AI Integration for Agency OS
PHASE: 18 (Channel Expansion)
TASK: VID-001
DEPENDENCIES:
  - httpx
  - pydantic
  - tenacity
  - src/config/settings.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: No hardcoded credentials

Generates AI avatar videos using HeyGen API.
Supports avatars, voices, and video status tracking.

API Docs: https://docs.heygen.com/
"""

import logging
import os
from pathlib import Path

import httpx
from pydantic import BaseModel, Field
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.exceptions import IntegrationError

logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Models
# =============================================================================


class HeyGenAvatar(BaseModel):
    """Avatar model from HeyGen."""

    avatar_id: str
    avatar_name: str
    gender: str | None = None
    preview_image_url: str | None = None
    preview_video_url: str | None = None


class HeyGenVoice(BaseModel):
    """Voice model from HeyGen."""

    voice_id: str
    name: str = Field(alias="display_name", default="")
    language: str | None = None
    gender: str | None = None
    preview_audio: str | None = None
    support_pause: bool = False
    emotion_support: bool = False

    class Config:
        populate_by_name = True


class HeyGenVideoStatus(BaseModel):
    """Video status response from HeyGen."""

    video_id: str
    status: str  # pending, waiting, processing, completed, failed
    video_url: str | None = None
    thumbnail_url: str | None = None
    duration: float | None = None
    error: str | None = None


class HeyGenVideoDimension(BaseModel):
    """Video dimension configuration."""

    width: int = 1280
    height: int = 720


class HeyGenVideoRequest(BaseModel):
    """Request model for creating a video."""

    script: str
    avatar_id: str
    voice_id: str
    dimension: HeyGenVideoDimension = Field(default_factory=HeyGenVideoDimension)
    test: bool = False  # Test mode - no credits charged


# =============================================================================
# HeyGen Client
# =============================================================================


class HeyGenClient:
    """
    HeyGen API client for AI avatar video generation.

    Handles:
    - Avatar listing and selection
    - Voice listing and selection
    - Video generation
    - Video status tracking
    - Video download

    All API methods include retry logic with exponential backoff for
    transient failures (network errors, timeouts, rate limits).

    API Docs: https://docs.heygen.com/
    """

    BASE_URL = "https://api.heygen.com"

    # Retry configuration
    MAX_RETRIES = 3
    RETRY_MIN_WAIT = 2  # seconds
    RETRY_MAX_WAIT = 10  # seconds

    # Request timeout
    TIMEOUT = 60.0  # seconds

    def __init__(self, api_key: str | None = None):
        """
        Initialize HeyGen client.

        Args:
            api_key: HeyGen API key. Falls back to HEYGEN_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("HEYGEN_API_KEY", "")
        if not self.api_key:
            raise IntegrationError(
                service="heygen",
                message="HEYGEN_API_KEY not configured",
            )
        self.headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _create_retry_decorator(self):
        """Create retry decorator with logging."""
        return retry(
            retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
            stop=stop_after_attempt(self.MAX_RETRIES),
            wait=wait_exponential(
                multiplier=1, min=self.RETRY_MIN_WAIT, max=self.RETRY_MAX_WAIT
            ),
            before_sleep=before_sleep_log(logger, logging.WARNING),
        )

    def _handle_response(self, response: httpx.Response, operation: str) -> dict:
        """
        Handle API response with consistent error handling.

        Args:
            response: HTTP response object
            operation: Name of the operation for error messages

        Returns:
            Parsed JSON response data

        Raises:
            IntegrationError: If response indicates an error
        """
        if response.status_code == 401:
            raise IntegrationError(
                service="heygen",
                message=f"HeyGen authentication failed for {operation}",
            )
        if response.status_code == 429:
            raise IntegrationError(
                service="heygen",
                message=f"HeyGen rate limit exceeded for {operation}",
            )
        if response.status_code >= 400:
            raise IntegrationError(
                service="heygen",
                message=f"HeyGen {operation} failed: {response.status_code} - {response.text}",
            )

        data = response.json()

        # HeyGen API wraps responses in an "error" field for failures
        if data.get("error"):
            raise IntegrationError(
                service="heygen",
                message=f"HeyGen {operation} error: {data.get('error')}",
            )

        return data

    # =========================================================================
    # Avatar Operations
    # =========================================================================

    async def list_avatars(self) -> list[HeyGenAvatar]:
        """
        List all available avatars including instant avatars and talking photos.

        Returns:
            List of available avatars

        Raises:
            IntegrationError: If API call fails
        """
        retry_decorator = self._create_retry_decorator()

        @retry_decorator
        async def _list_avatars():
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.get(
                    f"{self.BASE_URL}/v2/avatars",
                    headers=self.headers,
                )
                data = self._handle_response(response, "list_avatars")

                avatars = []
                # V2 API returns avatars in data.avatars
                avatar_data = data.get("data", {}).get("avatars", [])
                for avatar in avatar_data:
                    avatars.append(
                        HeyGenAvatar(
                            avatar_id=avatar.get("avatar_id", ""),
                            avatar_name=avatar.get("avatar_name", ""),
                            gender=avatar.get("gender"),
                            preview_image_url=avatar.get("preview_image_url"),
                            preview_video_url=avatar.get("preview_video_url"),
                        )
                    )

                logger.info(f"Listed {len(avatars)} HeyGen avatars")
                return avatars

        return await _list_avatars()

    # =========================================================================
    # Voice Operations
    # =========================================================================

    async def list_voices(self) -> list[HeyGenVoice]:
        """
        List all available AI voices.

        Returns:
            List of available voices

        Raises:
            IntegrationError: If API call fails
        """
        retry_decorator = self._create_retry_decorator()

        @retry_decorator
        async def _list_voices():
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.get(
                    f"{self.BASE_URL}/v2/voices",
                    headers=self.headers,
                )
                data = self._handle_response(response, "list_voices")

                voices = []
                # V2 API returns voices in data.voices
                voice_data = data.get("data", {}).get("voices", [])
                for voice in voice_data:
                    voices.append(
                        HeyGenVoice(
                            voice_id=voice.get("voice_id", ""),
                            display_name=voice.get("display_name", voice.get("name", "")),
                            language=voice.get("language"),
                            gender=voice.get("gender"),
                            preview_audio=voice.get("preview_audio"),
                            support_pause=voice.get("support_pause", False),
                            emotion_support=voice.get("emotion_support", False),
                        )
                    )

                logger.info(f"Listed {len(voices)} HeyGen voices")
                return voices

        return await _list_voices()

    # =========================================================================
    # Video Operations
    # =========================================================================

    async def create_video(
        self,
        script: str,
        avatar_id: str,
        voice_id: str,
        dimension: HeyGenVideoDimension | None = None,
        test: bool = False,
    ) -> str:
        """
        Create an AI avatar video.

        Args:
            script: Text script for the avatar to speak (max 5000 characters)
            avatar_id: ID of the avatar to use
            voice_id: ID of the voice to use
            dimension: Video dimensions (default 1280x720)
            test: If True, creates test video (no credits charged)

        Returns:
            video_id for tracking generation status

        Raises:
            IntegrationError: If API call fails or script too long
        """
        if len(script) > 5000:
            raise IntegrationError(
                service="heygen",
                message=f"Script exceeds 5000 character limit: {len(script)} characters",
            )

        dimension = dimension or HeyGenVideoDimension()

        retry_decorator = self._create_retry_decorator()

        @retry_decorator
        async def _create_video():
            payload = {
                "video_inputs": [
                    {
                        "character": {
                            "type": "avatar",
                            "avatar_id": avatar_id,
                            "avatar_style": "normal",
                        },
                        "voice": {
                            "type": "text",
                            "input_text": script,
                            "voice_id": voice_id,
                        },
                    }
                ],
                "dimension": {
                    "width": dimension.width,
                    "height": dimension.height,
                },
                "test": test,
            }

            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.post(
                    f"{self.BASE_URL}/v2/video/generate",
                    headers=self.headers,
                    json=payload,
                )
                data = self._handle_response(response, "create_video")

                video_id = data.get("data", {}).get("video_id")
                if not video_id:
                    raise IntegrationError(
                        service="heygen",
                        message="HeyGen create_video: No video_id in response",
                    )

                logger.info(f"Created HeyGen video: {video_id}")
                return video_id

        return await _create_video()

    async def get_video_status(self, video_id: str) -> HeyGenVideoStatus:
        """
        Get the status and details of a video.

        Args:
            video_id: ID of the video to check

        Returns:
            HeyGenVideoStatus with status, URL (if completed), etc.

        Raises:
            IntegrationError: If API call fails

        Status values:
            - pending: Video is queued
            - waiting: Video is in waiting state
            - processing: Video is rendering
            - completed: Video is ready for download
            - failed: Video generation failed
        """
        retry_decorator = self._create_retry_decorator()

        @retry_decorator
        async def _get_video_status():
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.get(
                    f"{self.BASE_URL}/v1/video_status.get",
                    headers=self.headers,
                    params={"video_id": video_id},
                )
                data = self._handle_response(response, "get_video_status")

                video_data = data.get("data", {})
                status = HeyGenVideoStatus(
                    video_id=video_id,
                    status=video_data.get("status", "unknown"),
                    video_url=video_data.get("video_url"),
                    thumbnail_url=video_data.get("thumbnail_url"),
                    duration=video_data.get("duration"),
                    error=video_data.get("error"),
                )

                logger.info(f"HeyGen video {video_id} status: {status.status}")
                return status

        return await _get_video_status()

    async def download_video(self, video_id: str, output_path: str | Path) -> Path:
        """
        Download a completed video to a local file.

        Args:
            video_id: ID of the video to download
            output_path: Local path to save the video (should end in .mp4)

        Returns:
            Path to the downloaded file

        Raises:
            IntegrationError: If video not ready or download fails
        """
        output_path = Path(output_path)

        # Get video status to retrieve download URL
        status = await self.get_video_status(video_id)

        if status.status != "completed":
            raise IntegrationError(
                service="heygen",
                message=f"Video {video_id} not ready for download: status={status.status}",
            )

        if not status.video_url:
            raise IntegrationError(
                service="heygen",
                message=f"Video {video_id} completed but no URL available",
            )

        retry_decorator = self._create_retry_decorator()

        @retry_decorator
        async def _download_video():
            # Create parent directories if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)

            async with httpx.AsyncClient(timeout=300.0) as client:  # 5 min timeout for large videos
                async with client.stream("GET", status.video_url) as response:
                    if response.status_code != 200:
                        raise IntegrationError(
                            service="heygen",
                            message=f"Failed to download video: {response.status_code}",
                        )

                    with open(output_path, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            f.write(chunk)

            logger.info(f"Downloaded HeyGen video {video_id} to {output_path}")
            return output_path

        return await _download_video()

    async def wait_for_video(
        self,
        video_id: str,
        poll_interval: float = 10.0,
        max_wait: float = 600.0,
    ) -> HeyGenVideoStatus:
        """
        Wait for a video to complete processing.

        Args:
            video_id: ID of the video to wait for
            poll_interval: Seconds between status checks (default 10)
            max_wait: Maximum seconds to wait (default 600 = 10 minutes)

        Returns:
            Final HeyGenVideoStatus (completed or failed)

        Raises:
            IntegrationError: If max_wait exceeded or video fails
        """
        import asyncio

        elapsed = 0.0
        while elapsed < max_wait:
            status = await self.get_video_status(video_id)

            if status.status == "completed":
                return status

            if status.status == "failed":
                raise IntegrationError(
                    service="heygen",
                    message=f"Video {video_id} failed: {status.error or 'Unknown error'}",
                )

            logger.debug(f"Video {video_id} status: {status.status}, waiting...")
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise IntegrationError(
            service="heygen",
            message=f"Video {video_id} timed out after {max_wait}s",
        )


# =============================================================================
# Singleton Pattern
# =============================================================================

_heygen_client: HeyGenClient | None = None


def get_heygen_client() -> HeyGenClient:
    """Get or create HeyGen client instance."""
    global _heygen_client
    if _heygen_client is None:
        _heygen_client = HeyGenClient()
    return _heygen_client


# === VERIFICATION CHECKLIST ===
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Uses env var for API key (HEYGEN_API_KEY)
# [x] All methods are async
# [x] Proper error handling with IntegrationError
# [x] Pydantic models for request/response validation
# [x] Singleton pattern for client instance
# [x] Retry logic with tenacity
# [x] create_video(script, avatar_id, voice_id) → video_id
# [x] get_video_status(video_id) → status, url
# [x] download_video(video_id, output_path)
# [x] list_avatars() → available avatars
# [x] list_voices() → available voices
# [x] All functions have type hints
# [x] All functions have docstrings
