"""Regression tests for domain keyword extraction — Directive #328.3b."""
import pytest
from src.pipeline.free_enrichment import FreeEnrichment


class TestDomainKeywordExtraction:
    def test_theavenuedental(self):
        result = FreeEnrichment._extract_domain_keywords("theavenuedental.com.au")
        assert "avenue" in result or "dental" in result
        assert "dental" in result
        # Must NOT return single unsplit token
        assert "theavenuedental" not in result

    def test_meltondentalhouse(self):
        result = FreeEnrichment._extract_domain_keywords("meltondentalhouse.com.au")
        assert "melton" in result
        assert "dental" in result
        # Must NOT produce garbage splits
        assert "meltondent" not in result
        assert "lhouse" not in result

    def test_sydneycriminallawyers_with_www(self):
        result = FreeEnrichment._extract_domain_keywords("www.sydneycriminallawyers.com.au")
        assert "sydney" in result
        assert "lawyers" in result
        # www must be stripped
        assert "www" not in result

    def test_glenferriedental(self):
        result = FreeEnrichment._extract_domain_keywords("glenferriedental.com.au")
        assert "glenferrie" in result
        assert "dental" in result

    def test_dentistsatpymble_backward_compat(self):
        """Existing test case from original implementation."""
        result = FreeEnrichment._extract_domain_keywords("dentistsatpymble.com.au")
        assert "dentists" in result or "dentist" in result
        assert "pymble" in result

    def test_hyphenated_domain(self):
        result = FreeEnrichment._extract_domain_keywords("happy-dentistry.com.au")
        assert "happy" in result
        assert "dentistry" in result

    def test_www_stripped(self):
        """www prefix must not appear in results."""
        result = FreeEnrichment._extract_domain_keywords("www.example.com.au")
        assert "www" not in result

    def test_returns_list(self):
        result = FreeEnrichment._extract_domain_keywords("test.com.au")
        assert isinstance(result, list)
