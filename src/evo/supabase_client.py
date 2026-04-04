"""supabase_client.py — Thin Supabase REST helpers shared across evo modules."""
import os
import httpx
from dotenv import load_dotenv

load_dotenv("/home/elliotbot/.config/agency-os/.env")

_URL = os.environ["SUPABASE_URL"]
_KEY = os.environ["SUPABASE_SERVICE_KEY"]
_HEADERS = {
    "apikey": _KEY,
    "Authorization": f"Bearer {_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}


def sb_post(table: str, payload: dict) -> list:
    with httpx.Client(timeout=30) as c:
        r = c.post(f"{_URL}/rest/v1/{table}", headers=_HEADERS, json=payload)
        r.raise_for_status()
        return r.json()


def sb_get(table: str, params: dict) -> list:
    with httpx.Client(timeout=30) as c:
        r = c.get(f"{_URL}/rest/v1/{table}", headers=_HEADERS, params=params)
        r.raise_for_status()
        return r.json()


def sb_patch(table: str, params: dict, payload: dict) -> list:
    with httpx.Client(timeout=30) as c:
        r = c.patch(f"{_URL}/rest/v1/{table}", headers=_HEADERS,
                    params=params, json=payload)
        r.raise_for_status()
        return r.json()
