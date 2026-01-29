"""
FILE: src/integrations/youtube.py
PURPOSE: YouTube Data API v3 integration
PHASE: Marketing Automation
TASK: MKTG-004
DEPENDENCIES:
  - src/config/settings.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Async operations with proper error handling
"""

import logging
import os
import tempfile
from typing import Any

import httpx

from src.config.settings import settings
from src.exceptions import APIError, IntegrationError

logger = logging.getLogger(__name__)


class YouTubeClient:
    """
    YouTube Data API v3 client.

    Uploads videos and manages YouTube content.
    """

    BASE_URL = "https://www.googleapis.com/youtube/v3"
    UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"

    # Video categories
    CATEGORY_PEOPLE_BLOGS = "22"
    CATEGORY_SCIENCE_TECH = "28"
    CATEGORY_HOWTO_STYLE = "26"

    def __init__(
        self,
        api_key: str | None = None,
        access_token: str | None = None,
        refresh_token: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
    ):
        """
        Initialize YouTube client.

        For uploads, OAuth credentials are required.
        For read-only operations, API key is sufficient.

        Args:
            api_key: YouTube Data API key
            access_token: OAuth access token (for uploads)
            refresh_token: OAuth refresh token
            client_id: Google OAuth client ID
            client_secret: Google OAuth client secret
        """
        self.api_key = api_key or getattr(settings, "youtube_api_key", None)
        self.access_token = access_token or getattr(settings, "youtube_access_token", None)
        self.refresh_token = refresh_token or getattr(settings, "youtube_refresh_token", None)
        self.client_id = client_id or getattr(settings, "google_client_id", None)
        self.client_secret = client_secret or getattr(settings, "google_client_secret", None)

        if not self.api_key and not self.access_token:
            raise IntegrationError(
                service="youtube",
                message="YouTube API key or OAuth token is required",
            )

    async def _refresh_access_token(self) -> str:
        """
        Refresh the OAuth access token.

        Returns:
            New access token
        """
        if not all([self.refresh_token, self.client_id, self.client_secret]):
            raise IntegrationError(
                service="youtube",
                message="OAuth credentials required for token refresh",
            )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": self.refresh_token,
                    "grant_type": "refresh_token",
                },
            )

            if response.status_code != 200:
                raise APIError(
                    service="youtube",
                    status_code=response.status_code,
                    message=f"Token refresh failed: {response.text}",
                )

            data = response.json()
            self.access_token = data["access_token"]
            return self.access_token

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        json_data: dict | None = None,
        require_auth: bool = False,
    ) -> dict[str, Any]:
        """
        Make request to YouTube API.

        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            json_data: Request body
            require_auth: Whether OAuth is required

        Returns:
            Response JSON
        """
        params = params or {}

        if require_auth:
            if not self.access_token:
                raise IntegrationError(
                    service="youtube",
                    message="OAuth access token required for this operation",
                )
            headers = {"Authorization": f"Bearer {self.access_token}"}
        else:
            params["key"] = self.api_key
            headers = {}

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                url = f"{self.BASE_URL}/{endpoint}"

                if method.upper() == "GET":
                    response = await client.get(url, params=params, headers=headers)
                elif method.upper() == "POST":
                    response = await client.post(
                        url, params=params, json=json_data, headers=headers
                    )
                elif method.upper() == "PUT":
                    response = await client.put(url, params=params, json=json_data, headers=headers)
                elif method.upper() == "DELETE":
                    response = await client.delete(url, params=params, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                if response.status_code not in (200, 201, 204):
                    raise APIError(
                        service="youtube",
                        status_code=response.status_code,
                        message=f"YouTube API error: {response.text}",
                    )

                return response.json() if response.content else {}

        except httpx.HTTPError as e:
            raise APIError(
                service="youtube",
                status_code=500,
                message=f"YouTube request failed: {str(e)}",
            )

    async def upload_video(
        self,
        video_path: str | None = None,
        video_url: str | None = None,
        title: str = "Untitled",
        description: str = "",
        tags: list[str] | None = None,
        category_id: str = "22",
        privacy_status: str = "public",
        thumbnail_path: str | None = None,
    ) -> dict[str, Any]:
        """
        Upload a video to YouTube.

        Args:
            video_path: Path to local video file
            video_url: URL to download video from (if no local path)
            title: Video title (max 100 chars)
            description: Video description (max 5000 chars)
            tags: List of tags
            category_id: YouTube category ID
            privacy_status: public, private, or unlisted
            thumbnail_path: Path to thumbnail image

        Returns:
            Upload result with video id and url
        """
        if not self.access_token:
            raise IntegrationError(
                service="youtube",
                message="OAuth access token required for uploads",
            )

        # Download video from URL if needed
        temp_video_path = None
        if video_url and not video_path:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.get(video_url)
                if response.status_code != 200:
                    raise APIError(
                        service="youtube",
                        status_code=response.status_code,
                        message=f"Failed to download video: {video_url}",
                    )

                temp_video_path = tempfile.mktemp(suffix=".mp4")
                with open(temp_video_path, "wb") as f:
                    f.write(response.content)
                video_path = temp_video_path

        if not video_path or not os.path.exists(video_path):
            raise IntegrationError(
                service="youtube",
                message="Video file path is required",
            )

        try:
            # Prepare video metadata
            video_metadata = {
                "snippet": {
                    "title": title[:100],  # Max 100 chars
                    "description": description[:5000],  # Max 5000 chars
                    "tags": tags or [],
                    "categoryId": category_id,
                },
                "status": {
                    "privacyStatus": privacy_status,
                    "selfDeclaredMadeForKids": False,
                },
            }

            # Upload video using resumable upload
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Type": "video/*",
            }

            async with httpx.AsyncClient(timeout=600.0) as client:
                # Step 1: Initialize upload
                init_response = await client.post(
                    self.UPLOAD_URL,
                    params={"uploadType": "resumable", "part": "snippet,status"},
                    json=video_metadata,
                    headers=headers,
                )

                if init_response.status_code != 200:
                    raise APIError(
                        service="youtube",
                        status_code=init_response.status_code,
                        message=f"Upload init failed: {init_response.text}",
                    )

                upload_url = init_response.headers.get("Location")
                if not upload_url:
                    raise APIError(
                        service="youtube",
                        status_code=500,
                        message="No upload URL in response",
                    )

                # Step 2: Upload video content
                with open(video_path, "rb") as video_file:
                    video_content = video_file.read()

                upload_response = await client.put(
                    upload_url,
                    content=video_content,
                    headers={"Content-Type": "video/*"},
                )

                if upload_response.status_code not in (200, 201):
                    raise APIError(
                        service="youtube",
                        status_code=upload_response.status_code,
                        message=f"Video upload failed: {upload_response.text}",
                    )

                video_data = upload_response.json()
                video_id = video_data.get("id")

                logger.info(f"YouTube video uploaded: {video_id}")

                # Step 3: Upload thumbnail if provided
                if thumbnail_path and os.path.exists(thumbnail_path):
                    await self._upload_thumbnail(video_id, thumbnail_path)

                return {
                    "video_id": video_id,
                    "url": f"https://youtube.com/watch?v={video_id}",
                    "title": video_data.get("snippet", {}).get("title"),
                    "status": video_data.get("status", {}).get("uploadStatus"),
                }

        finally:
            # Cleanup temp file
            if temp_video_path and os.path.exists(temp_video_path):
                os.remove(temp_video_path)

    async def _upload_thumbnail(self, video_id: str, thumbnail_path: str) -> None:
        """
        Upload a custom thumbnail for a video.

        Args:
            video_id: YouTube video ID
            thumbnail_path: Path to thumbnail image
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(thumbnail_path, "rb") as thumb_file:
                response = await client.post(
                    f"{self.BASE_URL}/thumbnails/set",
                    params={"videoId": video_id},
                    content=thumb_file.read(),
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "image/jpeg",
                    },
                )

                if response.status_code not in (200, 201):
                    logger.warning(f"Thumbnail upload failed: {response.text}")

    async def get_channel_info(self) -> dict[str, Any]:
        """
        Get authenticated user's channel info.

        Returns:
            Channel data dict
        """
        result = await self._request(
            "GET",
            "channels",
            params={"part": "snippet,statistics", "mine": "true"},
            require_auth=True,
        )
        items = result.get("items", [])
        return items[0] if items else {}

    async def get_video_info(self, video_id: str) -> dict[str, Any]:
        """
        Get video information.

        Args:
            video_id: YouTube video ID

        Returns:
            Video data dict
        """
        result = await self._request(
            "GET",
            "videos",
            params={"part": "snippet,statistics,status", "id": video_id},
        )
        items = result.get("items", [])
        return items[0] if items else {}

    async def update_video(
        self,
        video_id: str,
        title: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Update video metadata.

        Args:
            video_id: YouTube video ID
            title: New title
            description: New description
            tags: New tags

        Returns:
            Updated video data
        """
        # First get current video data
        current = await self.get_video_info(video_id)
        if not current:
            raise APIError(
                service="youtube",
                status_code=404,
                message=f"Video not found: {video_id}",
            )

        snippet = current.get("snippet", {})

        # Update fields
        if title:
            snippet["title"] = title[:100]
        if description:
            snippet["description"] = description[:5000]
        if tags is not None:
            snippet["tags"] = tags

        result = await self._request(
            "PUT",
            "videos",
            params={"part": "snippet"},
            json_data={"id": video_id, "snippet": snippet},
            require_auth=True,
        )

        logger.info(f"YouTube video updated: {video_id}")
        return result

    async def delete_video(self, video_id: str) -> bool:
        """
        Delete a video.

        Args:
            video_id: YouTube video ID

        Returns:
            True if deleted successfully
        """
        await self._request(
            "DELETE",
            "videos",
            params={"id": video_id},
            require_auth=True,
        )
        logger.info(f"YouTube video deleted: {video_id}")
        return True


# Singleton instance
_youtube_client: YouTubeClient | None = None


def get_youtube_client() -> YouTubeClient:
    """Get or create YouTube client instance."""
    global _youtube_client
    if _youtube_client is None:
        _youtube_client = YouTubeClient()
    return _youtube_client


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Video upload (resumable)
# [x] Thumbnail upload
# [x] Video metadata update
# [x] Video deletion
# [x] Channel info retrieval
# [x] OAuth token refresh
# [x] Error handling with custom exceptions
# [x] Async operations
# [x] Logging
# [x] All functions have type hints
# [x] All functions have docstrings
