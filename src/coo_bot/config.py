"""COO Bot configuration — loaded from environment at import time."""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv("/home/elliotbot/.config/agency-os/.env")


class COOConfig:
    """Configuration container for the COO bot (Max).

    All values sourced from environment variables. Required vars raise
    ValueError at instantiation if absent so failures surface at startup.
    """

    def __init__(self) -> None:
        self.bot_token: str = self._require("COO_BOT_TOKEN")
        self.openai_api_key: str = self._require("OPENAI_API_KEY")
        self.dave_chat_id: int = int(os.getenv("COO_DAVE_CHAT_ID", "7267788033"))
        self.digest_interval_minutes: int = int(
            os.getenv("COO_DIGEST_INTERVAL_MINUTES", "60")
        )
        raw_dsn = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL") or ""
        # asyncpg rejects the SQLAlchemy prefix — strip it
        self.database_url: str = raw_dsn.replace(
            "postgresql+asyncpg://", "postgresql://"
        )

    @staticmethod
    def _require(key: str) -> str:
        val = os.getenv(key, "")
        if not val:
            raise ValueError(f"COO bot: required env var {key!r} is not set")
        return val
