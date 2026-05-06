"""src/pipeline/austender_discovery.py — AusTender → business_universe writer.

Bridges AwardEvent (from src/integrations/austender_client.py) into BU rows.
For each AU supplier event:
  - If an existing BU row matches by ABN → UPDATE signal_source / category_baselines
  - Otherwise INSERT a new minimal row with discovery_source = 'austender_supplier',
    pipeline_stage = 0 (feeds Stage 2+ on next pipeline run)

Per LAW XII: callers go through skills/austender/SKILL.md (PR #583).
Per LAW XIII: any change to call patterns updates the skill in the same PR.

Skill spec: skills/austender/SKILL.md.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from src.integrations.austender_client import (
    AusTenderClient,
    AwardEvent,
    date_range_chunks,
)

logger = logging.getLogger(__name__)

__all__ = [
    "IngestResult",
    "ingest_award_event",
    "run_ingest",
]


@dataclass
class IngestResult:
    """Summary of one AusTender ingest run."""

    fetched: int = 0  # OCDS releases pulled from API
    parsed: int = 0  # AwardEvents successfully parsed (None-returns excluded)
    filtered_non_au: int = 0  # parsed but is_au_supplier()==False
    filtered_low_value: int = 0  # AUD value below threshold
    inserted: int = 0  # new BU rows
    updated: int = 0  # existing BU rows (signal refresh)
    errors: int = 0  # exceptions during write

    def __str__(self) -> str:
        return (
            f"fetched={self.fetched} parsed={self.parsed} "
            f"non_au_filtered={self.filtered_non_au} "
            f"low_value_filtered={self.filtered_low_value} "
            f"inserted={self.inserted} updated={self.updated} errors={self.errors}"
        )


_UPDATE_SQL = """
    UPDATE public.business_universe
    SET signal_source = 'austender_supplier',
        signal_checked_at = NOW(),
        last_signal_refresh = NOW(),
        category_baselines = COALESCE(category_baselines, '{}'::jsonb) ||
            jsonb_build_object('austender', $2::jsonb)
    WHERE abn = $1
    RETURNING id::text
"""


_INSERT_SQL = """
    INSERT INTO public.business_universe (
        id, abn, display_name, discovery_source, discovery_batch_id,
        signal_source, signal_checked_at, last_signal_refresh,
        pipeline_stage, category_baselines, created_at, updated_at
    ) VALUES (
        gen_random_uuid(), $1, $2, 'austender_supplier', $3,
        'austender_supplier', NOW(), NOW(),
        0, jsonb_build_object('austender', $4::jsonb), NOW(), NOW()
    )
    ON CONFLICT (abn) DO UPDATE SET
        signal_source = 'austender_supplier',
        signal_checked_at = NOW(),
        last_signal_refresh = NOW(),
        category_baselines = COALESCE(public.business_universe.category_baselines, '{}'::jsonb) ||
            jsonb_build_object('austender', $4::jsonb)
    RETURNING id::text, (xmax = 0) AS inserted
"""


def _build_jsonb_payload(event: AwardEvent) -> dict[str, Any]:
    """Build the category_baselines.austender jsonb payload from an event."""
    return {
        "contract_id": event.contract_id,
        "contract_value_aud": event.contract_value_aud,
        "awarded_date": event.awarded_date,
        "agency_name": event.agency_name,
        "classification_id": event.classification_id,
    }


async def ingest_award_event(
    event: AwardEvent,
    conn,
    discovery_batch_id: str,
    *,
    dry_run: bool = True,
) -> tuple[str, bool] | None:
    """Persist one AwardEvent to BU. Returns (bu_id, was_inserted) or None on skip.

    Filters out non-AU suppliers and missing-ABN events upstream — caller is
    responsible for that. This function assumes the event is AU-supplier valid.

    Args:
        event: parsed AwardEvent (must have supplier_abn).
        conn: asyncpg connection.
        discovery_batch_id: UUID for tracing the run that produced this row.
        dry_run: when True, logs would-be SQL but does not execute.

    Returns:
        (bu_id, was_inserted) tuple where was_inserted=True means new row.
        None on dry-run or invalid event.
    """
    if not event.supplier_abn or not event.is_au_supplier():
        logger.debug("[austender] skipping non-AU/no-ABN event %s", event.contract_id)
        return None

    payload = _build_jsonb_payload(event)
    payload_json = json.dumps(payload)

    if dry_run:
        logger.info(
            "[austender] DRY-RUN would upsert abn=%s name=%s contract=%s value=%s",
            event.supplier_abn,
            event.supplier_name,
            event.contract_id,
            event.contract_value_aud,
        )
        return None

    # Try UPDATE first (existing BU row); fall back to INSERT if no match.
    updated_id = await conn.fetchval(_UPDATE_SQL, event.supplier_abn, payload_json)
    if updated_id:
        logger.info(
            "[austender] updated bu=%s abn=%s contract=%s",
            updated_id,
            event.supplier_abn,
            event.contract_id,
        )
        return (updated_id, False)

    # No existing row — INSERT
    row = await conn.fetchrow(
        _INSERT_SQL,
        event.supplier_abn,
        event.supplier_name or "",
        discovery_batch_id,
        payload_json,
    )
    if row is None:
        logger.error(
            "[austender] INSERT returned nothing for abn=%s contract=%s",
            event.supplier_abn,
            event.contract_id,
        )
        return None
    bu_id = row["id"]
    inserted = bool(row["inserted"])
    logger.info(
        "[austender] %s bu=%s abn=%s contract=%s",
        "inserted" if inserted else "updated_via_conflict",
        bu_id,
        event.supplier_abn,
        event.contract_id,
    )
    return (bu_id, inserted)


async def run_ingest(
    date_from: date,
    date_to: date,
    conn,
    *,
    value_min_aud: int = 50000,
    dry_run: bool = True,
    client: AusTenderClient | None = None,
) -> IngestResult:
    """Top-level: fetch AusTender awards in a date range, parse, persist to BU.

    Splits wide ranges into <=7-day chunks to avoid OCDS timeouts.

    Args:
        date_from / date_to: inclusive bounds.
        conn: asyncpg connection.
        value_min_aud: AUD value floor (default 50000 per skill spec).
        dry_run: when True, no DB writes.
        client: optional pre-built AusTenderClient (for tests).

    Returns:
        IngestResult with counts.
    """
    result = IngestResult()
    discovery_batch_id = str(uuid4())
    cli = client or AusTenderClient()

    chunks = date_range_chunks(date_from, date_to, step_days=7)
    logger.info(
        "[austender] run_ingest from=%s to=%s chunks=%d batch_id=%s dry_run=%s",
        date_from,
        date_to,
        len(chunks),
        discovery_batch_id,
        dry_run,
    )

    for chunk_from, chunk_to in chunks:
        try:
            releases = await cli.fetch_awards(
                date_from=chunk_from,
                date_to=chunk_to,
                value_min_aud=value_min_aud,
            )
        except Exception as exc:
            logger.error(
                "[austender] fetch failed for chunk %s..%s: %s",
                chunk_from,
                chunk_to,
                exc,
            )
            result.errors += 1
            continue

        result.fetched += len(releases)

        for release in releases:
            event = AwardEvent.from_ocds_release(release)
            if event is None:
                continue
            result.parsed += 1

            if not event.is_au_supplier():
                result.filtered_non_au += 1
                continue

            if (
                event.contract_value_aud is None
                or event.contract_value_aud < value_min_aud
            ):
                result.filtered_low_value += 1
                continue

            try:
                outcome = await ingest_award_event(
                    event,
                    conn,
                    discovery_batch_id,
                    dry_run=dry_run,
                )
            except Exception as exc:
                logger.error(
                    "[austender] write failed for contract=%s: %s",
                    event.contract_id,
                    exc,
                )
                result.errors += 1
                continue

            if outcome is None:
                continue

            _, was_inserted = outcome
            if was_inserted:
                result.inserted += 1
            else:
                result.updated += 1

    logger.info("[austender] run_ingest complete: %s", result)
    return result


def yesterday_aest() -> date:
    """Return yesterday's date in AEST (Australia/Sydney UTC+10/+11).

    Approximation: uses UTC+10 (no DST). Off by 1d for ~half the year on
    edge cases — acceptable for daily-cron 02:00 AEST scheduling. The
    OCDS feed is timezone-naive at the date level anyway.
    """
    aest_now = datetime.now(timezone(timedelta(hours=10)))
    return (aest_now - timedelta(days=1)).date()
