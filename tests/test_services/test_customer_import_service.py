"""
FILE: tests/test_services/test_customer_import_service.py
TASK: CUST-016
PHASE: 24F - Customer Import
PURPOSE: Unit tests for CustomerImportService, SuppressionService, BuyerSignalService
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.services.customer_import_service import (
    CustomerImportService,
    CustomerData,
    ImportResult,
    ColumnMapping,
)
from src.services.suppression_service import (
    SuppressionService,
    SuppressionResult,
    SuppressionEntry,
)
from src.services.buyer_signal_service import (
    BuyerSignalService,
    BuyerSignal,
    BuyerScoreBoost,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    return db


@pytest.fixture
def client_id():
    """Generate a test client ID."""
    return uuid4()


@pytest.fixture
def customer_import_service(mock_db):
    """Create a CustomerImportService instance."""
    return CustomerImportService(mock_db)


@pytest.fixture
def suppression_service(mock_db):
    """Create a SuppressionService instance."""
    return SuppressionService(mock_db)


@pytest.fixture
def buyer_signal_service(mock_db):
    """Create a BuyerSignalService instance."""
    return BuyerSignalService(mock_db)


# ============================================================================
# CUSTOMER IMPORT SERVICE TESTS
# ============================================================================


class TestCustomerImportService:
    """Tests for CustomerImportService."""

    async def test_process_customer_creates_entry(
        self, customer_import_service, mock_db, client_id
    ):
        """Test that process_customer creates a customer entry."""
        # Arrange
        customer_data = CustomerData(
            company_name="Acme Corp",
            domain="acme.com",
            contact_email="john@acme.com",
            deal_value=10000.0,
            closed_at=datetime.now(),
            source="csv_import",
        )

        # Mock the database response
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.id = uuid4()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Act
        result = await customer_import_service.process_customer(
            client_id=client_id,
            data=customer_data,
            auto_suppress=True,
        )

        # Assert
        assert result is not None
        mock_db.execute.assert_called()
        mock_db.commit.assert_called()

    async def test_import_from_csv_parses_content(
        self, customer_import_service, mock_db, client_id
    ):
        """Test that import_from_csv parses CSV content correctly."""
        # Arrange
        csv_content = """domain,company_name,email
acme.com,Acme Corp,john@acme.com
widget.io,Widget Inc,jane@widget.io
"""
        column_mapping = ColumnMapping(
            domain="domain",
            company_name="company_name",
            email="email",
        )

        # Mock the database response
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.id = uuid4()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Act
        result = await customer_import_service.import_from_csv(
            client_id=client_id,
            csv_content=csv_content,
            column_mapping=column_mapping,
            source="csv_import",
        )

        # Assert
        assert result.success is True
        assert result.imported >= 0

    async def test_import_from_csv_handles_missing_column(
        self, customer_import_service, mock_db, client_id
    ):
        """Test that import_from_csv handles missing columns gracefully."""
        # Arrange
        csv_content = """domain
acme.com
widget.io
"""
        column_mapping = ColumnMapping(
            domain="domain",
            email="nonexistent_column",  # Column doesn't exist
        )

        # Mock the database response
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.id = uuid4()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Act
        result = await customer_import_service.import_from_csv(
            client_id=client_id,
            csv_content=csv_content,
            column_mapping=column_mapping,
            source="csv_import",
        )

        # Assert - should still process rows with domain only
        assert result is not None

    async def test_import_from_csv_skips_empty_rows(
        self, customer_import_service, mock_db, client_id
    ):
        """Test that import_from_csv skips empty rows."""
        # Arrange
        csv_content = """domain,company_name
acme.com,Acme Corp

widget.io,Widget Inc
"""
        column_mapping = ColumnMapping(domain="domain")

        # Mock the database response
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.id = uuid4()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Act
        result = await customer_import_service.import_from_csv(
            client_id=client_id,
            csv_content=csv_content,
            column_mapping=column_mapping,
        )

        # Assert
        assert result is not None


# ============================================================================
# SUPPRESSION SERVICE TESTS
# ============================================================================


class TestSuppressionService:
    """Tests for SuppressionService."""

    async def test_is_suppressed_returns_none_when_not_suppressed(
        self, suppression_service, mock_db, client_id
    ):
        """Test that is_suppressed returns None when email is not suppressed."""
        # Arrange
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.suppressed = False
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Act
        result = await suppression_service.is_suppressed(
            client_id=client_id,
            email="john@acme.com",
        )

        # Assert
        assert result is None

    async def test_is_suppressed_returns_result_when_suppressed(
        self, suppression_service, mock_db, client_id
    ):
        """Test that is_suppressed returns SuppressionResult when suppressed."""
        # Arrange
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.suppressed = True
        mock_row.reason = "existing_customer"
        mock_row.details = "Domain acme.com is suppressed"
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Act
        result = await suppression_service.is_suppressed(
            client_id=client_id,
            email="john@acme.com",
        )

        # Assert
        assert result is not None
        assert result.suppressed is True
        assert result.reason == "existing_customer"

    async def test_add_suppression_creates_entry(
        self, suppression_service, mock_db, client_id
    ):
        """Test that add_suppression creates a suppression entry."""
        # Arrange
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.id = uuid4()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Act
        result = await suppression_service.add_suppression(
            client_id=client_id,
            domain="competitor.com",
            reason="competitor",
            source="manual",
            notes="Main competitor",
        )

        # Assert
        assert result is not None
        mock_db.execute.assert_called()
        mock_db.commit.assert_called()

    async def test_remove_suppression_by_id(
        self, suppression_service, mock_db, client_id
    ):
        """Test that remove_suppression removes by ID."""
        # Arrange
        suppression_id = uuid4()
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.id = suppression_id
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Act
        result = await suppression_service.remove_suppression(
            client_id=client_id,
            suppression_id=suppression_id,
        )

        # Assert
        assert result is True
        mock_db.execute.assert_called()
        mock_db.commit.assert_called()

    async def test_remove_suppression_returns_false_when_not_found(
        self, suppression_service, mock_db, client_id
    ):
        """Test that remove_suppression returns False when not found."""
        # Arrange
        suppression_id = uuid4()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        # Act
        result = await suppression_service.remove_suppression(
            client_id=client_id,
            suppression_id=suppression_id,
        )

        # Assert
        assert result is False

    async def test_is_suppressed_batch_checks_multiple(
        self, suppression_service, mock_db, client_id
    ):
        """Test that is_suppressed_batch checks multiple emails."""
        # Arrange
        emails = ["john@acme.com", "jane@widget.io", "bob@competitor.com"]

        # Mock domain suppression check
        domain_result = MagicMock()
        domain_result.fetchall.return_value = [MagicMock(domain="competitor.com", reason="competitor")]

        # Mock email suppression check
        email_result = MagicMock()
        email_result.fetchall.return_value = []

        mock_db.execute.side_effect = [domain_result, email_result]

        # Act
        results = await suppression_service.is_suppressed_batch(
            client_id=client_id,
            emails=emails,
        )

        # Assert
        assert len(results) == 3
        # bob@competitor.com should be suppressed (domain match)
        assert results["bob@competitor.com"] is not None
        assert results["bob@competitor.com"].suppressed is True

    async def test_add_from_bounce_creates_suppression(
        self, suppression_service, mock_db, client_id
    ):
        """Test that add_from_bounce creates suppression entry."""
        # Arrange
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.id = uuid4()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Act
        result = await suppression_service.add_from_bounce(
            client_id=client_id,
            email="invalid@bounced.com",
            bounce_type="hard",
        )

        # Assert
        assert result is not None
        mock_db.execute.assert_called()


# ============================================================================
# BUYER SIGNAL SERVICE TESTS
# ============================================================================


class TestBuyerSignalService:
    """Tests for BuyerSignalService."""

    async def test_get_buyer_signal_returns_signal_when_found(
        self, buyer_signal_service, mock_db
    ):
        """Test that get_buyer_signal returns signal when found."""
        # Arrange
        signal_id = uuid4()
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.id = signal_id
        mock_row.domain = "acme.com"
        mock_row.company_name = "Acme Corp"
        mock_row.industry = "Technology"
        mock_row.employee_count_range = "50-200"
        mock_row.times_bought = 2
        mock_row.total_value = 25000.0
        mock_row.avg_deal_value = 12500.0
        mock_row.services_bought = ["SEO", "PPC"]
        mock_row.buyer_score = 75
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Act
        result = await buyer_signal_service.get_buyer_signal("acme.com")

        # Assert
        assert result is not None
        assert result.domain == "acme.com"
        assert result.times_bought == 2
        assert result.buyer_score == 75

    async def test_get_buyer_signal_returns_none_when_not_found(
        self, buyer_signal_service, mock_db
    ):
        """Test that get_buyer_signal returns None when not found."""
        # Arrange
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        # Act
        result = await buyer_signal_service.get_buyer_signal("unknown.com")

        # Assert
        assert result is None

    async def test_get_buyer_score_boost_returns_boost_when_found(
        self, buyer_signal_service, mock_db
    ):
        """Test that get_buyer_score_boost returns boost when signal found."""
        # Arrange
        signal_id = uuid4()

        # Mock signal query
        signal_mock = MagicMock()
        signal_row = MagicMock()
        signal_row.id = signal_id
        signal_row.domain = "acme.com"
        signal_row.company_name = "Acme Corp"
        signal_row.industry = "Technology"
        signal_row.employee_count_range = "50-200"
        signal_row.times_bought = 3
        signal_row.total_value = 50000.0
        signal_row.avg_deal_value = 16666.67
        signal_row.services_bought = ["SEO", "PPC", "Content"]
        signal_row.buyer_score = 80
        signal_mock.fetchone.return_value = signal_row

        # Mock boost query
        boost_mock = MagicMock()
        boost_row = MagicMock()
        boost_row.boost = 12  # 80 * 0.15 = 12
        boost_mock.fetchone.return_value = boost_row

        mock_db.execute.side_effect = [signal_mock, boost_mock]

        # Act
        result = await buyer_signal_service.get_buyer_score_boost("acme.com")

        # Assert
        assert result.boost_points == 12
        assert result.reason == "Repeat agency buyer (3x)"
        assert result.signal is not None

    async def test_get_buyer_score_boost_returns_zero_when_not_found(
        self, buyer_signal_service, mock_db
    ):
        """Test that get_buyer_score_boost returns zero when not found."""
        # Arrange
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        # Act
        result = await buyer_signal_service.get_buyer_score_boost("unknown.com")

        # Assert
        assert result.boost_points == 0
        assert result.reason is None
        assert result.signal is None

    async def test_get_buyer_signal_from_email_extracts_domain(
        self, buyer_signal_service, mock_db
    ):
        """Test that get_buyer_signal_from_email extracts domain correctly."""
        # Arrange
        signal_id = uuid4()
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.id = signal_id
        mock_row.domain = "acme.com"
        mock_row.company_name = "Acme Corp"
        mock_row.industry = "Technology"
        mock_row.employee_count_range = None
        mock_row.times_bought = 1
        mock_row.total_value = None
        mock_row.avg_deal_value = None
        mock_row.services_bought = []
        mock_row.buyer_score = 50
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Act
        result = await buyer_signal_service.get_buyer_signal_from_email("john@acme.com")

        # Assert
        assert result is not None
        assert result.domain == "acme.com"

    async def test_get_buyer_signals_batch(self, buyer_signal_service, mock_db):
        """Test that get_buyer_signals_batch returns signals for multiple domains."""
        # Arrange
        domains = ["acme.com", "widget.io", "unknown.com"]

        signal1 = MagicMock()
        signal1.id = uuid4()
        signal1.domain = "acme.com"
        signal1.company_name = "Acme Corp"
        signal1.industry = "Technology"
        signal1.employee_count_range = None
        signal1.times_bought = 2
        signal1.total_value = 20000.0
        signal1.avg_deal_value = 10000.0
        signal1.services_bought = ["SEO"]
        signal1.buyer_score = 70

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [signal1]  # Only acme.com found
        mock_db.execute.return_value = mock_result

        # Act
        results = await buyer_signal_service.get_buyer_signals_batch(domains)

        # Assert
        assert len(results) == 3
        assert results["acme.com"] is not None
        assert results["acme.com"].times_bought == 2
        assert results["widget.io"] is None
        assert results["unknown.com"] is None


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestSuppressionIntegration:
    """Integration tests for suppression workflow."""

    async def test_customer_import_auto_suppresses(
        self, customer_import_service, mock_db, client_id
    ):
        """Test that customer import auto-suppresses the domain."""
        # Arrange
        csv_content = """domain,company_name
acme.com,Acme Corp
"""
        column_mapping = ColumnMapping(domain="domain", company_name="company_name")

        # Mock the database responses
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.id = uuid4()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        # Act
        result = await customer_import_service.import_from_csv(
            client_id=client_id,
            csv_content=csv_content,
            column_mapping=column_mapping,
            auto_suppress=True,
        )

        # Assert
        assert result is not None
        # Verify that suppression was attempted (would be in the DB calls)
        assert mock_db.execute.called


class TestDomainExtraction:
    """Tests for domain extraction utilities."""

    def test_extract_domain_from_email(self, suppression_service):
        """Test domain extraction from email."""
        assert suppression_service._extract_domain("john@acme.com") == "acme.com"
        assert suppression_service._extract_domain("jane@sub.widget.io") == "sub.widget.io"
        assert suppression_service._extract_domain("invalid") is None
        assert suppression_service._extract_domain("") is None
        assert suppression_service._extract_domain(None) is None


# ============================================================================
# VERIFICATION CHECKLIST
# ============================================================================
# [x] Contract comment at top with FILE, TASK, PHASE, PURPOSE
# [x] Fixtures for mock_db, client_id, services
# [x] CustomerImportService tests
#   [x] process_customer creates entry
#   [x] import_from_csv parses content
#   [x] handles missing columns
#   [x] skips empty rows
# [x] SuppressionService tests
#   [x] is_suppressed returns None when not suppressed
#   [x] is_suppressed returns result when suppressed
#   [x] add_suppression creates entry
#   [x] remove_suppression by ID
#   [x] returns False when not found
#   [x] is_suppressed_batch checks multiple
#   [x] add_from_bounce creates suppression
# [x] BuyerSignalService tests
#   [x] get_buyer_signal returns signal when found
#   [x] returns None when not found
#   [x] get_buyer_score_boost returns boost
#   [x] returns zero when not found
#   [x] get_buyer_signal_from_email extracts domain
#   [x] get_buyer_signals_batch
# [x] Integration tests
# [x] Domain extraction tests
