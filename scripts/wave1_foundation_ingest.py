#!/usr/bin/env python3
"""Wave 1 foundation ingest into Weaviate Discoveries collection.

KEI-73 Phase B (Dave-direct dispatch 2026-05-16). Ingests Supabase tables
and filesystem docs into Discoveries via direct Weaviate REST + fastembed
local embeddings (BGE-small-en-v1.5, 384-dim).

Originally tried Max's KEI-49 orchestrator surface (src/retrieval/
orchestrator.py) but llama-index is declared in requirements.txt and
never installed in the venv — KEI-49 was tagged research/analysis/
documentation, not runtime. Direct-REST path uses installed deps only
(fastembed 0.8.0, urllib stdlib), preserves the canonical schema, and
matches the "or equivalent" surface latitude Dave authorised.

Sources:
    Supabase: ceo_memory, ceo_memory_archive, tasks, task_verifications,
              tier_registry
    Filesystem: ~/.claude/projects/.../memory/*.md, /home/elliotbot/clawd/
              skills/*/SKILL.md, docs/governance/*.md, ARCHITECTURE.md

Role-flag (Class 1+3): rows with created_at < 2026-05-11 get
metadata['pre_role_swap']=True (era: Elliot=CTO, Max=COO). Files without
a discoverable created_at fall through to False.

Idempotency: source_id-derived deterministic UUID. Re-run replaces.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib import error as urlerror
from urllib import request as urlrequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("wave1")

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

ENV_HASH = hashlib.sha256(
    f"weaviate-1.32:bge-small:{datetime.now(timezone.utc).date().isoformat()}".encode()
).hexdigest()[:16]
ROLE_SWAP_BOUNDARY = datetime(2026, 5, 11, tzinfo=timezone.utc)
COLLECTION = "Discoveries"
WEAVIATE_BASE = "http://127.0.0.1:8090"  # NOSONAR
NS_UUID = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # DNS namespace
MEMORY_DIR = Path.home() / ".claude/projects/-home-elliotbot-clawd-Agency-OS/memory"
SKILLS_DIR = Path("/home/elliotbot/clawd/skills")
GOV_DIR = REPO_ROOT / "docs/governance"
ARCH_PATH = REPO_ROOT / "ARCHITECTURE.md"
MCP_BRIDGE = Path("/home/elliotbot/clawd/skills/mcp-bridge/scripts/mcp-bridge.js")

_EMBED_MODEL = None


def get_embedder():
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        from fastembed import TextEmbedding
        _EMBED_MODEL = TextEmbedding("BAAI/bge-small-en-v1.5")
    return _EMBED_MODEL


@dataclass(frozen=True)
class IngestRow:
    text: str
    source_id: str
    agent: str
    kei: str
    created_at: str


def _supabase_query(sql: str) -> list[dict]:
    result = subprocess.run(
        ["node", str(MCP_BRIDGE), "call", "supabase", "execute_sql",
         json.dumps({"project_id": "jatzvazlbusedwsnqxzr", "query": sql})],
        capture_output=True, text=True, timeout=180, check=False,
    )
    stdout = result.stdout
    try:
        outer = json.loads(stdout)
        inner = outer.get("result", "") if isinstance(outer, dict) else ""
    except json.JSONDecodeError:
        inner = stdout
    match = re.search(r"<untrusted-data-[a-f0-9-]+>\s*(\[.*?\])\s*</untrusted-data-",
                      inner, re.DOTALL)
    if not match:
        log.warning("no rows parsed; stdout head: %s", stdout[:300])
        return []
    return json.loads(match.group(1))


def _role_flag(created_at_iso: str) -> bool:
    if not created_at_iso:
        return False
    try:
        dt = datetime.fromisoformat(_to_rfc3339(created_at_iso).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt < ROLE_SWAP_BOUNDARY
    except (ValueError, TypeError):
        return False


def _to_rfc3339(ts: str) -> str:
    """Normalise Postgres timestamps to RFC3339 (Weaviate's date format).

    Postgres returns '2026-05-14 08:14:38.212462+00'; Weaviate's typed
    `date` property wants '2026-05-14T08:14:38.212462+00:00'. Replace
    space with T and pad timezone offset.
    """
    if not ts:
        return "2026-01-01T00:00:00+00:00"
    ts = ts.strip().replace(" ", "T")
    m = re.match(r"^(.+)([+-])(\d{2})(:?(\d{2}))?$", ts)
    if m:
        base, sign, hh, _, mm = m.groups()
        ts = f"{base}{sign}{hh}:{mm or '00'}"
    return ts


def _det_uuid(source_id: str) -> str:
    return str(uuid.uuid5(NS_UUID, source_id))


def _weaviate_post(obj: dict) -> tuple[int, str]:
    body = json.dumps(obj).encode("utf-8")
    req = urlrequest.Request(
        f"{WEAVIATE_BASE}/v1/objects",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=30) as resp:  # noqa: S310
            return resp.status, resp.read().decode("utf-8")[:300]
    except urlerror.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")[:300]


def _weaviate_delete_if_exists(uid: str) -> None:
    req = urlrequest.Request(
        f"{WEAVIATE_BASE}/v1/objects/{COLLECTION}/{uid}",
        method="DELETE",
    )
    try:
        urlrequest.urlopen(req, timeout=10)  # noqa: S310
    except urlerror.HTTPError:
        pass


def _index_row(row: IngestRow, embedder) -> bool:
    uid = _det_uuid(row.source_id)
    _weaviate_delete_if_exists(uid)
    vector = list(map(float, next(embedder.embed([row.text]))))
    obj = {
        "id": uid,
        "class": COLLECTION,
        "vector": vector,
        "properties": {
            "raw_text": row.text[:30000],
            "environment_hash": ENV_HASH,
            "created_at": _to_rfc3339(row.created_at),
            "agent": row.agent,
            "kei": row.kei or "",
            "source_id": row.source_id,
            "pre_role_swap": _role_flag(row.created_at),
        },
    }
    status, body = _weaviate_post(obj)
    if status not in (200, 201):
        log.warning("POST status=%d for %s body=%s", status, row.source_id, body[:200])
        return False
    return True


def _ingest_batch(label: str, rows: list[IngestRow], embedder) -> int:
    n = 0
    for r in rows:
        if _index_row(r, embedder):
            n += 1
    log.info("%-26s indexed=%d / total=%d", label, n, len(rows))
    return n


# ---- Source extractors -----------------------------------------------------


def src_ceo_memory() -> list[IngestRow]:
    rows = _supabase_query(
        "SELECT key, value::text AS value, updated_at FROM public.ceo_memory "
        "ORDER BY updated_at"
    )
    return [
        IngestRow(
            text=f"[ceo_memory:{r.get('key','')}]\n{r.get('value','')}",
            source_id=f"ceo_memory:{r['key']}",
            agent="ceo",
            kei="",
            created_at=r.get("updated_at", ""),
        ) for r in rows
    ]


def src_ceo_memory_archive() -> list[IngestRow]:
    rows = _supabase_query(
        "SELECT key, value::text AS value, archived_at, archive_reason "
        "FROM public.ceo_memory_archive"
    )
    return [
        IngestRow(
            text=f"[ceo_memory_archive:{r.get('key','')}] reason={r.get('archive_reason','')}\n"
                 f"{r.get('value','')}",
            source_id=f"ceo_memory_archive:{r['key']}",
            agent="ceo",
            kei="",
            created_at=r.get("archived_at", ""),
        ) for r in rows
    ]


def src_tasks() -> list[IngestRow]:
    rows = _supabase_query(
        "SELECT id, title, acceptance_criteria, created_at FROM public.tasks "
        "WHERE acceptance_criteria IS NOT NULL"
    )
    out = []
    for r in rows:
        kei = r["id"] if str(r.get("id", "")).startswith("KEI-") else ""
        out.append(IngestRow(
            text=f"[{r.get('id')}] {r.get('title','')}\nAcceptance: {r.get('acceptance_criteria','')}",
            source_id=f"tasks:{r['id']}",
            agent="planner",
            kei=kei,
            created_at=r.get("created_at", ""),
        ))
    return out


def src_task_verifications() -> list[IngestRow]:
    rows = _supabase_query(
        "SELECT id, task_id, test_output, created_at FROM public.task_verifications "
        "WHERE test_output IS NOT NULL"
    )
    return [
        IngestRow(
            text=f"[task_verification:{r.get('task_id')}]\n{(r.get('test_output') or '')[:4000]}",
            source_id=f"task_verifications:{r['id']}",
            agent="verifier",
            kei=str(r.get("task_id")) if str(r.get("task_id","")).startswith("KEI-") else "",
            created_at=r.get("created_at", ""),
        ) for r in rows
    ]


def src_tier_registry() -> list[IngestRow]:
    rows = _supabase_query("SELECT * FROM public.tier_registry")
    out = []
    for r in rows:
        body = ", ".join(f"{k}={v}" for k, v in r.items() if v is not None)
        callsign = r.get("callsign") or r.get("name") or r.get("id") or "unknown"
        out.append(IngestRow(
            text=f"[tier_registry:{callsign}]\n{body}",
            source_id=f"tier_registry:{callsign}",
            agent=str(callsign),
            kei="",
            created_at=r.get("registered_at") or r.get("created_at") or "2026-04-22T00:00:00+00:00",
        ))
    return out


def src_memory_notes() -> list[IngestRow]:
    out = []
    for p in sorted(MEMORY_DIR.glob("*.md")):
        if p.name == "MEMORY.md":
            continue
        text = p.read_text(encoding="utf-8")
        mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat()
        out.append(IngestRow(
            text=f"[memory:{p.stem}]\n{text}",
            source_id=f"memory:{p.name}",
            agent="team",
            kei="",
            created_at=mtime,
        ))
    return out


def src_skills() -> list[IngestRow]:
    out = []
    for p in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        text = p.read_text(encoding="utf-8")
        mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat()
        out.append(IngestRow(
            text=f"[skill:{p.parent.name}]\n{text}",
            source_id=f"skill:{p.parent.name}",
            agent="system",
            kei="",
            created_at=mtime,
        ))
    return out


def src_governance() -> list[IngestRow]:
    out = []
    for p in sorted(GOV_DIR.rglob("*.md")):
        text = p.read_text(encoding="utf-8")
        rel = p.relative_to(REPO_ROOT)
        mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat()
        out.append(IngestRow(
            text=f"[governance:{rel}]\n{text}",
            source_id=f"governance:{rel}",
            agent="governance",
            kei="",
            created_at=mtime,
        ))
    return out


def src_architecture() -> list[IngestRow]:
    text = ARCH_PATH.read_text(encoding="utf-8")
    mtime = datetime.fromtimestamp(ARCH_PATH.stat().st_mtime, tz=timezone.utc).isoformat()
    sections = re.split(r"^(?=## )", text, flags=re.MULTILINE)
    out = []
    for i, section in enumerate(sections):
        if not section.strip():
            continue
        heading = section.split("\n", 1)[0].strip()[:80]
        out.append(IngestRow(
            text=f"[ARCHITECTURE.md#{i}: {heading}]\n{section[:8000]}",
            source_id=f"architecture:section_{i:02d}",
            agent="system",
            kei="",
            created_at=mtime,
        ))
    return out


# ---- Main ------------------------------------------------------------------


def main() -> int:
    log.info("env_hash=%s role_swap_boundary=%s", ENV_HASH, ROLE_SWAP_BOUNDARY.date())
    log.info("warming embedder (BAAI/bge-small-en-v1.5)...")
    embedder = get_embedder()
    log.info("embedder ready")

    sources = [
        ("ceo_memory", src_ceo_memory),
        ("ceo_memory_archive", src_ceo_memory_archive),
        ("tasks", src_tasks),
        ("task_verifications", src_task_verifications),
        ("tier_registry", src_tier_registry),
        ("memory_notes", src_memory_notes),
        ("skills", src_skills),
        ("governance", src_governance),
        ("architecture", src_architecture),
    ]

    tally: dict[str, int] = {}
    for label, fn in sources:
        try:
            rows = fn()
        except Exception:  # noqa: BLE001
            log.error("extraction failed for %s", label, exc_info=True)
            tally[label] = 0
            continue
        tally[label] = _ingest_batch(label, rows, embedder)

    total = sum(tally.values())
    log.info("===== WAVE 1 INGEST COMPLETE =====")
    for k, v in tally.items():
        log.info("  %-26s %d", k, v)
    log.info("  %-26s %d", "TOTAL", total)
    print(json.dumps({"tally": tally, "total": total, "env_hash": ENV_HASH}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
