"""
Contract: src/enrichment/email_verifier.py
Purpose: SMTP-based email discovery and verification. Zero cost. No external API.
         Discovers DM emails via RCPT TO probing across 13 pattern variants.
         Groups by domain to reuse SMTP connections and MX lookups.
Layer: 2 - integrations
Directive: #301
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
import smtplib
import string
import time
from dataclasses import dataclass, field
from typing import Any

import dns.resolver

logger = logging.getLogger(__name__)

# ── Pattern generation ────────────────────────────────────────────────────────


def _clean(name: str) -> str:
    """Lowercase, strip non-alpha except spaces, collapse spaces."""
    return re.sub(r"[^a-z\s]", "", name.lower()).strip()


def generate_patterns(first_name: str, last_name: str, domain: str) -> list[str]:
    """
    Generate 13 email pattern variants for a person at a domain.
    Returns deduplicated list of candidate email addresses.
    """
    f = _clean(first_name)
    l = _clean(last_name)
    fi = f[0] if f else ""
    li = l[0] if l else ""

    domain = domain[4:] if domain.startswith("www.") else domain

    candidates: list[str] = []
    templates = []

    if f:
        templates.append(f"{f}@{domain}")  # first@
    if l:
        templates.append(f"{l}@{domain}")  # last@
    if f and l:
        templates.append(f"{f}.{l}@{domain}")  # first.last@
        templates.append(f"{l}.{f}@{domain}")  # last.first@
        templates.append(f"{f}{l}@{domain}")  # firstlast@
        templates.append(f"{l}{f}@{domain}")  # lastfirst@
    if fi and l:
        templates.append(f"{fi}.{l}@{domain}")  # f.last@
        templates.append(f"{fi}{l}@{domain}")  # flast@
    if f and li:
        templates.append(f"{f}.{li}@{domain}")  # first.l@
    if f and l:
        templates.append(f"{f}_{l}@{domain}")  # first_last@
    if fi and l:
        templates.append(f"{fi}_{l}@{domain}")  # f_last@
    if f and l:
        templates.append(f"{f}-{l}@{domain}")  # first-last@
    if fi and l:
        templates.append(f"{fi}-{l}@{domain}")  # f-last@

    # Deduplicate while preserving order
    seen: set[str] = set()
    for t in templates:
        if t not in seen:
            seen.add(t)
            candidates.append(t)

    return candidates


# ── MX resolution ─────────────────────────────────────────────────────────────


def resolve_mx(domain: str, timeout: float = 5.0) -> str | None:
    """Resolve MX record for domain. Returns highest-priority MX host or None."""
    resolver = dns.resolver.Resolver()
    resolver.lifetime = timeout
    try:
        answers = resolver.resolve(domain, "MX")
        # Lowest preference = highest priority
        best = sorted(answers, key=lambda r: r.preference)[0]
        return str(best.exchange).rstrip(".")
    except Exception:
        return None


# ── SMTP probing ──────────────────────────────────────────────────────────────


@dataclass
class SmtpProbeResult:
    domain: str
    mx_host: str | None
    accept_all: bool
    verified_emails: list[str] = field(default_factory=list)
    invalid_emails: list[str] = field(default_factory=list)
    patterns_tested: int = 0
    error: str | None = None
    time_seconds: float = 0.0


def _smtp_probe(
    candidates: list[str],
    mx_host: str,
    domain: str,
    sender: str = "verify@example-check.com",
    timeout: float = 10.0,
) -> tuple[list[str], list[str], bool]:
    """
    Open one SMTP connection, send one EHLO + MAIL FROM, then RCPT TO each candidate.
    Returns (verified, invalid, accept_all).
    Accept-all check: probe one random garbage address first.
    """
    verified: list[str] = []
    invalid: list[str] = []

    # Random garbage address for accept-all detection
    rand_local = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))
    canary = f"{rand_local}@{domain}"

    try:
        smtp = smtplib.SMTP(timeout=timeout)
        smtp.connect(mx_host, 25)
        smtp.ehlo_or_helo_if_needed()
        smtp.mail(sender)

        # Canary check
        code, _ = smtp.rcpt(canary)
        accept_all = code == 250

        if accept_all:
            smtp.quit()
            return [], [], True

        # Probe each candidate
        for email in candidates:
            try:
                code, _ = smtp.rcpt(email)
                if code == 250:
                    verified.append(email)
                else:
                    invalid.append(email)
            except smtplib.SMTPServerDisconnected:
                # Server dropped connection — stop probing this domain
                break
            except Exception:
                invalid.append(email)

        smtp.quit()
    except smtplib.SMTPConnectError:
        return [], [], False
    except smtplib.SMTPException:
        raise
    except (TimeoutError, OSError):
        raise

    return verified, invalid, False


def probe_domain(
    candidates: list[str],
    domain: str,
    mx_host: str,
    timeout: float = 10.0,
) -> SmtpProbeResult:
    """Synchronous SMTP probe of all candidate emails for a single domain."""
    t0 = time.monotonic()
    result = SmtpProbeResult(domain=domain, mx_host=mx_host, accept_all=False)
    try:
        verified, invalid, accept_all = _smtp_probe(candidates, mx_host, domain, timeout=timeout)
        result.verified_emails = verified
        result.invalid_emails = invalid
        result.accept_all = accept_all
        result.patterns_tested = len(candidates)
    except Exception as exc:
        result.error = str(exc)
    result.time_seconds = round(time.monotonic() - t0, 2)
    return result


# ── Public API ────────────────────────────────────────────────────────────────

SMTP_SEM = asyncio.Semaphore(20)


async def discover_email(
    first_name: str,
    last_name: str,
    domain: str,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """
    FUNCTION 1: Discover DM email via SMTP RCPT TO probing.

    1. Generate 13 pattern variants.
    2. Resolve MX record once.
    3. Open ONE SMTP connection.
    4. HELO + MAIL FROM once.
    5. RCPT TO each variant.
    6. Accept-all check via canary address.
    7. QUIT.

    Returns dict with domain, mx_host, accept_all, verified_emails,
    invalid_emails, patterns_tested, time_seconds.
    """
    async with SMTP_SEM:
        candidates = generate_patterns(first_name, last_name, domain)
        if not candidates:
            return {
                "domain": domain,
                "mx_host": None,
                "accept_all": False,
                "verified_emails": [],
                "invalid_emails": [],
                "patterns_tested": 0,
                "time_seconds": 0.0,
                "error": "no_patterns",
            }

        loop = asyncio.get_event_loop()

        mx_host = await loop.run_in_executor(None, lambda: resolve_mx(domain))
        if not mx_host:
            return {
                "domain": domain,
                "mx_host": None,
                "accept_all": False,
                "verified_emails": [],
                "invalid_emails": [],
                "patterns_tested": 0,
                "time_seconds": 0.0,
                "error": "no_mx",
            }

        result = await loop.run_in_executor(
            None,
            lambda: probe_domain(candidates, domain, mx_host, timeout=timeout),
        )
        return {
            "domain": result.domain,
            "mx_host": result.mx_host,
            "accept_all": result.accept_all,
            "verified_emails": result.verified_emails,
            "invalid_emails": result.invalid_emails,
            "patterns_tested": result.patterns_tested,
            "time_seconds": result.time_seconds,
            "error": result.error,
        }


async def verify_emails(emails: list[str]) -> list[dict[str, Any]]:
    """
    FUNCTION 2: Bulk verify existing emails. Groups by domain to reuse connections.
    Returns list of {email, domain, verified, error}.
    """
    # Group by domain
    by_domain: dict[str, list[str]] = {}
    for email in emails:
        parts = email.split("@")
        if len(parts) != 2:
            continue
        domain = parts[1].lower()
        by_domain.setdefault(domain, []).append(email)

    results: list[dict[str, Any]] = []

    async def _verify_domain_group(domain: str, email_list: list[str]) -> None:
        async with SMTP_SEM:
            loop = asyncio.get_event_loop()
            mx_host = await loop.run_in_executor(None, lambda: resolve_mx(domain))
            if not mx_host:
                for e in email_list:
                    results.append(
                        {"email": e, "domain": domain, "verified": False, "error": "no_mx"}
                    )
                return
            probe = await loop.run_in_executor(
                None,
                lambda: probe_domain(email_list, domain, mx_host),
            )
            for e in probe.verified_emails:
                results.append(
                    {
                        "email": e,
                        "domain": domain,
                        "verified": True,
                        "accept_all": probe.accept_all,
                        "error": probe.error,
                    }
                )
            for e in probe.invalid_emails:
                results.append(
                    {
                        "email": e,
                        "domain": domain,
                        "verified": False,
                        "accept_all": probe.accept_all,
                        "error": probe.error,
                    }
                )
            if probe.accept_all:
                for e in email_list:
                    results.append(
                        {
                            "email": e,
                            "domain": domain,
                            "verified": False,
                            "accept_all": True,
                            "error": None,
                        }
                    )

    await asyncio.gather(*[_verify_domain_group(d, el) for d, el in by_domain.items()])
    return results


async def discover_and_verify_batch(
    prospects: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    FUNCTION 3: Batch discover + verify for list of prospects.
    Each prospect dict: {first_name, last_name, domain, dm_email (optional)}.
    Runs discover_email concurrently (sem=20).

    Returns enriched list with smtp_verified_email, smtp_result.
    """

    async def _process(p: dict[str, Any]) -> dict[str, Any]:
        domain = p.get("domain", "")
        first_name = p.get("first_name", "")
        last_name = p.get("last_name", "")
        existing = p.get("dm_email")

        # Clean domain
        d = domain[4:] if domain.startswith("www.") else domain

        result = await discover_email(first_name, last_name, d)

        # If existing email, also verify it
        verified_existing = False
        if existing and not result.get("accept_all"):
            # Check if it appeared in verified list
            if existing in result.get("verified_emails", []):
                verified_existing = True

        smtp_email = result["verified_emails"][0] if result.get("verified_emails") else None

        return {
            **p,
            "smtp_verified_email": smtp_email,
            "smtp_existing_verified": verified_existing,
            "smtp_result": result,
        }

    return await asyncio.gather(*[_process(p) for p in prospects])
