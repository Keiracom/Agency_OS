"""
#301 — SMTP Email Discovery + Verification
Zero cost. No external API. Pure SMTP RCPT TO probing.

Functions:
  discover_email(first_name, last_name, domain) -> dict
  verify_emails(emails: list[str]) -> list[dict]
  discover_and_verify_batch(prospects: list[dict]) -> list[dict]
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
import smtplib
import socket
import string
import time
from typing import Optional

import dns.resolver

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SMTP_TIMEOUT = 10          # seconds per connection
_SMTP_FROM = "verify@agency-os.io"
_HELO_DOMAIN = "agency-os.io"
_FAKE_LOCAL = "xq7z9fake"   # accept-all probe prefix
_BATCH_SEM = 20             # max concurrent asyncio tasks


# ---------------------------------------------------------------------------
# Pattern generation
# ---------------------------------------------------------------------------

def generate_patterns(first_name: str, last_name: str, domain: str) -> list[str]:
    """
    Generate 13 email variants for a person.
    Names are lowercased and stripped of non-alpha chars (handles hyphens, apostrophes).
    """
    def clean(s: str) -> str:
        return re.sub(r"[^a-z]", "", s.lower())

    first = clean(first_name)
    last = clean(last_name)
    f = first[:1] if first else ""
    l = last[:1] if last else ""

    if not first or not last:
        return []

    locals_list = [
        first,                       # {first}
        last,                        # {last}
        f"{first}.{last}",           # {first}.{last}
        f"{last}.{first}",           # {last}.{first}
        f"{first}{last}",            # {first}{last}
        f"{last}{first}",            # {last}{first}
        f"{f}.{last}",               # {f}.{last}
        f"{f}{last}",                # {f}{last}
        f"{first}.{l}",              # {first}.{l}
        f"{first}_{last}",           # {first}_{last}
        f"{f}_{last}",               # {f}_{last}
        f"{first}-{last}",           # {first}-{last}
        f"{f}-{last}",               # {f}-{last}
    ]
    return [f"{local}@{domain}" for local in locals_list]


# ---------------------------------------------------------------------------
# MX resolution
# ---------------------------------------------------------------------------

def resolve_mx(domain: str) -> Optional[str]:
    """Return the highest-priority MX hostname for domain, or None."""
    try:
        records = dns.resolver.resolve(domain, "MX", lifetime=8.0)
        best = sorted(records, key=lambda r: r.preference)[0]
        return str(best.exchange).rstrip(".")
    except Exception as exc:
        logger.debug("MX lookup failed for %s: %s", domain, exc)
        return None


# ---------------------------------------------------------------------------
# Core SMTP probe
# ---------------------------------------------------------------------------

def _smtp_probe(
    mx_host: str,
    domain: str,
    candidates: list[str],
    fake_addr: str,
) -> dict:
    """
    Open one SMTP connection, probe all candidates + accept-all check.
    Returns dict with verified, invalid, accept_all, error.
    """
    verified: list[str] = []
    invalid: list[str] = []
    accept_all = False
    error: Optional[str] = None

    try:
        with smtplib.SMTP(timeout=_SMTP_TIMEOUT) as smtp:
            smtp.connect(mx_host, 25)
            smtp.helo(_HELO_DOMAIN)
            smtp.mail(_SMTP_FROM)

            # Accept-all check first
            code, _ = smtp.rcpt(fake_addr)
            if code == 250:
                accept_all = True
                smtp.quit()
                return {
                    "verified": [],
                    "invalid": [],
                    "accept_all": True,
                    "error": None,
                }

            # Probe all candidates
            for addr in candidates:
                try:
                    code, _ = smtp.rcpt(addr)
                    if code == 250:
                        verified.append(addr)
                    else:
                        invalid.append(addr)
                except smtplib.SMTPServerDisconnected:
                    # Server dropped us — reconnect
                    error = "server_disconnected_mid_probe"
                    break
                except Exception as e:
                    invalid.append(addr)
                    logger.debug("RCPT TO %s failed: %s", addr, e)

            try:
                smtp.quit()
            except Exception:
                pass

    except smtplib.SMTPConnectError as e:
        error = f"connect_error: {e}"
    except smtplib.SMTPServerDisconnected as e:
        error = f"server_disconnected: {e}"
    except socket.timeout:
        error = "timeout"
    except ConnectionRefusedError:
        error = "connection_refused"
    except OSError as e:
        error = f"os_error: {e}"
    except Exception as e:
        error = f"unexpected: {e}"

    return {
        "verified": verified,
        "invalid": invalid,
        "accept_all": accept_all,
        "error": error,
    }


# ---------------------------------------------------------------------------
# FUNCTION 1: discover_email
# ---------------------------------------------------------------------------

def discover_email(first_name: str, last_name: str, domain: str) -> dict:
    """
    Discover and verify email addresses for a person via SMTP probing.

    Returns:
      {
        "domain": str,
        "mx_host": str | None,
        "accept_all": bool,
        "verified_emails": list[str],
        "invalid_emails": list[str],
        "patterns_tested": int,
        "time_seconds": float,
        "error": str | None,
      }
    """
    t0 = time.time()

    patterns = generate_patterns(first_name, last_name, domain)
    fake_addr = f"{_FAKE_LOCAL}@{domain}"

    # Resolve MX
    mx_host = resolve_mx(domain)
    if not mx_host:
        return {
            "domain": domain,
            "mx_host": None,
            "accept_all": False,
            "verified_emails": [],
            "invalid_emails": [],
            "patterns_tested": len(patterns),
            "time_seconds": round(time.time() - t0, 2),
            "error": "no_mx_record",
        }

    # SMTP probe
    result = _smtp_probe(mx_host, domain, patterns, fake_addr)

    return {
        "domain": domain,
        "mx_host": mx_host,
        "accept_all": result["accept_all"],
        "verified_emails": result["verified"],
        "invalid_emails": result["invalid"],
        "patterns_tested": len(patterns),
        "time_seconds": round(time.time() - t0, 2),
        "error": result["error"],
    }


# ---------------------------------------------------------------------------
# FUNCTION 2: verify_emails
# ---------------------------------------------------------------------------

def verify_emails(emails: list[str]) -> list[dict]:
    """
    Bulk verify existing email addresses.
    Groups by domain — one SMTP connection per domain.

    Returns list of:
      {"email": str, "verified": bool, "accept_all": bool, "error": str|None}
    """
    # Group by domain
    by_domain: dict[str, list[str]] = {}
    for email in emails:
        if "@" not in email:
            continue
        _, domain = email.rsplit("@", 1)
        by_domain.setdefault(domain, []).append(email)

    results: list[dict] = []

    for domain, domain_emails in by_domain.items():
        fake_addr = f"{_FAKE_LOCAL}@{domain}"
        mx_host = resolve_mx(domain)
        if not mx_host:
            for email in domain_emails:
                results.append({
                    "email": email,
                    "verified": False,
                    "accept_all": False,
                    "error": "no_mx_record",
                })
            continue

        probe = _smtp_probe(mx_host, domain, domain_emails, fake_addr)
        for email in domain_emails:
            results.append({
                "email": email,
                "verified": email in probe["verified"],
                "accept_all": probe["accept_all"],
                "error": probe["error"],
            })

    return results


# ---------------------------------------------------------------------------
# FUNCTION 3: discover_and_verify_batch (async)
# ---------------------------------------------------------------------------

async def _discover_one(
    prospect: dict,
    sem: asyncio.Semaphore,
) -> dict:
    """Run discover_email in a thread pool (SMTP is blocking)."""
    async with sem:
        loop = asyncio.get_event_loop()
        first = prospect.get("first_name", "")
        last = prospect.get("last_name", "")
        domain = prospect.get("domain", "")
        result = await loop.run_in_executor(
            None, discover_email, first, last, domain
        )
        return {**prospect, "smtp_result": result}


async def discover_and_verify_batch(prospects: list[dict]) -> list[dict]:
    """
    Concurrently discover emails for a list of prospects.
    Input: list of {first_name, last_name, domain, ...any other fields}
    Output: same list with smtp_result added.
    Semaphore: _BATCH_SEM concurrent tasks (default 20).
    """
    sem = asyncio.Semaphore(_BATCH_SEM)
    tasks = [_discover_one(p, sem) for p in prospects]
    return await asyncio.gather(*tasks)
