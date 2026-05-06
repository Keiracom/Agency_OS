"""
FILE: tests/test_services/test_onboarding_pipeline.py
PURPOSE: Tests for Directive #184 pipeline fixes
  - Fix 1: promote_pool_leads_to_leads_task
  - Fix 2: bypass_gates param
  - Fix 3: demo_mode param + fixture injection

Tests use mocked Supabase sessions to avoid hitting the live DB.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest


# ============================================
# FIX 1: promote_pool_leads_to_leads_task
# ============================================


class TestPromotePoolLeadsToLeads:
    """Tests for the lead_pool → leads promotion task."""

    @pytest.mark.asyncio
    async def test_promotes_assigned_pool_leads(self):
        """Promotion inserts lead_pool rows into leads with correct column mapping."""
        client_id = uuid4()
        campaign_id = uuid4()
        pool_lead_id = uuid4()

        # Mock pool lead row
        mock_pool_lead = MagicMock()
        mock_pool_lead.id = pool_lead_id
        mock_pool_lead.client_id = client_id
        mock_pool_lead.campaign_id = campaign_id
        mock_pool_lead.email = "james.thornton@brisbanebuildco.com.au"
        mock_pool_lead.first_name = "James"
        mock_pool_lead.last_name = "Thornton"
        mock_pool_lead.title = "Managing Director"
        mock_pool_lead.phone = None
        mock_pool_lead.linkedin_url = None
        mock_pool_lead.seniority = "director"
        mock_pool_lead.personal_email = None
        mock_pool_lead.timezone = "Australia/Brisbane"
        mock_pool_lead.company_name = "Brisbane Build Co"
        mock_pool_lead.company_domain = "brisbanebuildco.com.au"
        mock_pool_lead.company_website = "https://brisbanebuildco.com.au"
        mock_pool_lead.company_linkedin_url = None
        mock_pool_lead.company_industry = "Construction"
        mock_pool_lead.company_employee_count = 42
        mock_pool_lead.company_country = "AU"
        mock_pool_lead.company_founded_year = 2008
        mock_pool_lead.company_is_hiring = None
        mock_pool_lead.enrichment_source = "apollo"
        mock_pool_lead.enrichment_confidence = 0.85

        mock_select_result = MagicMock()
        mock_select_result.fetchall.return_value = [mock_pool_lead]

        _new_lead_uuid = uuid4()
        mock_insert_result = MagicMock()
        mock_insert_result.rowcount = 1
        # Bulk INSERT SELECT uses fetchall() to collect RETURNING id rows
        mock_insert_result.fetchall.return_value = [(_new_lead_uuid,)]

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=[mock_select_result, mock_insert_result])
        mock_db.commit = AsyncMock()

        mock_session_ctx = MagicMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "src.orchestration.flows.post_onboarding_flow.get_db_session",
            return_value=mock_session_ctx,
        ):
            from src.orchestration.flows.post_onboarding_flow import (
                promote_pool_leads_to_leads_task,
            )

            result = await promote_pool_leads_to_leads_task.fn(client_id=client_id)

        assert result["success"] is True
        assert result["promoted"] == 1
        assert result["skipped"] == 0
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_skips_on_conflict(self):
        """When lead already exists (ON CONFLICT), rowcount=0 → counted as skipped."""
        client_id = uuid4()
        campaign_id = uuid4()
        pool_lead_id = uuid4()

        mock_pool_lead = MagicMock()
        mock_pool_lead.id = pool_lead_id
        mock_pool_lead.client_id = client_id
        mock_pool_lead.campaign_id = campaign_id
        mock_pool_lead.email = "existing@example.com"
        mock_pool_lead.first_name = "Existing"
        mock_pool_lead.last_name = "Lead"
        mock_pool_lead.title = None
        mock_pool_lead.phone = None
        mock_pool_lead.linkedin_url = None
        mock_pool_lead.seniority = None
        mock_pool_lead.personal_email = None
        mock_pool_lead.timezone = None
        mock_pool_lead.company_name = "Test Co"
        mock_pool_lead.company_domain = "testco.com"
        mock_pool_lead.company_website = None
        mock_pool_lead.company_linkedin_url = None
        mock_pool_lead.company_industry = "Technology"
        mock_pool_lead.company_employee_count = 10
        mock_pool_lead.company_country = "AU"
        mock_pool_lead.company_founded_year = None
        mock_pool_lead.company_is_hiring = None
        mock_pool_lead.enrichment_source = None
        mock_pool_lead.enrichment_confidence = None

        mock_select_result = MagicMock()
        mock_select_result.fetchall.return_value = [mock_pool_lead]

        # ON CONFLICT DO NOTHING → RETURNING id returns nothing → fetchall() = []
        mock_insert_result = MagicMock()
        mock_insert_result.rowcount = 0
        mock_insert_result.fetchall.return_value = []  # Bulk INSERT: no rows → skipped

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=[mock_select_result, mock_insert_result])
        mock_db.commit = AsyncMock()

        mock_session_ctx = MagicMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "src.orchestration.flows.post_onboarding_flow.get_db_session",
            return_value=mock_session_ctx,
        ):
            from src.orchestration.flows.post_onboarding_flow import (
                promote_pool_leads_to_leads_task,
            )

            result = await promote_pool_leads_to_leads_task.fn(client_id=client_id)

        assert result["success"] is True
        assert result["promoted"] == 0
        assert result["skipped"] == 1

    @pytest.mark.asyncio
    async def test_no_pool_leads_returns_zero(self):
        """When no pool leads exist for client, returns promoted=0 gracefully."""
        client_id = uuid4()

        mock_select_result = MagicMock()
        mock_select_result.fetchall.return_value = []

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_select_result)
        mock_db.commit = AsyncMock()

        mock_session_ctx = MagicMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "src.orchestration.flows.post_onboarding_flow.get_db_session",
            return_value=mock_session_ctx,
        ):
            from src.orchestration.flows.post_onboarding_flow import (
                promote_pool_leads_to_leads_task,
            )

            result = await promote_pool_leads_to_leads_task.fn(client_id=client_id)

        assert result["success"] is True
        assert result["promoted"] == 0


# ============================================
# FIX 2: bypass_gates
# ============================================


class TestBypassGates:
    """Tests for gate bypass (Directive #184 Fix 2)."""

    @pytest.mark.asyncio
    async def test_bypass_gates_skips_enforcement(self):
        """bypass_gates=True skips enforce_onboarding_gates, even if gates would fail.

        enforce_onboarding_gates is a local import inside the flow, so we track
        calls via a side-effect sentinel on the service module.
        """
        from src.orchestration.flows.post_onboarding_flow import post_onboarding_setup_flow

        called_enforce = []

        async def spy_enforce(db, client_id):
            called_enforce.append(client_id)

        with (
            patch(
                "src.services.onboarding_gate_service.enforce_onboarding_gates",
                new=spy_enforce,
            ),
            patch("src.orchestration.flows.post_onboarding_flow.verify_icp_ready_task") as mock_icp,
            patch("src.orchestration.flows.post_onboarding_flow.get_db_session") as mock_db_ctx,
        ):
            mock_db = AsyncMock()
            mock_ctx = MagicMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_db)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_db_ctx.return_value = mock_ctx

            # ICP not ready → flow exits early but gate should NOT be called
            mock_icp.return_value = {"ready": False, "error": "No ICP data"}

            result = await post_onboarding_setup_flow.fn(
                client_id=str(uuid4()),
                bypass_gates=True,
            )

            # enforce_onboarding_gates must NOT have been called with bypass=True
            assert called_enforce == [], "enforce_onboarding_gates was called but should be skipped"
            # Flow exits at ICP check (not at gate)
            assert result["success"] is False
            assert result.get("error_code") is None  # Not a gate error

    @pytest.mark.asyncio
    async def test_gates_enforced_when_bypass_false(self):
        """bypass_gates=False (default) enforces gate check and returns gate error.

        Directive #192: check_onboarding_gates is now called first to detect domain-only
        clients. Test mocks it to return partially-connected status (LinkedIn only) so
        auto-bypass doesn't trigger, then enforce_onboarding_gates raises the error.
        """
        from src.services.onboarding_gate_service import (
            LinkedInConnectionRequired,
            OnboardingGateStatus,
        )
        from src.orchestration.flows.post_onboarding_flow import post_onboarding_setup_flow

        client_id = str(uuid4())
        client_uuid = UUID(client_id)

        # Simulate: LinkedIn connected, CRM missing → auto-bypass does NOT trigger
        # (auto-bypass only triggers when BOTH are disconnected)
        partial_status = OnboardingGateStatus(
            client_id=client_uuid,
            linkedin_connected=True,
            linkedin_connected_at=None,
            linkedin_seat_count=1,
            crm_connected=False,
            crm_connected_at=None,
            crm_type=None,
            can_proceed=False,
        )

        async def mock_check_gates(db, cid):
            return partial_status

        async def raise_linkedin(db, cid):
            raise LinkedInConnectionRequired(client_uuid)

        with (
            patch(
                "src.services.onboarding_gate_service.check_onboarding_gates",
                new=mock_check_gates,
            ),
            patch(
                "src.services.onboarding_gate_service.enforce_onboarding_gates",
                new=raise_linkedin,
            ),
            patch("src.orchestration.flows.post_onboarding_flow.get_db_session") as mock_db_ctx,
        ):
            mock_db = AsyncMock()
            mock_ctx = MagicMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_db)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_db_ctx.return_value = mock_ctx

            result = await post_onboarding_setup_flow.fn(
                client_id=client_id,
                bypass_gates=False,
            )

        assert result["success"] is False
        assert result["error_code"] == "LINKEDIN_CONNECTION_REQUIRED"
        assert result["gate"] == "linkedin"

    @pytest.mark.asyncio
    async def test_domain_only_client_auto_bypass(self):
        """Directive #192: client with no LinkedIn AND no CRM auto-sets bypass_gates=True.

        When both gates are disconnected, the flow should auto-bypass and continue
        (not return success:False with a gate error).
        """
        from src.services.onboarding_gate_service import OnboardingGateStatus
        from src.orchestration.flows.post_onboarding_flow import post_onboarding_setup_flow

        client_id = str(uuid4())
        client_uuid = UUID(client_id)

        # Simulate: no LinkedIn, no CRM → auto-bypass should trigger
        no_integrations_status = OnboardingGateStatus(
            client_id=client_uuid,
            linkedin_connected=False,
            linkedin_connected_at=None,
            linkedin_seat_count=0,
            crm_connected=False,
            crm_connected_at=None,
            crm_type=None,
            can_proceed=False,
        )

        async def mock_check_gates(db, cid):
            return no_integrations_status

        with (
            patch(
                "src.services.onboarding_gate_service.check_onboarding_gates",
                new=mock_check_gates,
            ),
            patch("src.orchestration.flows.post_onboarding_flow.get_db_session") as mock_db_ctx,
            patch("src.orchestration.flows.post_onboarding_flow.verify_icp_ready_task") as mock_icp,
        ):
            mock_db = AsyncMock()
            mock_ctx = MagicMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_db)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_db_ctx.return_value = mock_ctx

            # ICP not ready → flow exits early but NOT at gate
            mock_icp.return_value = {"ready": False, "error": "No ICP"}

            result = await post_onboarding_setup_flow.fn(
                client_id=client_id,
                bypass_gates=False,  # default — should be auto-upgraded
            )

        # Gate error must NOT appear — flow bypassed gates automatically
        assert result.get("error_code") not in (
            "LINKEDIN_CONNECTION_REQUIRED",
            "CRM_CONNECTION_REQUIRED",
        ), f"Expected auto-bypass but got gate error: {result}"
        # Flow should have exited past gates (success=False at ICP or later, not gate)
        assert result["success"] is False


# ============================================
# FIX 3: demo_mode
# ============================================


class TestDemoMode:
    """Tests for demo mode (Directive #184 Fix 3)."""

    def test_demo_fixture_file_exists(self):
        """Demo leads fixture file must exist and contain >= 8 leads."""
        fixture_path = Path(__file__).parent.parent.parent / "src" / "fixtures" / "demo_leads.json"
        assert fixture_path.exists(), f"Demo fixture not found at {fixture_path}"

        with open(fixture_path) as f:
            leads = json.load(f)

        assert len(leads) >= 8, f"Expected at least 8 demo leads, got {len(leads)}"

    def test_demo_fixture_required_fields(self):
        """Each demo lead must have email, company, domain, organization_industry."""
        fixture_path = Path(__file__).parent.parent.parent / "src" / "fixtures" / "demo_leads.json"
        with open(fixture_path) as f:
            leads = json.load(f)

        required_fields = ["email", "company", "domain", "organization_industry"]
        for lead in leads:
            for field in required_fields:
                assert field in lead and lead[field], f"Demo lead missing '{field}': {lead}"

    def test_demo_fixture_au_domains(self):
        """All demo leads should have .com.au domains (Brisbane construction companies)."""
        fixture_path = Path(__file__).parent.parent.parent / "src" / "fixtures" / "demo_leads.json"
        with open(fixture_path) as f:
            leads = json.load(f)

        for lead in leads:
            assert lead["domain"].endswith(".com.au"), (
                f"Expected .com.au domain, got: {lead['domain']}"
            )
            assert lead["organization_country"] == "AU", (
                f"Expected AU country, got: {lead.get('organization_country')}"
            )

    @pytest.mark.asyncio
    async def test_demo_mode_skips_real_discovery(self):
        """demo_mode=True must NOT call pool_population_flow (source_leads_task)."""
        from src.orchestration.flows.post_onboarding_flow import post_onboarding_setup_flow

        client_id = str(uuid4())

        called_enforce = []

        async def spy_enforce(db, cid):
            called_enforce.append(cid)

        with (
            patch(
                "src.services.onboarding_gate_service.enforce_onboarding_gates",
                new=spy_enforce,
            ),
            patch(
                "src.orchestration.flows.post_onboarding_flow.verify_icp_ready_task",
                new_callable=AsyncMock,
            ) as mock_icp,
            patch(
                "src.orchestration.flows.post_onboarding_flow.generate_campaign_suggestions_task",
                new_callable=AsyncMock,
            ) as mock_suggest,
            patch(
                "src.orchestration.flows.post_onboarding_flow.create_draft_campaigns_task",
                new_callable=AsyncMock,
            ) as mock_create,
            patch(
                "src.orchestration.flows.post_onboarding_flow.source_leads_task",
                new_callable=AsyncMock,
            ) as mock_source,
            patch(
                "src.orchestration.flows.post_onboarding_flow.inject_demo_leads",
                new_callable=AsyncMock,
            ) as mock_inject,
            patch(
                "src.orchestration.flows.post_onboarding_flow.promote_pool_leads_to_leads_task",
                new_callable=AsyncMock,
            ) as mock_promote,
            patch(
                "src.orchestration.flows.post_onboarding_flow.update_onboarding_status_task",
                new_callable=AsyncMock,
            ) as mock_status,
            patch("src.orchestration.flows.post_onboarding_flow.get_db_session") as mock_db_ctx,
            patch("src.config.tiers.TIER_CONFIG", {"ignition": {"leads_per_month": 100}}),
        ):
            mock_db = AsyncMock()
            mock_ctx = MagicMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_db)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_db_ctx.return_value = mock_ctx

            campaign_id = str(uuid4())
            mock_icp.return_value = {
                "ready": True,
                "client_id": client_id,
                "company_name": "Demo Agency",
                "tier": "ignition",
                "icp": {
                    "industries": ["Construction"],
                    "titles": [],
                    "company_sizes": [],
                    "locations": [],
                    "pain_points": [],
                },
                "icp_confirmed": True,
            }
            mock_suggest.return_value = {
                "success": True,
                "suggestions": [{"name": "Construction Outreach"}],
                "ai_campaign_slots": 1,
                "custom_campaign_slots": 0,
            }
            mock_create.return_value = {
                "success": True,
                "campaigns_created": 1,
                "campaigns": [
                    {
                        "campaign_id": campaign_id,
                        "name": "Construction Outreach",
                        "allocation_pct": 100,
                    }
                ],
                "total_allocation": 100,
            }
            mock_inject.return_value = 8
            mock_promote.return_value = {"success": True, "promoted": 8, "skipped": 0, "errors": []}
            mock_status.return_value = True

            result = await post_onboarding_setup_flow.fn(
                client_id=client_id,
                demo_mode=True,
            )

        # source_leads_task should NOT have been called
        mock_source.assert_not_called()
        # inject_demo_leads SHOULD have been called
        mock_inject.assert_called_once()
        # Gates should NOT have been enforced (demo_mode implies bypass)
        assert called_enforce == [], (
            "enforce_onboarding_gates was called but demo_mode implies bypass"
        )

        assert result["success"] is True
        assert result["demo_mode"] is True
        assert result["bypass_gates"] is True
        assert result["leads_sourced"] == 8
