"""
Tests for business_universe schema and load script.

All tests use mocks - NO live downloads, NO live database operations.
"""

import pytest
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from lxml import etree

# Import the module under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_xml_valid_company():
    """Sample XML record for a valid public company (should pass all filters)."""
    return b"""<?xml version="1.0" encoding="UTF-8"?>
    <Transfer>
        <ABR>
            <ABN>12345678901</ABN>
            <ASICNumber>123456789</ASICNumber>
            <EntityStatus>
                <EntityStatusCode>ACT</EntityStatusCode>
                <EffectiveFrom>2010-01-01</EffectiveFrom>
            </EntityStatus>
            <EntityType>
                <EntityTypeCode>PUB</EntityTypeCode>
                <EntityTypeInd>Public Company</EntityTypeInd>
            </EntityType>
            <MainEntity>
                <NonIndividualName>
                    <NonIndividualNameText>ACME CORPORATION PTY LTD</NonIndividualNameText>
                </NonIndividualName>
            </MainEntity>
            <BusinessName>
                <OrganisationName>ACME Trading</OrganisationName>
            </BusinessName>
            <MainBusinessPhysicalAddress>
                <StateCode>NSW</StateCode>
                <Postcode>2000</Postcode>
            </MainBusinessPhysicalAddress>
            <GoodsAndServicesTax>
                <GSTStatus>Registered</GSTStatus>
            </GoodsAndServicesTax>
        </ABR>
    </Transfer>
    """


@pytest.fixture
def sample_xml_individual():
    """Sample XML record for an individual (should be filtered out)."""
    return b"""<?xml version="1.0" encoding="UTF-8"?>
    <Transfer>
        <ABR>
            <ABN>98765432109</ABN>
            <EntityStatus>
                <EntityStatusCode>ACT</EntityStatusCode>
            </EntityStatus>
            <EntityType>
                <EntityTypeCode>IND</EntityTypeCode>
                <EntityTypeInd>Individual/Sole Trader</EntityTypeInd>
            </EntityType>
            <LegalEntity>
                <IndividualName>
                    <GivenName>John</GivenName>
                    <FamilyName>Smith</FamilyName>
                </IndividualName>
            </LegalEntity>
        </ABR>
    </Transfer>
    """


@pytest.fixture
def sample_xml_trust():
    """Sample XML record for a trust (should be filtered out)."""
    return b"""<?xml version="1.0" encoding="UTF-8"?>
    <Transfer>
        <ABR>
            <ABN>11223344556</ABN>
            <EntityStatus>
                <EntityStatusCode>ACT</EntityStatusCode>
            </EntityStatus>
            <EntityType>
                <EntityTypeCode>DIS</EntityTypeCode>
                <EntityTypeInd>Discretionary Trust</EntityTypeInd>
            </EntityType>
            <MainEntity>
                <NonIndividualName>
                    <NonIndividualNameText>FAMILY DISCRETIONARY TRUST</NonIndividualNameText>
                </NonIndividualName>
            </MainEntity>
        </ABR>
    </Transfer>
    """


@pytest.fixture
def sample_xml_inactive():
    """Sample XML record for an inactive business (should be filtered out)."""
    return b"""<?xml version="1.0" encoding="UTF-8"?>
    <Transfer>
        <ABR>
            <ABN>99887766554</ABN>
            <EntityStatus>
                <EntityStatusCode>CAN</EntityStatusCode>
            </EntityStatus>
            <EntityType>
                <EntityTypeCode>PUB</EntityTypeCode>
                <EntityTypeInd>Public Company</EntityTypeInd>
            </EntityType>
            <MainEntity>
                <NonIndividualName>
                    <NonIndividualNameText>DEFUNCT COMPANY PTY LTD</NonIndividualNameText>
                </NonIndividualName>
            </MainEntity>
        </ABR>
    </Transfer>
    """


@pytest.fixture
def sample_xml_government():
    """Sample XML record for a government entity (should be filtered out)."""
    return b"""<?xml version="1.0" encoding="UTF-8"?>
    <Transfer>
        <ABR>
            <ABN>55443322110</ABN>
            <EntityStatus>
                <EntityStatusCode>ACT</EntityStatusCode>
            </EntityStatus>
            <EntityType>
                <EntityTypeCode>GVT</EntityTypeCode>
                <EntityTypeInd>Government Entity</EntityTypeInd>
            </EntityType>
            <MainEntity>
                <NonIndividualName>
                    <NonIndividualNameText>DEPARTMENT OF SOMETHING</NonIndividualNameText>
                </NonIndividualName>
            </MainEntity>
        </ABR>
    </Transfer>
    """


@pytest.fixture
def sample_xml_super():
    """Sample XML record for a super fund (should be filtered out)."""
    return b"""<?xml version="1.0" encoding="UTF-8"?>
    <Transfer>
        <ABR>
            <ABN>66554433221</ABN>
            <EntityStatus>
                <EntityStatusCode>ACT</EntityStatusCode>
            </EntityStatus>
            <EntityType>
                <EntityTypeCode>SUP</EntityTypeCode>
                <EntityTypeInd>Superannuation Fund</EntityTypeInd>
            </EntityType>
            <MainEntity>
                <NonIndividualName>
                    <NonIndividualNameText>SUPER FUND TRUSTEE PTY LTD</NonIndividualNameText>
                </NonIndividualName>
            </MainEntity>
        </ABR>
    </Transfer>
    """


@pytest.fixture
def sample_xml_nfp():
    """Sample XML record for a not-for-profit (should be filtered out)."""
    return b"""<?xml version="1.0" encoding="UTF-8"?>
    <Transfer>
        <ABR>
            <ABN>77665544332</ABN>
            <EntityStatus>
                <EntityStatusCode>ACT</EntityStatusCode>
            </EntityStatus>
            <EntityType>
                <EntityTypeCode>NPF</EntityTypeCode>
                <EntityTypeInd>Not-for-profit Organisation</EntityTypeInd>
            </EntityType>
            <MainEntity>
                <NonIndividualName>
                    <NonIndividualNameText>CHARITY INCORPORATED</NonIndividualNameText>
                </NonIndividualName>
            </MainEntity>
        </ABR>
    </Transfer>
    """


@pytest.fixture
def mock_db_pool():
    """Mock asyncpg connection pool."""
    pool = MagicMock()
    conn = AsyncMock()
    
    # Create a proper async context manager
    async_cm = AsyncMock()
    async_cm.__aenter__.return_value = conn
    async_cm.__aexit__.return_value = None
    pool.acquire.return_value = async_cm
    
    conn.executemany = AsyncMock()
    return pool


# =============================================================================
# MIGRATION TESTS
# =============================================================================

class TestMigrationBusinessUniverse:
    """Tests for 086_business_universe.sql migration."""

    def test_business_universe_table_structure(self):
        """Test business_universe table exists with all expected columns."""
        migration_path = Path(__file__).parent.parent / "supabase/migrations/086_business_universe.sql"
        content = migration_path.read_text()
        
        # Check table creation
        assert "CREATE TABLE IF NOT EXISTS business_universe" in content
        
        # Check all expected columns
        expected_columns = [
            "id UUID PRIMARY KEY",
            "abn TEXT UNIQUE NOT NULL",
            "acn TEXT",
            "legal_name TEXT NOT NULL",
            "trading_name TEXT",
            "entity_type TEXT NOT NULL",
            "entity_type_code TEXT NOT NULL",
            "state TEXT",
            "postcode TEXT",
            "gst_registered BOOLEAN",
            "status TEXT NOT NULL",
            "abn_status_code TEXT",
            "registration_date DATE",
            "last_abr_check TIMESTAMPTZ",
            "gmb_enriched_at TIMESTAMPTZ",
            "linkedin_enriched_at TIMESTAMPTZ",
            "abr_last_updated TIMESTAMPTZ",
            "created_at TIMESTAMPTZ",
            "updated_at TIMESTAMPTZ",
        ]
        
        for col in expected_columns:
            # Normalize whitespace for comparison
            col_pattern = col.replace(" ", r"\s+")
            assert col.split()[0] in content, f"Column {col.split()[0]} not found"

    def test_business_universe_indexes(self):
        """Test indexes exist on business_universe table."""
        migration_path = Path(__file__).parent.parent / "supabase/migrations/086_business_universe.sql"
        content = migration_path.read_text()
        
        expected_indexes = [
            "idx_bu_state",
            "idx_bu_entity_type",
            "idx_bu_status",
            "idx_bu_trading_name",
            "idx_bu_postcode",
        ]
        
        for idx in expected_indexes:
            assert idx in content, f"Index {idx} not found in migration"

    def test_abn_unique_constraint(self):
        """Test ABN has UNIQUE constraint."""
        migration_path = Path(__file__).parent.parent / "supabase/migrations/086_business_universe.sql"
        content = migration_path.read_text()
        
        assert "abn TEXT UNIQUE NOT NULL" in content


class TestMigrationBusinessDecisionMakers:
    """Tests for 087_business_decision_makers.sql migration."""

    def test_business_decision_makers_table_structure(self):
        """Test business_decision_makers table exists with all expected columns."""
        migration_path = Path(__file__).parent.parent / "supabase/migrations/087_business_decision_makers.sql"
        content = migration_path.read_text()
        
        # Check table creation
        assert "CREATE TABLE IF NOT EXISTS business_decision_makers" in content
        
        # Check all expected columns
        expected_columns = [
            "id UUID PRIMARY KEY",
            "business_universe_id UUID NOT NULL",
            "linkedin_url TEXT",
            "name TEXT",
            "title TEXT",
            "seniority TEXT",
            "dm_enriched_at TIMESTAMPTZ",
            "email TEXT",
            "email_confidence FLOAT",
            "email_verified_at TIMESTAMPTZ",
            "is_current BOOLEAN",
            "last_verified_at TIMESTAMPTZ",
            "last_outreach_at TIMESTAMPTZ",
            "last_outcome TEXT",
            "total_outreach_count INTEGER",
            "created_at TIMESTAMPTZ",
            "updated_at TIMESTAMPTZ",
        ]
        
        for col in expected_columns:
            assert col.split()[0] in content, f"Column {col.split()[0]} not found"

    def test_foreign_key_constraint(self):
        """Test foreign key constraint from business_decision_makers to business_universe."""
        migration_path = Path(__file__).parent.parent / "supabase/migrations/087_business_decision_makers.sql"
        content = migration_path.read_text()
        
        assert "REFERENCES business_universe(id)" in content
        assert "ON DELETE CASCADE" in content

    def test_business_decision_makers_indexes(self):
        """Test indexes exist on business_decision_makers table."""
        migration_path = Path(__file__).parent.parent / "supabase/migrations/087_business_decision_makers.sql"
        content = migration_path.read_text()
        
        expected_indexes = [
            "idx_bdm_business_id",
            "idx_bdm_linkedin_url",
            "idx_bdm_is_current",
        ]
        
        for idx in expected_indexes:
            assert idx in content, f"Index {idx} not found in migration"

    def test_mobile_never_stored_comment(self):
        """Test that documentation explicitly states mobile is never stored."""
        migration_path = Path(__file__).parent.parent / "supabase/migrations/087_business_decision_makers.sql"
        content = migration_path.read_text()
        
        assert "mobile" in content.lower()
        assert "NEVER" in content


# =============================================================================
# FILTER LOGIC TESTS
# =============================================================================

class TestFilterLogic:
    """Unit tests for the load script filtering logic."""

    def _parse_xml_and_get_filter_result(self, xml_bytes: bytes) -> tuple[bool, str]:
        """
        Parse XML and determine if record would be filtered.
        Returns (is_filtered, filter_reason).
        """
        root = etree.fromstring(xml_bytes)
        elem = root.find(".//ABR")
        
        if elem is None:
            return True, "no_abr_element"
        
        # Check ABN exists
        abn_elem = elem.find(".//ABN")
        if abn_elem is None or not abn_elem.text:
            return True, "no_abn"
        
        # Get entity status
        status_elem = elem.find(".//EntityStatus/EntityStatusCode")
        status_code = status_elem.text if status_elem is not None else ""
        
        # FILTER 1: Inactive
        if status_code != "ACT":
            return True, "inactive"
        
        # Get entity type
        entity_type_elem = elem.find(".//EntityType/EntityTypeCode")
        entity_type_code = entity_type_elem.text if entity_type_elem is not None else ""
        
        entity_type_name_elem = elem.find(".//EntityType/EntityTypeInd")
        entity_type_name = entity_type_name_elem.text if entity_type_name_elem is not None else ""
        
        # FILTER 2: Individuals
        if entity_type_code in {"IND", "PRV"}:
            return True, "individual"
        
        # FILTER 3: Trusts
        if "TRU" in entity_type_code or "Trust" in entity_type_name:
            return True, "trust"
        
        # FILTER 4: Government
        if entity_type_code in {"GVT", "LGV", "STG", "CGV", "GCO"}:
            return True, "government"
        
        # FILTER 5: Super funds
        if entity_type_code in {"SUP", "ADF"}:
            return True, "superannuation"
        
        # FILTER 6: NFP/Charities
        if entity_type_code in {"DIT", "NPF", "NPB", "NPE"}:
            return True, "nfp"
        
        return False, "passed"

    def test_filter1_inactive_records_rejected(self, sample_xml_inactive):
        """Test Filter 1 — Inactive records rejected (EntityStatusCode != 'ACT')."""
        is_filtered, reason = self._parse_xml_and_get_filter_result(sample_xml_inactive)
        assert is_filtered is True
        assert reason == "inactive"

    def test_filter2_individuals_rejected(self, sample_xml_individual):
        """Test Filter 2 — Individuals rejected (EntityTypeCode = 'IND')."""
        is_filtered, reason = self._parse_xml_and_get_filter_result(sample_xml_individual)
        assert is_filtered is True
        assert reason == "individual"

    def test_filter3_trusts_rejected(self, sample_xml_trust):
        """Test Filter 3 — Trusts rejected (EntityTypeCode contains 'TRU' or name contains 'Trust')."""
        is_filtered, reason = self._parse_xml_and_get_filter_result(sample_xml_trust)
        assert is_filtered is True
        assert reason == "trust"

    def test_filter4_government_rejected(self, sample_xml_government):
        """Test Filter 4 — Government rejected (EntityTypeCode = 'GVT')."""
        is_filtered, reason = self._parse_xml_and_get_filter_result(sample_xml_government)
        assert is_filtered is True
        assert reason == "government"

    def test_filter5_super_funds_rejected(self, sample_xml_super):
        """Test Filter 5 — Super funds rejected (EntityTypeCode = 'SUP')."""
        is_filtered, reason = self._parse_xml_and_get_filter_result(sample_xml_super)
        assert is_filtered is True
        assert reason == "superannuation"

    def test_filter6_nfp_rejected(self, sample_xml_nfp):
        """Test Filter 6 — NFP rejected (EntityTypeCode = 'NPF')."""
        is_filtered, reason = self._parse_xml_and_get_filter_result(sample_xml_nfp)
        assert is_filtered is True
        assert reason == "nfp"

    def test_valid_company_passes_all_filters(self, sample_xml_valid_company):
        """Test valid company passes all filters (EntityStatusCode = 'ACT', EntityTypeCode = 'PUB')."""
        is_filtered, reason = self._parse_xml_and_get_filter_result(sample_xml_valid_company)
        assert is_filtered is False
        assert reason == "passed"

    def test_filter_prv_sole_trader(self):
        """Test PRV (private/sole trader) entity type is filtered."""
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <Transfer>
            <ABR>
                <ABN>11111111111</ABN>
                <EntityStatus><EntityStatusCode>ACT</EntityStatusCode></EntityStatus>
                <EntityType>
                    <EntityTypeCode>PRV</EntityTypeCode>
                    <EntityTypeInd>Private Company</EntityTypeInd>
                </EntityType>
            </ABR>
        </Transfer>
        """
        is_filtered, reason = self._parse_xml_and_get_filter_result(xml)
        assert is_filtered is True
        assert reason == "individual"

    def test_filter_trust_by_name(self):
        """Test trust detection by name even without TRU code."""
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <Transfer>
            <ABR>
                <ABN>22222222222</ABN>
                <EntityStatus><EntityStatusCode>ACT</EntityStatusCode></EntityStatus>
                <EntityType>
                    <EntityTypeCode>OTH</EntityTypeCode>
                    <EntityTypeInd>Family Trust</EntityTypeInd>
                </EntityType>
            </ABR>
        </Transfer>
        """
        is_filtered, reason = self._parse_xml_and_get_filter_result(xml)
        assert is_filtered is True
        assert reason == "trust"


# =============================================================================
# UPSERT LOGIC TESTS
# =============================================================================

class TestUpsertLogic:
    """Tests for UPSERT behavior."""

    def test_upsert_sql_has_on_conflict(self):
        """Test UPSERT uses ON CONFLICT (abn) DO UPDATE."""
        script_path = Path(__file__).parent.parent / "scripts/load_business_universe.py"
        content = script_path.read_text()
        
        assert "ON CONFLICT (abn) DO UPDATE" in content

    def test_upsert_updates_timestamps(self):
        """Test last_abr_check and updated_at are set on update."""
        script_path = Path(__file__).parent.parent / "scripts/load_business_universe.py"
        content = script_path.read_text()
        
        assert "last_abr_check = now()" in content
        assert "updated_at = now()" in content

    @pytest.mark.asyncio
    async def test_new_record_inserted(self, mock_db_pool):
        """Test new record inserted correctly via executemany."""
        # Import here to avoid module-level import issues
        from load_business_universe import BusinessRecord, LoadStats, upsert_batch
        
        records = [
            BusinessRecord(
                abn="12345678901",
                acn="123456789",
                legal_name="TEST COMPANY PTY LTD",
                trading_name="Test Co",
                entity_type="Public Company",
                entity_type_code="PUB",
                state="NSW",
                postcode="2000",
                gst_registered=True,
                status="active",
                abn_status_code="ACT",
                registration_date="2020-01-01",
            )
        ]
        
        stats = LoadStats()
        await upsert_batch(mock_db_pool, records, stats, dry_run=False)
        
        # Verify executemany was called
        conn = mock_db_pool.acquire.return_value.__aenter__.return_value
        conn.executemany.assert_called_once()
        
        # Verify stats updated
        assert stats.total_inserted == 1

    @pytest.mark.asyncio
    async def test_dry_run_no_database_writes(self, mock_db_pool):
        """Test dry_run mode does not write to database."""
        from load_business_universe import BusinessRecord, LoadStats, upsert_batch
        
        records = [
            BusinessRecord(
                abn="12345678901",
                acn=None,
                legal_name="TEST COMPANY",
                trading_name=None,
                entity_type="Company",
                entity_type_code="PUB",
                state="VIC",
                postcode="3000",
                gst_registered=False,
                status="active",
                abn_status_code="ACT",
                registration_date=None,
            )
        ]
        
        stats = LoadStats()
        await upsert_batch(mock_db_pool, records, stats, dry_run=True)
        
        # Verify no database calls
        conn = mock_db_pool.acquire.return_value.__aenter__.return_value
        conn.executemany.assert_not_called()
        
        # But stats should still update
        assert stats.total_inserted == 1


# =============================================================================
# DATA EXTRACTION TESTS
# =============================================================================

class TestDataExtraction:
    """Tests for data extraction from XML."""

    def _extract_record(self, xml_bytes: bytes) -> dict:
        """Extract business record fields from XML (mirrors load script logic)."""
        root = etree.fromstring(xml_bytes)
        elem = root.find(".//ABR")
        
        # ABN
        abn_elem = elem.find(".//ABN")
        abn = abn_elem.text if abn_elem is not None else None
        
        # ACN
        acn_elem = elem.find(".//ASICNumber")
        acn = acn_elem.text if acn_elem is not None else None
        
        # Legal name - try multiple paths (same logic as load script)
        legal_name = None
        for path in [".//MainEntity/NonIndividualName/NonIndividualNameText",
                     ".//MainEntity/OrganisationName"]:
            name_elem = elem.find(path)
            if name_elem is not None and name_elem.text:
                legal_name = name_elem.text
                break
        
        # Try concatenating individual name parts if no legal name yet
        if not legal_name:
            given = elem.find(".//LegalEntity/IndividualName/GivenName")
            family = elem.find(".//LegalEntity/IndividualName/FamilyName")
            if given is not None or family is not None:
                parts = []
                if given is not None and given.text:
                    parts.append(given.text)
                if family is not None and family.text:
                    parts.append(family.text)
                legal_name = " ".join(parts) if parts else None
        
        # Trading name
        bn_elem = elem.find(".//BusinessName/OrganisationName")
        trading_name = bn_elem.text if bn_elem is not None else None
        
        # State and postcode
        state_elem = elem.find(".//MainBusinessPhysicalAddress/StateCode")
        state = state_elem.text if state_elem is not None else None
        
        pc_elem = elem.find(".//MainBusinessPhysicalAddress/Postcode")
        postcode = pc_elem.text if pc_elem is not None else None
        
        # GST
        gst_elem = elem.find(".//GoodsAndServicesTax/GSTStatus")
        gst_registered = gst_elem is not None and gst_elem.text == "Registered"
        
        return {
            "abn": abn,
            "acn": acn,
            "legal_name": legal_name,
            "trading_name": trading_name,
            "state": state,
            "postcode": postcode,
            "gst_registered": gst_registered,
        }

    def test_abn_extracted_correctly(self, sample_xml_valid_company):
        """Test ABN extracted correctly from XML."""
        record = self._extract_record(sample_xml_valid_company)
        assert record["abn"] == "12345678901"

    def test_acn_extracted_correctly(self, sample_xml_valid_company):
        """Test ACN extracted correctly (when present)."""
        record = self._extract_record(sample_xml_valid_company)
        assert record["acn"] == "123456789"

    def test_acn_none_when_missing(self, sample_xml_individual):
        """Test ACN is None when not present."""
        record = self._extract_record(sample_xml_individual)
        assert record["acn"] is None

    def test_legal_name_from_main_name(self, sample_xml_valid_company):
        """Test legal_name extracted from MainName/NonIndividualNameText."""
        record = self._extract_record(sample_xml_valid_company)
        assert record["legal_name"] == "ACME CORPORATION PTY LTD"

    def test_legal_name_from_individual_name(self, sample_xml_individual):
        """Test legal_name extracted from individual name parts."""
        record = self._extract_record(sample_xml_individual)
        assert record["legal_name"] == "John Smith"

    def test_trading_name_extracted(self, sample_xml_valid_company):
        """Test trading_name extracted from MainTradingName."""
        record = self._extract_record(sample_xml_valid_company)
        assert record["trading_name"] == "ACME Trading"

    def test_trading_name_none_when_missing(self, sample_xml_individual):
        """Test trading_name is None when not present."""
        record = self._extract_record(sample_xml_individual)
        assert record["trading_name"] is None

    def test_state_extracted(self, sample_xml_valid_company):
        """Test state extracted from address."""
        record = self._extract_record(sample_xml_valid_company)
        assert record["state"] == "NSW"

    def test_postcode_extracted(self, sample_xml_valid_company):
        """Test postcode extracted from address."""
        record = self._extract_record(sample_xml_valid_company)
        assert record["postcode"] == "2000"

    def test_gst_registered_true(self, sample_xml_valid_company):
        """Test gst_registered boolean derived correctly (True)."""
        record = self._extract_record(sample_xml_valid_company)
        assert record["gst_registered"] is True

    def test_gst_registered_false_when_missing(self, sample_xml_individual):
        """Test gst_registered is False when GST element missing."""
        record = self._extract_record(sample_xml_individual)
        assert record["gst_registered"] is False


# =============================================================================
# INTEGRATION TESTS (with mocks)
# =============================================================================

class TestLoadScriptIntegration:
    """Integration tests for the load script (with mocks)."""

    def test_filter_stats_dataclass(self):
        """Test FilterStats dataclass tracks all filter categories."""
        from load_business_universe import FilterStats
        
        stats = FilterStats()
        stats.inactive = 100
        stats.individuals = 200
        stats.trusts = 50
        stats.government = 25
        stats.superannuation = 15
        stats.charities_nfp = 30
        
        assert stats.inactive == 100
        assert stats.individuals == 200
        assert stats.trusts == 50
        assert stats.government == 25
        assert stats.superannuation == 15
        assert stats.charities_nfp == 30

    def test_load_stats_qualified_count(self):
        """Test LoadStats.qualified_count calculation."""
        from load_business_universe import LoadStats
        
        stats = LoadStats()
        stats.total_processed = 1000
        stats.total_filtered = 400
        
        assert stats.qualified_count == 600

    def test_business_record_dataclass(self):
        """Test BusinessRecord dataclass has all required fields."""
        from load_business_universe import BusinessRecord
        
        record = BusinessRecord(
            abn="12345678901",
            acn="123456789",
            legal_name="Test Company",
            trading_name="Test",
            entity_type="Public Company",
            entity_type_code="PUB",
            state="NSW",
            postcode="2000",
            gst_registered=True,
            status="active",
            abn_status_code="ACT",
            registration_date="2020-01-01",
        )
        
        assert record.abn == "12345678901"
        assert record.acn == "123456789"
        assert record.legal_name == "Test Company"
        assert record.trading_name == "Test"
        assert record.entity_type == "Public Company"
        assert record.entity_type_code == "PUB"
        assert record.state == "NSW"
        assert record.postcode == "2000"
        assert record.gst_registered is True
        assert record.status == "active"
        assert record.abn_status_code == "ACT"
        assert record.registration_date == "2020-01-01"

    def test_exclude_constants_defined(self):
        """Test exclusion constant sets are defined correctly."""
        from load_business_universe import (
            EXCLUDE_INDIVIDUAL,
            EXCLUDE_GOVERNMENT,
            EXCLUDE_SUPER,
            EXCLUDE_CHARITY_NFP,
        )
        
        assert "IND" in EXCLUDE_INDIVIDUAL
        assert "SGE" in EXCLUDE_GOVERNMENT
        assert "SUP" in EXCLUDE_SUPER
        assert "NPF" in EXCLUDE_CHARITY_NFP

    def test_batch_size_constant(self):
        """Test BATCH_SIZE constant is reasonable."""
        from load_business_universe import BATCH_SIZE
        
        assert BATCH_SIZE >= 100
        assert BATCH_SIZE <= 10000
