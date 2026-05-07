"""tests/integrations/test_abn_client_live.py — live smoke for ABR lookup.

Phase 1a pre-cohort sweep — closes audit checklist item #7 (template § A in
docs/audits/2026-05-07_connector_live_smoke_audit.md) for abn_client.py.

One real call to the Australian Business Register (ABR) ABN Lookup web
service. Free per-call (registered GUID, no per-call cost). The point is
to fail loudly when the upstream URL changes, the SOAP/JSON contract
drifts, or the ABN_LOOKUP_GUID is invalid — not to validate behaviour
(which mocks already cover).
"""

from __future__ import annotations

import os

import pytest

pytestmark = [pytest.mark.live, pytest.mark.asyncio]


_TEST_ABN = os.environ.get(
    "ABN_LIVE_SMOKE_ABN",
    # Atlassian Pty Ltd — known-stable, registered ASIC business, AU resident.
    "33051775556",
)


@pytest.mark.skipif(
    not os.environ.get("ABN_LOOKUP_GUID"),
    reason="ABN_LOOKUP_GUID env var unset; live smoke skipped",
)
async def test_abn_search_live_smoke():
    """Real ABR lookup of a known-stable AU-ABN.

    Asserts the response is well-formed (found=True, business_name
    populated) so a URL/contract regression fails this test loudly.
    """
    from src.integrations.abn_client import get_abn_client

    client = get_abn_client()
    try:
        result = await client.search_by_abn(_TEST_ABN)
    finally:
        await client.close()

    assert result is not None, "ABR lookup returned None"
    assert result.get("found") is True, (
        f"ABR did not find ABN {_TEST_ABN}: {result!r}"
    )
    business_name = result.get("business_name")
    assert business_name, (
        f"business_name empty for {_TEST_ABN} — schema may have drifted: "
        f"{result!r}"
    )
    # ABN comes back formatted (e.g. '33 051 775 556'); compare digits-only.
    returned_digits = "".join(ch for ch in str(result.get("abn", "")) if ch.isdigit())
    assert returned_digits == _TEST_ABN, (
        f"echoed ABN {returned_digits!r} != {_TEST_ABN!r}"
    )
    assert result.get("source") == "abn_lookup"
