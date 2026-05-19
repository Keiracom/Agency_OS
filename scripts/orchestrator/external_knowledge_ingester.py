#!/usr/bin/env python3
"""external_knowledge_ingester.py — KEI-232 — third-party-docs ingester.

Crawls a curated set of documentation websites + GitHub repos, rule-chunks
the content (H2/H3 boundaries + size cap, no LLM calls), and upserts into
the Weaviate `ExternalKnowledge` collection. Re-used by the weekly systemd
timer for refresh.

Pattern reuses `scripts/orchestrator/indexer_base.py` helpers — ensure_class,
post_object, deterministic_uuid, aggregate_count — so this script stays
small and inherits the existing convergence + idempotency story.

Usage:
    python3 scripts/orchestrator/external_knowledge_ingester.py            # all sources
    python3 scripts/orchestrator/external_knowledge_ingester.py --source NATS
    python3 scripts/orchestrator/external_knowledge_ingester.py --max-pages 50
    python3 scripts/orchestrator/external_knowledge_ingester.py --json     # JSON outcome

Constraints (Dave directive 2026-05-19):
    - No Claude / LLM API calls during ingestion. Rule-based chunker only.
    - Failed URLs logged verbatim, not silently skipped.
    - Idempotent: same (url, chunk_index) -> same Weaviate UUID.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

# Reuse the existing indexer helpers — same Weaviate client logic as KEI-85
# indexers; no duplication of ensure_class/post_object/aggregate_count.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from indexer_base import (  # noqa: E402
    aggregate_count,
    deterministic_uuid,
    ensure_class,
    post_object,
)

logger = logging.getLogger("external_knowledge_ingester")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

WEAVIATE_CLASS = "ExternalKnowledge"
SOURCE_NAMESPACE = "external_knowledge"
CHUNK_MAX_CHARS = 2000  # Hard cap per chunk; further splits a long section.
CHUNK_MIN_CHARS = 80  # Drop chunks shorter than this — typically nav residue.
DEFAULT_MAX_PAGES = 100  # Per-source crawl ceiling (docs-site BFS).
HTTP_TIMEOUT_SECONDS = 20
GIT_CLONE_TIMEOUT_SECONDS = 180
USER_AGENT = "AgencyOS-ExternalKnowledgeIngester/1.0 (+https://keiracom.com)"

# Source registry — first batch from Dave directive 2026-05-19.
# Each entry: (source_name, kind, target). kind ∈ {"docs", "repo"}.
SOURCES: list[tuple[str, str, str]] = [
    ("NATS", "docs", "https://docs.nats.io"),
    ("NATS", "repo", "https://github.com/nats-io/nats.py"),
    ("NATS", "repo", "https://github.com/nats-io/nats-architecture-and-design"),
    ("Valkey", "docs", "https://valkey.io/docs"),
    ("Valkey", "repo", "https://github.com/valkey-io/valkey-py"),
    ("Weaviate", "docs", "https://weaviate.io/developers/weaviate"),
    ("Weaviate", "repo", "https://github.com/weaviate/weaviate-python-client"),
    ("Cognee", "docs", "https://docs.cognee.ai"),
    ("Cognee", "repo", "https://github.com/topoteretes/cognee"),
    ("LiteLLM", "docs", "https://docs.litellm.ai"),
    ("LiteLLM", "repo", "https://github.com/BerriAI/litellm"),
    ("Supabase", "docs", "https://supabase.com/docs/guides/auth"),
    (
        "Supabase",
        "docs",
        "https://supabase.com/docs/guides/database/postgres/row-level-security",
    ),
    ("Supabase", "docs", "https://supabase.com/docs/reference/python/introduction"),
    ("FastAPI", "docs", "https://fastapi.tiangolo.com"),
    ("asyncpg", "docs", "https://magicstack.github.io/asyncpg/current"),
    ("psycopg3", "docs", "https://www.psycopg.org/psycopg3/docs"),
    ("Docker", "docs", "https://docs.docker.com/engine/install/ubuntu"),
    # Original directive URL https://docs.docker.com/config/containers/systemd is 404
    # — replaced with the current canonical location for Docker+systemd integration.
    ("Docker", "docs", "https://docs.docker.com/engine/containers/start-containers-automatically/"),
    ("systemd", "docs", "https://systemd.io"),
    (
        "systemd",
        "docs",
        "https://www.freedesktop.org/software/systemd/man/systemd.service.html",
    ),
    ("LinearAPI", "docs", "https://developers.linear.app/docs"),
    # Original directive URL https://betterstack.com/docs/logs/getting-started is 404
    # — replaced with the current canonical Logs index entry point.
    ("BetterStack", "docs", "https://betterstack.com/docs/logs/start/"),
    ("BetterStack", "docs", "https://betterstack.com/docs/uptime/webhooks"),
    ("ClaudeCode", "docs", "https://docs.anthropic.com/en/docs/claude-code/overview"),
]


# ---------------------------------------------------------------------------
# Weaviate schema.
# ---------------------------------------------------------------------------


def class_schema() -> dict:
    """ExternalKnowledge class definition. text2vec-openai on `content`."""
    return {
        "class": WEAVIATE_CLASS,
        "description": "Pre-loaded third-party documentation chunks (KEI-232).",
        "vectorizer": "text2vec-openai",
        "moduleConfig": {
            "text2vec-openai": {
                "model": "text-embedding-3-small",
                "type": "text",
            }
        },
        "properties": [
            {
                "name": "url",
                "dataType": ["text"],
                "moduleConfig": {"text2vec-openai": {"skip": True}},
            },
            {
                "name": "source_name",
                "dataType": ["text"],
                "moduleConfig": {"text2vec-openai": {"skip": True}},
            },
            {"name": "section_title", "dataType": ["text"]},
            {"name": "content", "dataType": ["text"]},
            {
                "name": "chunk_index",
                "dataType": ["int"],
                "moduleConfig": {"text2vec-openai": {"skip": True}},
            },
            {
                "name": "ingested_at",
                "dataType": ["date"],
                "moduleConfig": {"text2vec-openai": {"skip": True}},
            },
        ],
    }


# ---------------------------------------------------------------------------
# HTML → text.
# ---------------------------------------------------------------------------


class _TextExtractor(HTMLParser):
    """Strip-but-keep-structure HTML→text. Standard-lib only (no bs4 dep
    in production runtime; tests run fine without external deps either)."""

    _BLOCK_TAGS = {
        "p",
        "div",
        "section",
        "article",
        "li",
        "br",
        "tr",
        "td",
        "th",
        "blockquote",
    }
    _SKIP_TAGS = {"script", "style", "nav", "footer", "header", "aside", "noscript"}
    _HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}

    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, _attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1
        elif tag in self._HEADING_TAGS:
            self._chunks.append("\n## ")
        elif tag in self._BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag in self._BLOCK_TAGS or tag in self._HEADING_TAGS:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        if data.strip():
            self._chunks.append(data)

    def text(self) -> str:
        raw = "".join(self._chunks)
        # Collapse 3+ newlines, trim trailing whitespace per line.
        out = re.sub(r"\n{3,}", "\n\n", raw)
        out = "\n".join(line.rstrip() for line in out.splitlines())
        return out.strip()


def html_to_text(html: str) -> str:
    p = _TextExtractor()
    try:
        p.feed(html)
    except Exception as exc:  # noqa: BLE001 — malformed HTML must not crash crawl
        logger.warning("HTML parse partial: %s", exc)
    return p.text()


# ---------------------------------------------------------------------------
# Rule-based chunker.
# ---------------------------------------------------------------------------


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.M)


def chunk_text(text: str, default_title: str) -> list[tuple[str, str]]:
    """Split `text` into (section_title, chunk_content) tuples.

    Rules:
      1. Section boundary = any markdown heading (`#`–`######`) OR HTML heading
         already converted to `## ` prefix by html_to_text.
      2. Within a section, if content exceeds CHUNK_MAX_CHARS, split on blank
         lines first; if still over the cap, hard-cut at CHUNK_MAX_CHARS.
      3. Drop chunks shorter than CHUNK_MIN_CHARS (typically nav residue).
    """
    if not text or not text.strip():
        return []
    sections: list[tuple[str, str]] = []
    cursor = 0
    current_title = default_title
    for match in _HEADING_RE.finditer(text):
        body = text[cursor : match.start()].strip()
        if body:
            sections.append((current_title, body))
        current_title = match.group(2).strip()[:200]
        cursor = match.end()
    tail = text[cursor:].strip()
    if tail:
        sections.append((current_title, tail))

    chunks: list[tuple[str, str]] = []
    for title, body in sections:
        for sub in _split_oversized(body):
            if len(sub) >= CHUNK_MIN_CHARS:
                chunks.append((title, sub))
    return chunks


def _split_oversized(body: str) -> list[str]:
    """If body > CHUNK_MAX_CHARS, split on blank-line boundary, then hard-cut."""
    if len(body) <= CHUNK_MAX_CHARS:
        return [body]
    out: list[str] = []
    buf: list[str] = []
    buf_len = 0
    for para in re.split(r"\n\s*\n", body):
        if buf_len + len(para) + 2 > CHUNK_MAX_CHARS and buf:
            out.append("\n\n".join(buf))
            buf = [para]
            buf_len = len(para)
        else:
            buf.append(para)
            buf_len += len(para) + 2
    if buf:
        out.append("\n\n".join(buf))
    # Final hard-cut pass for any paragraph that itself exceeded the cap.
    final: list[str] = []
    for chunk in out:
        if len(chunk) <= CHUNK_MAX_CHARS:
            final.append(chunk)
            continue
        for i in range(0, len(chunk), CHUNK_MAX_CHARS):
            final.append(chunk[i : i + CHUNK_MAX_CHARS])
    return final


# ---------------------------------------------------------------------------
# HTTP fetch with backoff.
# ---------------------------------------------------------------------------


def fetch_url(url: str, timeout: int = HTTP_TIMEOUT_SECONDS) -> str | None:
    """GET `url`; return body str or None on failure. Retries with backoff."""
    backoff = 1.0
    for attempt in range(1, 4):
        try:
            req = urlrequest.Request(
                url,
                headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*;q=0.8"},
            )
            with urlrequest.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    raw = resp.read()
                    # Best-effort decode — most docs sites are UTF-8.
                    return raw.decode("utf-8", errors="replace")
                logger.warning("fetch %s rc=%d attempt=%d", url, resp.status, attempt)
        except urlerror.HTTPError as exc:
            if exc.code in (404, 410):
                # Permanent — no retry.
                logger.warning("fetch %s permanent %d", url, exc.code)
                return None
            logger.warning("fetch %s HTTPError=%d attempt=%d", url, exc.code, attempt)
        except (urlerror.URLError, OSError, TimeoutError) as exc:
            logger.warning("fetch %s transient %s attempt=%d", url, exc, attempt)
        if attempt < 3:
            time.sleep(backoff)
            backoff *= 2
    return None


# ---------------------------------------------------------------------------
# Docs-site BFS crawler.
# ---------------------------------------------------------------------------


_LINK_RE = re.compile(r'href=["\']([^"\']+)["\']', re.I)


def crawl_docs_site(seed_url: str, max_pages: int) -> dict[str, str]:
    """BFS-crawl same-domain HTML pages starting from `seed_url`.

    Returns {url: html_body}. Limits to `max_pages` to bound runtime.
    Same-domain match uses the host AND the seed's URL prefix (so e.g.
    crawling `https://supabase.com/docs/guides/auth` won't wander into
    `https://supabase.com/blog/...`).
    """
    parsed = urlparse.urlparse(seed_url)
    prefix_path = parsed.path or "/"
    # Trim trailing slash on prefix so /docs and /docs/ both match /docs/x.
    prefix_norm = prefix_path.rstrip("/") if prefix_path != "/" else "/"

    seen: set[str] = set()
    pages: dict[str, str] = {}
    queue: deque[str] = deque([seed_url])
    while queue and len(pages) < max_pages:
        url = queue.popleft()
        if url in seen:
            continue
        seen.add(url)
        body = fetch_url(url)
        if body is None:
            continue
        pages[url] = body
        for href in _LINK_RE.findall(body):
            # Skip unrendered template syntax — some docs sites (e.g. Docker)
            # leak Jinja2 placeholders into href attributes; fetching them
            # raises http.client.InvalidURL on the control characters.
            if "{{" in href or "}}" in href or "{%" in href:
                continue
            absolute = urlparse.urljoin(url, href)
            absolute = absolute.split("#", 1)[0]
            # Drop fragments + query strings (anchor-only links produce dup
            # pages with same content; nav-bar links carry the seed-page body).
            p = urlparse.urlparse(absolute)
            if p.netloc != parsed.netloc:
                continue
            if prefix_norm not in ("/", "") and not p.path.startswith(prefix_norm):
                continue
            # Final guard — any whitespace or control char in the URL means
            # leftover template residue; skip rather than blow up urlopen.
            if any(c.isspace() or ord(c) < 32 for c in absolute):
                continue
            if absolute not in seen:
                queue.append(absolute)
    return pages


# ---------------------------------------------------------------------------
# GitHub repo walk.
# ---------------------------------------------------------------------------


_REPO_DOC_EXTS = {".md", ".rst", ".txt"}


def fetch_repo_docs(repo_url: str) -> dict[str, str]:
    """Shallow-clone the repo to a tempdir and return {file_url: content}
    for every doc-ish file (.md / .rst / .txt). Cleans up the tempdir on
    return.

    `file_url` is constructed as `{repo_url}/blob/HEAD/{relative_path}` so
    each chunk's `url` deep-links to the source file in the GitHub UI.
    """
    tmpdir = tempfile.mkdtemp(prefix="ext_knowledge_")
    try:
        cmd = ["git", "clone", "--depth", "1", "--quiet", repo_url, tmpdir]
        try:
            subprocess.run(  # noqa: S603 — controlled args, no shell
                cmd,
                check=False,
                capture_output=True,
                timeout=GIT_CLONE_TIMEOUT_SECONDS,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
            logger.warning("clone %s failed: %s", repo_url, exc)
            return {}
        out: dict[str, str] = {}
        root = Path(tmpdir)
        for p in root.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in _REPO_DOC_EXTS:
                continue
            rel = p.relative_to(root).as_posix()
            try:
                content = p.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                logger.warning("read %s failed: %s", rel, exc)
                continue
            if not content.strip():
                continue
            file_url = f"{repo_url.rstrip('/')}/blob/HEAD/{rel}"
            out[file_url] = content
        return out
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Ingester orchestration.
# ---------------------------------------------------------------------------


@dataclass
class SourceOutcome:
    source_name: str
    kind: str
    target: str
    pages: int = 0
    chunks_posted: int = 0
    failures: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "source_name": self.source_name,
            "kind": self.kind,
            "target": self.target,
            "pages": self.pages,
            "chunks_posted": self.chunks_posted,
            "failures": self.failures,
        }


def ingest_source(
    source_name: str,
    kind: str,
    target: str,
    *,
    max_pages: int = DEFAULT_MAX_PAGES,
) -> SourceOutcome:
    outcome = SourceOutcome(source_name=source_name, kind=kind, target=target)
    if kind == "docs":
        pages = crawl_docs_site(target, max_pages)
    elif kind == "repo":
        pages = fetch_repo_docs(target)
    else:
        outcome.failures.append(f"unknown kind={kind}")
        return outcome
    outcome.pages = len(pages)
    if not pages:
        outcome.failures.append(f"no pages fetched from {target}")
        return outcome

    now = datetime.now(UTC).isoformat()
    for page_url, raw_body in pages.items():
        try:
            if kind == "docs":
                text = html_to_text(raw_body)
            else:
                text = raw_body
            chunks = chunk_text(text, default_title=page_url.rsplit("/", 1)[-1] or page_url)
        except Exception as exc:  # noqa: BLE001 — never crash crawl on chunker bug
            outcome.failures.append(f"chunk {page_url}: {exc}")
            continue
        for idx, (title, body) in enumerate(chunks):
            obj = {
                "id": deterministic_uuid(SOURCE_NAMESPACE, f"{page_url}#{idx}"),
                "class": WEAVIATE_CLASS,
                "properties": {
                    "url": page_url,
                    "source_name": source_name,
                    "section_title": title,
                    "content": body,
                    "chunk_index": idx,
                    "ingested_at": now,
                },
            }
            if post_object(obj):
                outcome.chunks_posted += 1
            else:
                outcome.failures.append(f"post {page_url}#{idx}")
    return outcome


def ingest_all(
    *,
    filter_source: str | None = None,
    max_pages: int = DEFAULT_MAX_PAGES,
) -> list[SourceOutcome]:
    ensure_class(WEAVIATE_CLASS, class_schema())
    outcomes: list[SourceOutcome] = []
    for source_name, kind, target in SOURCES:
        if filter_source and filter_source.lower() != source_name.lower():
            continue
        logger.info("ingest %s (%s) <- %s", source_name, kind, target)
        outcomes.append(ingest_source(source_name, kind, target, max_pages=max_pages))
    return outcomes


def _print_report(outcomes: list[SourceOutcome], emit_json: bool = False) -> None:
    if emit_json:
        print(json.dumps([o.to_dict() for o in outcomes], indent=2))
        return
    total_chunks = sum(o.chunks_posted for o in outcomes)
    total_pages = sum(o.pages for o in outcomes)
    total_failures = sum(len(o.failures) for o in outcomes)
    print(
        f"\nIngest report — sources={len(outcomes)} pages={total_pages} "
        f"chunks={total_chunks} failures={total_failures}\n"
    )
    print(f"{'source':<14} {'kind':<5} {'pages':>6} {'chunks':>7} {'fail':>5}  target")
    print("-" * 100)
    for o in outcomes:
        print(
            f"{o.source_name:<14} {o.kind:<5} {o.pages:>6} {o.chunks_posted:>7} "
            f"{len(o.failures):>5}  {o.target}"
        )
        for failure in o.failures[:3]:
            print(f"  FAIL: {failure}")
    after = aggregate_count(WEAVIATE_CLASS)
    print(f"\nExternalKnowledge total count after run: {after}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", help="Ingest only this source_name (case-insensitive)")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=int(os.environ.get("EXTERNAL_KNOWLEDGE_MAX_PAGES", DEFAULT_MAX_PAGES)),
        help="Per-source page ceiling for docs-site BFS",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON outcome")
    args = parser.parse_args(argv)
    outcomes = ingest_all(filter_source=args.source, max_pages=args.max_pages)
    _print_report(outcomes, emit_json=args.json)
    # Exit 1 if any source produced ZERO chunks AND ZERO failures (mute drop).
    silent_drops = [o for o in outcomes if o.chunks_posted == 0 and not o.failures]
    if silent_drops:
        for o in silent_drops:
            logger.error(
                "source %s produced no chunks and no failures — investigate", o.source_name
            )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
