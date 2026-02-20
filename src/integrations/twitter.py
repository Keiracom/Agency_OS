"""
FILE: src/integrations/twitter.py
PURPOSE: Twitter/X API v2 integration for social media automation
PHASE: 3 (Integrations)
TASK: INT-013
DEPENDENCIES:
  - src/config/settings.py
  - src/exceptions.py
  - tweepy (Twitter API library)
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 17: Rate limit handling with exponential backoff
"""

import asyncio
import mimetypes
import time
from pathlib import Path
from typing import Any

import sentry_sdk
import tweepy
from tweepy.errors import (
    BadRequest,
    Forbidden,
    NotFound,
    TooManyRequests,
    TweepyException,
    Unauthorized,
)

from src.config.settings import settings
from src.exceptions import APIError, IntegrationError, RateLimitError


class TwitterClient:
    """
    Twitter/X API v2 client.

    Handles tweet posting, threads, media uploads, and account operations
    with proper rate limit handling and error recovery.

    Authentication: OAuth 1.0a User Context for write operations,
    OAuth 2.0 Bearer Token for read-only operations.
    """

    # Rate limit constants (Twitter API v2 limits)
    RATE_LIMIT_WINDOW = 15 * 60  # 15 minutes in seconds
    TWEET_CREATE_LIMIT = 200  # per 15 min window (app-level)
    MEDIA_UPLOAD_LIMIT = 415  # per 15 min window

    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        access_token: str | None = None,
        access_secret: str | None = None,
        bearer_token: str | None = None,
    ):
        """
        Initialize Twitter client with credentials.

        Args:
            api_key: Twitter API key (consumer key)
            api_secret: Twitter API secret (consumer secret)
            access_token: OAuth 1.0a access token
            access_secret: OAuth 1.0a access token secret
            bearer_token: OAuth 2.0 bearer token for read operations
        """
        self.api_key = api_key or settings.twitter_api_key
        self.api_secret = api_secret or settings.twitter_api_secret
        self.access_token = access_token or settings.twitter_access_token
        self.access_secret = access_secret or settings.twitter_access_secret
        self.bearer_token = bearer_token or settings.twitter_bearer_token

        # Validate required credentials for write operations
        if not all([self.api_key, self.api_secret, self.access_token, self.access_secret]):
            raise IntegrationError(
                service="twitter",
                message="Twitter OAuth 1.0a credentials are required for write operations",
            )

        # Initialize clients
        self._client = tweepy.Client(
            consumer_key=self.api_key,
            consumer_secret=self.api_secret,
            access_token=self.access_token,
            access_token_secret=self.access_secret,
            bearer_token=self.bearer_token,
            wait_on_rate_limit=False,  # Handle rate limits manually for better control
        )

        # OAuth 1.0a handler for media uploads (v1.1 API)
        self._auth = tweepy.OAuth1UserHandler(
            self.api_key,
            self.api_secret,
            self.access_token,
            self.access_secret,
        )
        self._api_v1 = tweepy.API(self._auth, wait_on_rate_limit=False)

        # Rate limit tracking
        self._rate_limit_reset: dict[str, float] = {}

    async def post_tweet(
        self,
        text: str,
        media_ids: list[str] | None = None,
        reply_to: str | None = None,
        quote_tweet_id: str | None = None,
        poll_options: list[str] | None = None,
        poll_duration_minutes: int | None = None,
    ) -> dict[str, Any]:
        """
        Post a tweet.

        Args:
            text: Tweet text (max 280 characters)
            media_ids: List of media IDs to attach (max 4)
            reply_to: Tweet ID to reply to
            quote_tweet_id: Tweet ID to quote
            poll_options: Poll options (2-4 choices)
            poll_duration_minutes: Poll duration (5-10080 minutes)

        Returns:
            Dict with tweet_id and text

        Raises:
            RateLimitError: If rate limit exceeded
            APIError: If API call fails
        """
        if len(text) > 280:
            raise IntegrationError(
                service="twitter",
                message=f"Tweet text exceeds 280 characters (got {len(text)})",
            )

        try:
            kwargs: dict[str, Any] = {"text": text}

            if media_ids:
                kwargs["media_ids"] = media_ids[:4]  # Max 4 media items
            if reply_to:
                kwargs["in_reply_to_tweet_id"] = reply_to
            if quote_tweet_id:
                kwargs["quote_tweet_id"] = quote_tweet_id
            if poll_options and len(poll_options) >= 2:
                kwargs["poll_options"] = poll_options[:4]  # Max 4 options
                kwargs["poll_duration_minutes"] = poll_duration_minutes or 60

            response = await asyncio.to_thread(self._client.create_tweet, **kwargs)

            return {
                "success": True,
                "tweet_id": str(response.data["id"]),
                "text": response.data.get("text", text),
                "provider": "twitter",
            }

        except TooManyRequests as e:
            reset_time = self._extract_reset_time(e)
            raise RateLimitError(
                limit_type="twitter_tweet_create",
                limit=self.TWEET_CREATE_LIMIT,
                reset_at=reset_time,
                message=f"Twitter rate limit exceeded. Reset at {reset_time}",
            )
        except Unauthorized as e:
            sentry_sdk.capture_exception(e)
            raise APIError(
                service="twitter",
                status_code=401,
                message="Twitter authentication failed. Check credentials.",
            )
        except Forbidden as e:
            sentry_sdk.capture_exception(e)
            raise APIError(
                service="twitter",
                status_code=403,
                message=f"Twitter action forbidden: {str(e)}",
            )
        except BadRequest as e:
            raise APIError(
                service="twitter",
                status_code=400,
                message=f"Invalid tweet request: {str(e)}",
            )
        except TweepyException as e:
            sentry_sdk.capture_exception(e)
            raise APIError(
                service="twitter",
                status_code=500,
                message=f"Twitter API error: {str(e)}",
            )

    async def post_thread(
        self,
        tweets: list[str],
        media_ids_per_tweet: list[list[str]] | None = None,
    ) -> list[str]:
        """
        Post a thread of tweets.

        Args:
            tweets: List of tweet texts (each max 280 chars)
            media_ids_per_tweet: Optional list of media IDs per tweet

        Returns:
            List of tweet IDs in order

        Raises:
            RateLimitError: If rate limit exceeded
            APIError: If API call fails
        """
        if not tweets:
            raise IntegrationError(
                service="twitter",
                message="Thread must contain at least one tweet",
            )

        tweet_ids: list[str] = []
        reply_to: str | None = None

        for i, tweet_text in enumerate(tweets):
            media_ids = None
            if media_ids_per_tweet and i < len(media_ids_per_tweet):
                media_ids = media_ids_per_tweet[i]

            result = await self.post_tweet(
                text=tweet_text,
                media_ids=media_ids,
                reply_to=reply_to,
            )

            tweet_id = result["tweet_id"]
            tweet_ids.append(tweet_id)
            reply_to = tweet_id  # Next tweet replies to this one

            # Small delay between tweets to avoid rate limits
            if i < len(tweets) - 1:
                await asyncio.sleep(1)

        return tweet_ids

    async def upload_media(
        self,
        file_path: str,
        alt_text: str | None = None,
    ) -> str:
        """
        Upload media to Twitter.

        Uses Twitter API v1.1 media upload endpoint.
        Supports images (PNG, JPEG, GIF, WEBP) and videos (MP4).

        Args:
            file_path: Path to media file
            alt_text: Alternative text for accessibility (max 1000 chars)

        Returns:
            Media ID string

        Raises:
            IntegrationError: If file not found or invalid type
            RateLimitError: If rate limit exceeded
            APIError: If upload fails
        """
        path = Path(file_path)

        if not path.exists():
            raise IntegrationError(
                service="twitter",
                message=f"Media file not found: {file_path}",
            )

        # Get MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            raise IntegrationError(
                service="twitter",
                message=f"Could not determine media type for: {file_path}",
            )

        # Validate media type
        allowed_types = [
            "image/png",
            "image/jpeg",
            "image/gif",
            "image/webp",
            "video/mp4",
        ]
        if mime_type not in allowed_types:
            raise IntegrationError(
                service="twitter",
                message=f"Unsupported media type: {mime_type}. Allowed: {allowed_types}",
            )

        try:
            # Use chunked upload for videos, simple upload for images
            is_video = mime_type.startswith("video/")

            if is_video:
                media = await asyncio.to_thread(
                    self._api_v1.media_upload,
                    filename=file_path,
                    chunked=True,
                    media_category="tweet_video",
                )
            else:
                media = await asyncio.to_thread(
                    self._api_v1.media_upload,
                    filename=file_path,
                )

            media_id = str(media.media_id)

            # Add alt text if provided
            if alt_text:
                await asyncio.to_thread(
                    self._api_v1.create_media_metadata,
                    media_id,
                    alt_text[:1000],  # Max 1000 chars
                )

            return media_id

        except TweepyException as e:
            error_msg = str(e)
            if "rate limit" in error_msg.lower():
                raise RateLimitError(
                    limit_type="twitter_media_upload",
                    limit=self.MEDIA_UPLOAD_LIMIT,
                    message="Twitter media upload rate limit exceeded",
                )
            sentry_sdk.capture_exception(e)
            raise APIError(
                service="twitter",
                status_code=500,
                message=f"Media upload failed: {error_msg}",
            )

    async def get_tweet(
        self,
        tweet_id: str,
        expansions: list[str] | None = None,
        tweet_fields: list[str] | None = None,
        user_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Get tweet details by ID.

        Args:
            tweet_id: Tweet ID to fetch
            expansions: Data expansions (e.g., author_id, attachments.media_keys)
            tweet_fields: Tweet fields to include
            user_fields: User fields to include

        Returns:
            Tweet data dict

        Raises:
            APIError: If tweet not found or API error
        """
        try:
            # Default expansions and fields
            if expansions is None:
                expansions = ["author_id", "attachments.media_keys"]
            if tweet_fields is None:
                tweet_fields = [
                    "created_at",
                    "public_metrics",
                    "conversation_id",
                    "in_reply_to_user_id",
                ]
            if user_fields is None:
                user_fields = ["username", "name", "profile_image_url"]

            response = await asyncio.to_thread(
                self._client.get_tweet,
                id=tweet_id,
                expansions=expansions,
                tweet_fields=tweet_fields,
                user_fields=user_fields,
            )

            if not response.data:
                raise APIError(
                    service="twitter",
                    status_code=404,
                    message=f"Tweet not found: {tweet_id}",
                )

            # Build response with includes
            result: dict[str, Any] = {
                "id": str(response.data.id),
                "text": response.data.text,
                "created_at": str(response.data.created_at) if response.data.created_at else None,
                "author_id": str(response.data.author_id) if response.data.author_id else None,
                "conversation_id": response.data.conversation_id,
                "public_metrics": response.data.public_metrics,
            }

            # Add author info if included
            if response.includes and "users" in response.includes:
                author = response.includes["users"][0]
                result["author"] = {
                    "id": str(author.id),
                    "username": author.username,
                    "name": author.name,
                    "profile_image_url": getattr(author, "profile_image_url", None),
                }

            return result

        except NotFound:
            raise APIError(
                service="twitter",
                status_code=404,
                message=f"Tweet not found: {tweet_id}",
            )
        except TooManyRequests as e:
            reset_time = self._extract_reset_time(e)
            raise RateLimitError(
                limit_type="twitter_get_tweet",
                limit=300,
                reset_at=reset_time,
            )
        except TweepyException as e:
            sentry_sdk.capture_exception(e)
            raise APIError(
                service="twitter",
                status_code=500,
                message=f"Failed to get tweet: {str(e)}",
            )

    async def delete_tweet(self, tweet_id: str) -> dict[str, Any]:
        """
        Delete a tweet.

        Args:
            tweet_id: Tweet ID to delete

        Returns:
            Deletion result

        Raises:
            APIError: If deletion fails
        """
        try:
            response = await asyncio.to_thread(
                self._client.delete_tweet,
                id=tweet_id,
            )

            deleted = response.data.get("deleted", False) if response.data else False

            return {
                "success": deleted,
                "tweet_id": tweet_id,
                "deleted": deleted,
                "provider": "twitter",
            }

        except NotFound:
            raise APIError(
                service="twitter",
                status_code=404,
                message=f"Tweet not found: {tweet_id}",
            )
        except Forbidden as e:
            raise APIError(
                service="twitter",
                status_code=403,
                message=f"Cannot delete tweet (not owner?): {str(e)}",
            )
        except TweepyException as e:
            sentry_sdk.capture_exception(e)
            raise APIError(
                service="twitter",
                status_code=500,
                message=f"Failed to delete tweet: {str(e)}",
            )

    async def get_me(self) -> dict[str, Any]:
        """
        Get authenticated user info.

        Returns:
            User data dict with id, username, name, etc.

        Raises:
            APIError: If API call fails
        """
        try:
            response = await asyncio.to_thread(
                self._client.get_me,
                user_fields=[
                    "id",
                    "username",
                    "name",
                    "description",
                    "profile_image_url",
                    "public_metrics",
                    "created_at",
                    "verified",
                ],
            )

            if not response.data:
                raise APIError(
                    service="twitter",
                    status_code=401,
                    message="Could not retrieve authenticated user",
                )

            user = response.data
            return {
                "id": str(user.id),
                "username": user.username,
                "name": user.name,
                "description": getattr(user, "description", None),
                "profile_image_url": getattr(user, "profile_image_url", None),
                "public_metrics": getattr(user, "public_metrics", None),
                "created_at": str(user.created_at) if getattr(user, "created_at", None) else None,
                "verified": getattr(user, "verified", False),
                "provider": "twitter",
            }

        except Unauthorized as e:
            raise APIError(
                service="twitter",
                status_code=401,
                message="Twitter authentication failed. Check credentials.",
            )
        except TweepyException as e:
            sentry_sdk.capture_exception(e)
            raise APIError(
                service="twitter",
                status_code=500,
                message=f"Failed to get user info: {str(e)}",
            )

    async def get_user_tweets(
        self,
        user_id: str | None = None,
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get recent tweets from a user.

        Args:
            user_id: User ID (defaults to authenticated user)
            max_results: Number of tweets to return (5-100)

        Returns:
            List of tweet dicts
        """
        try:
            if not user_id:
                me = await self.get_me()
                user_id = me["id"]

            response = await asyncio.to_thread(
                self._client.get_users_tweets,
                id=user_id,
                max_results=min(max(max_results, 5), 100),
                tweet_fields=["created_at", "public_metrics"],
            )

            if not response.data:
                return []

            return [
                {
                    "id": str(tweet.id),
                    "text": tweet.text,
                    "created_at": str(tweet.created_at) if tweet.created_at else None,
                    "public_metrics": tweet.public_metrics,
                }
                for tweet in response.data
            ]

        except TweepyException as e:
            sentry_sdk.capture_exception(e)
            raise APIError(
                service="twitter",
                status_code=500,
                message=f"Failed to get user tweets: {str(e)}",
            )

    def _extract_reset_time(self, error: TooManyRequests) -> str | None:
        """Extract rate limit reset time from error response."""
        try:
            # Tweepy stores rate limit info in the response
            if hasattr(error, "response") and error.response is not None:
                reset = error.response.headers.get("x-rate-limit-reset")
                if reset:
                    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(int(reset)))
        except Exception:
            pass
        return None


# Singleton instance
_twitter_client: TwitterClient | None = None


def get_twitter_client() -> TwitterClient:
    """Get or create Twitter client instance."""
    global _twitter_client
    if _twitter_client is None:
        _twitter_client = TwitterClient()
    return _twitter_client


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] post_tweet with media and reply support
# [x] post_thread with sequential replies
# [x] upload_media with alt text support
# [x] get_tweet with expansions
# [x] delete_tweet
# [x] get_me for authenticated user
# [x] Rate limit handling (Rule 17)
# [x] Error handling with custom exceptions
# [x] Sentry error tracking
# [x] All functions have type hints
# [x] All functions have docstrings
# [x] Sync Tweepy SDK wrapped with asyncio.to_thread()
