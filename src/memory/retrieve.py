"""
FILE: src/memory/retrieve.py
PURPOSE: Read memories from agent_memories via PostgREST filters.
         v1 — text+tag+type filters only; no embeddings.
"""

import uuid
from datetime import datetime
from typing import Literal

import httpx

from .client import MEMORIES_ENDPOINT, _supabase_headers, _supabase_url
from .types import Memory


def _parse_memory(row: dict) -> Memory:
    def _dt(val: str | None) -> datetime | None:
        if val is None:
            return None
        from datetime import timezone
        from dateutil import parser as dateutil_parser
        try:
            dt = dateutil_parser.isoparse(val)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None

    valid_from_raw = row.get("valid_from")
    created_at_raw = row.get("created_at")

    from datetime import timezone
    valid_from_dt = _dt(valid_from_raw)
    if valid_from_dt is None:
        valid_from_dt = datetime.now(timezone.utc)
    created_at_dt = _dt(created_at_raw)
    if created_at_dt is None:
        created_at_dt = datetime.now(timezone.utc)

    return Memory(
        id=uuid.UUID(row["id"]),
        callsign=row["callsign"],
        source_type=row["source_type"],
        content=row["content"],
        typed_metadata=row.get("typed_metadata") or {},
        tags=row.get("tags") or [],
        valid_from=valid_from_dt,
        valid_to=_dt(row.get("valid_to")),
        created_at=created_at_dt,
    )


def retrieve(
    types: list[str] | None = None,
    callsigns: list[str] | None = None,
    tags: list[str] | None = None,
    tag_mode: Literal["any", "all"] = "any",
    since: datetime | None = None,
    until: datetime | None = None,
    content_contains: str | None = None,
    n: int = 20,
) -> list[Memory]:
    """General filter query. Combines any of: type IN (...), callsign IN (...),
    tags overlap (any) or contain (all), created_at >= since, created_at <= until,
    content ILIKE %X%. Orders by created_at DESC. Limit n."""

    params: list[str] = []

    if types:
        type_csv = ",".join(types)
        params.append(f"source_type=in.({type_csv})")

    if callsigns:
        cs_csv = ",".join(callsigns)
        params.append(f"callsign=in.({cs_csv})")

    if tags:
        tag_csv = ",".join(tags)
        if tag_mode == "all":
            params.append(f"tags=cs.{{{tag_csv}}}")
        else:
            params.append(f"tags=ov.{{{tag_csv}}}")

    if since is not None:
        params.append(f"created_at=gte.{since.isoformat()}")

    if until is not None:
        params.append(f"created_at=lte.{until.isoformat()}")

    if content_contains:
        # Escape any % or _ in the search term to avoid accidental wildcards
        safe = content_contains.replace("%", r"\%").replace("_", r"\_")
        params.append(f"content=ilike.*{safe}*")

    params.append("order=created_at.desc")
    params.append(f"limit={n}")

    qs = "&".join(params)
    url = _supabase_url() + MEMORIES_ENDPOINT + (f"?{qs}" if qs else "")

    try:
        response = httpx.get(url, headers=_supabase_headers(), timeout=10)
        if response.status_code != 200:
            raise RuntimeError(
                f"Supabase returned {response.status_code}: {response.text}"
            )
        return [_parse_memory(row) for row in response.json()]
    except httpx.HTTPError as exc:
        raise RuntimeError(f"HTTP error retrieving memories: {exc}") from exc


def retrieve_by_tags(
    tags: list[str],
    n: int = 20,
    mode: Literal["any", "all"] = "any",
) -> list[Memory]:
    """Convenience: filter by tags only. mode 'any' uses ov., 'all' uses cs."""
    return retrieve(tags=tags, tag_mode=mode, n=n)
