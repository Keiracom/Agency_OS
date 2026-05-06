#!/usr/bin/env python3
"""Start the Elliot Voice agent.

Creates a Daily.co room (or uses DAILY_ROOM_URL from env), then runs
the Pipecat pipeline until the call ends.

Usage:
    # Auto-create a Daily.co room
    python scripts/start_voice.py

    # Use an existing room
    DAILY_ROOM_URL=https://yourdomain.daily.co/room python scripts/start_voice.py

    # With investor briefing
    python scripts/start_voice.py --briefing "Investor: Jane, Fund: XYZ"
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv("/home/elliotbot/.config/agency-os/.env")
load_dotenv("/home/elliotbot/clawd/Agency_OS/config/.env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def create_daily_room() -> tuple[str, str | None]:
    """Create a Daily.co room via their REST API.

    Returns (room_url, token) tuple. Token may be None for public rooms.
    """
    import httpx

    api_key = os.environ.get("DAILY_API_KEY", "")
    if not api_key:
        logger.error("DAILY_API_KEY not set — cannot create room")
        sys.exit(1)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.daily.co/v1/rooms",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "properties": {
                    "enable_chat": False,
                    "enable_screenshare": False,
                    "start_video_off": True,
                    "start_audio_off": False,
                    "exp": None,  # no expiry
                },
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        room_url = data["url"]
        logger.info("Daily.co room created: %s", room_url)

    # Create a meeting token for the bot
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.daily.co/v1/meeting-tokens",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "properties": {
                    "room_name": data["name"],
                    "is_owner": True,
                    "user_name": "Elliot",
                },
            },
            timeout=15,
        )
        resp.raise_for_status()
        token = resp.json().get("token")

    return room_url, token


async def main():
    parser = argparse.ArgumentParser(description="Start Elliot Voice agent")
    parser.add_argument(
        "--briefing",
        help="Investor briefing text (or path to a .txt file)",
    )
    args = parser.parse_args()

    # Load briefing
    briefing = None
    if args.briefing:
        briefing_path = Path(args.briefing)
        if briefing_path.exists():
            briefing = briefing_path.read_text()
        else:
            briefing = args.briefing

    # Verify required API keys
    missing = []
    for key in ["ANTHROPIC_API_KEY", "ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID"]:
        if not os.environ.get(key):
            missing.append(key)
    if missing:
        logger.error("Missing required env vars: %s", ", ".join(missing))
        sys.exit(1)

    # Get or create Daily.co room
    room_url = os.environ.get("DAILY_ROOM_URL")
    token = None
    if not room_url:
        if not os.environ.get("DAILY_API_KEY"):
            logger.error("Set DAILY_ROOM_URL or DAILY_API_KEY to create a room")
            sys.exit(1)
        room_url, token = await create_daily_room()

    print(f"\n{'=' * 60}")
    print("ELLIOT VOICE — Phase 1 MVP")
    print(f"{'=' * 60}")
    print(f"  Room URL: {room_url}")
    print("  Join this URL in your browser to talk to Elliot")
    print(f"{'=' * 60}\n")

    from src.voice.elliot_voice import run_voice_agent

    await run_voice_agent(
        room_url=room_url,
        room_token=token,
        investor_briefing=briefing,
    )


if __name__ == "__main__":
    asyncio.run(main())
