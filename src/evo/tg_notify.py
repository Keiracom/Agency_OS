"""Tiny Telegram send helper for the callback poller."""
import os
import httpx

TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8381203809:AAFiTOe680BCs_X7WdbQYmKl1rSVs9GFycw")
TG_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "7267788033")


def tg_send(text: str) -> None:
    httpx.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        json={"chat_id": TG_CHAT, "text": text},
        timeout=10,
    )
