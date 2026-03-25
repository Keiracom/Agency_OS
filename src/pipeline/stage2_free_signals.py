# FILE: src/pipeline/stage2_free_signals.py
# PURPOSE: Stage 2 — Free signal collection (pixel audit + Yellow Pages)
# PIPELINE STAGE: 1 → 2
# DEPENDENCIES: httpx, BeautifulSoup, asyncpg
# DIRECTIVE: #249

from __future__ import annotations

import json
import re
import urllib.parse

import httpx


class Stage2FreeSignals:
    def __init__(
        self,
        db,  # asyncpg connection or pool
        jina_api_key: str | None = None,  # reserved for future rate limit bypass
    ) -> None:
        self.db = db
        self.jina_api_key = jina_api_key
        self._http: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                timeout=10.0,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (compatible; AgencyOS/1.0)"},
            )
        return self._http

    async def close(self) -> None:
        if self._http and not self._http.is_closed:
            await self._http.aclose()

    async def run(self, batch_size: int = 50) -> dict:
        """
        Process BU rows at pipeline_stage=1, pipeline_status='discovered'.
        Runs pixel audit + YP check. Advances to stage=2.
        Returns: processed, pixel_audit_success, yp_found, errors
        """
        processed = 0
        pixel_audit_success = 0
        yp_found = 0
        errors = []

        db = self.db

        # SELECT batch with row lock
        rows = await db.fetch(
            """
            SELECT id, display_name, website, domain, suburb, state, postcode
            FROM business_universe
            WHERE pipeline_stage = 1 AND pipeline_status = 'discovered'
            LIMIT $1
            FOR UPDATE SKIP LOCKED
            """,
            batch_size,
        )

        for row in rows:
            signals: dict = {}
            error = None
            try:
                # Part A: Pixel audit
                if row["website"] or row["domain"]:
                    url = row["website"] or f"https://{row['domain']}"
                    audit = await self._pixel_audit(url)
                    signals.update(audit)
                    if audit.get("signal_checked_at") is not None or any(
                        k != "signal_checked_at" for k in audit
                    ):
                        pixel_audit_success += 1

                # Part B: YP check
                yp = await self._yp_check(
                    row["display_name"], row["suburb"], row["state"]
                )
                signals.update(yp)
                if yp.get("listed_on_yp"):
                    yp_found += 1

            except Exception as e:
                error = str(e)
                errors.append({"id": str(row["id"]), "error": error})

            # Always advance stage — failed signals are still a signal
            signals["signal_checked_at"] = "NOW()"
            signals["signal_source"] = "pixel_audit+yp"
            signals["pipeline_stage"] = 2
            signals["pipeline_status"] = "signals_collected"

            await self._update_bu_row(row["id"], signals)
            processed += 1

        return {
            "processed": processed,
            "pixel_audit_success": pixel_audit_success,
            "yp_found": yp_found,
            "errors": errors,
        }

    async def _pixel_audit(self, url: str) -> dict:
        """Fetch website and extract pixel/tracking/social signals."""
        html: str | None = None

        # Step 1: Try direct fetch first
        try:
            client = await self._get_client()
            resp = await client.get(url)
            html = resp.text
        except Exception:
            html = None

        # Step 2: If direct fetch fails, try Jina fallback
        if html is None:
            try:
                client = await self._get_client()
                jina_url = f"https://r.jina.ai/{url}"
                resp = await client.get(
                    jina_url,
                    headers={"Accept": "text/markdown", "X-No-Cache": "true"},
                )
                if resp.status_code == 200 and len(resp.text) >= 200:
                    html = resp.text
            except Exception:
                html = None

        # Step 3: If both fail, return empty signals
        if html is None:
            return {"signal_checked_at": None}

        # Step 4: Parse HTML/markdown for signals
        signals: dict = {}
        if html:
            h = html.lower()
            signals["has_google_analytics"] = any(
                x in h
                for x in [
                    "gtag.js",
                    "analytics.js",
                    "ga.js",
                    "google-analytics.com",
                    "googletagmanager.com/gtag",
                    "/gtm.js",
                ]
            ) or bool(re.search(r"\b(G-[A-Z0-9]+|UA-\d+)", html))

            signals["has_google_ads"] = any(
                x in h
                for x in [
                    "googleads.g.doubleclick.net",
                    "conversion.js",
                    "gclid",
                    "google_conversion_id",
                ]
            ) or bool(re.search(r"\bAW-\d+", html))

            signals["has_facebook_pixel"] = any(
                x in h for x in ["connect.facebook.net", "fbq(", "fbevents.js"]
            )

            signals["has_conversion_tracking"] = (
                signals.get("has_google_analytics")
                or signals.get("has_google_ads")
                or signals.get("has_facebook_pixel", False)
            )

            signals["is_mobile_responsive"] = '<meta name="viewport"' in html.lower()

            signals["has_booking_system"] = any(
                x in h
                for x in [
                    "calendly.com",
                    "acuityscheduling",
                    "hubspot meetings",
                    "bookings.",
                    "/book-now",
                    "/schedule",
                    "oncehub.com",
                    "tidycal.com",
                ]
            )

            # Copyright year
            year_match = re.findall(
                r"©\s*(\d{4})|copyright\s+(\d{4})", html.lower()
            )
            years = [int(y[0] or y[1]) for y in year_match if (y[0] or y[1])]
            signals["site_copyright_year"] = max(years) if years else None

            # Social URLs
            for pattern, key in [
                (
                    r'href=["\']([^"\']*facebook\.com/(?!sharer|dialog|tr\?|plugins)[^"\']+)["\']',
                    "social_facebook_url",
                ),
                (
                    r'href=["\']([^"\']*instagram\.com/[^"\']+)["\']',
                    "social_instagram_url",
                ),
                (
                    r'href=["\']([^"\']*linkedin\.com/company/[^"\']+)["\']',
                    "social_linkedin_company_url",
                ),
                (
                    r'href=["\']([^"\']*(?:twitter|x)\.com/[^"\']+)["\']',
                    "social_twitter_url",
                ),
            ]:
                m = re.search(pattern, html, re.IGNORECASE)
                if m:
                    signals[key] = m.group(1).split('"')[0].split("'")[0]

        return signals

    async def _yp_check(
        self,
        name: str,
        suburb: str | None,
        state: str | None,
    ) -> dict:
        """Check Yellow Pages listing via Jina Reader."""
        # Construct YP search URL
        slug_name = urllib.parse.quote(name.lower().replace(" ", "-"))
        slug_loc = (
            f"{(suburb or '').lower().replace(' ', '-')}-{(state or '').lower()}"
        )
        yp_url = f"https://www.yellowpages.com.au/find/{slug_name}/{slug_loc}"
        jina_url = f"https://r.jina.ai/{yp_url}"

        try:
            client = await self._get_client()
            resp = await client.get(
                jina_url,
                headers={"Accept": "text/markdown", "X-No-Cache": "true"},
            )
            content = resp.text if resp.status_code == 200 else ""
        except Exception:
            content = ""

        if not content:
            return {"listed_on_yp": False}

        # Try JSON format first
        data = None
        listed = False
        try:
            data = json.loads(content)
            # JSON format: look for results
            listed = bool(data.get("results") or data.get("listings"))
            # Count /bpp/ links in raw content as fallback
        except (json.JSONDecodeError, AttributeError):
            data = None

        # Count /bpp/ occurrences (each = a paid listing link per gotcha)
        bpp_count = content.count("/bpp/")
        listed_on_yp = bpp_count > 0 or (data is not None and listed)

        # Ad signal: standalone "Ad" line in pipe-delimited or markdown
        yp_advertiser = bool(
            re.search(r"(?:^|\|)\s*Ad\s*(?:\||$)", content, re.MULTILINE)
        )

        # Years in business: look for "X years in business" pattern
        years_match = re.search(
            r"(\d+)\s+years?\s+in\s+business", content, re.IGNORECASE
        )
        yp_years = int(years_match.group(1)) if years_match else None

        return {
            "listed_on_yp": listed_on_yp,
            "yp_advertiser": yp_advertiser,
            "yp_years_in_business": yp_years,
        }

    async def _update_bu_row(self, row_id, signals: dict) -> None:
        """Dynamically build and execute UPDATE for business_universe row."""
        # Handle NOW() specially
        set_clauses = []
        values = []
        param_idx = 1

        for key, val in signals.items():
            if val == "NOW()":
                set_clauses.append(f"{key} = NOW()")
            else:
                set_clauses.append(f"{key} = ${param_idx}")
                values.append(val)
                param_idx += 1

        values.append(row_id)
        await self.db.execute(
            f"UPDATE business_universe SET {', '.join(set_clauses)} WHERE id = ${param_idx}",
            *values,
        )
