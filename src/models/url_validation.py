"""
Contract: src/models/url_validation.py
Purpose: Pydantic models for URL validation results (Tier 0 of Scraper Waterfall)
Layer: 1 - models
Imports: exceptions only
Consumers: url_validator.py, icp_scraper.py, orchestration
"""

from typing import Optional

from pydantic import BaseModel, Field


class URLValidationResult(BaseModel):
    """
    Result of URL validation (Tier 0 of Scraper Waterfall).

    Validates URL format, follows redirects, checks DNS resolution,
    and detects parked/placeholder domains before scraping.
    """

    valid: bool = Field(
        description="Whether the URL is valid and reachable"
    )
    canonical_url: Optional[str] = Field(
        default=None,
        description="The final URL after following redirects"
    )
    redirected: bool = Field(
        default=False,
        description="Whether the URL was redirected to a different location"
    )
    redirect_chain: list[str] = Field(
        default_factory=list,
        description="List of URLs in the redirect chain"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if validation failed"
    )
    error_type: Optional[str] = Field(
        default=None,
        description="Type of error (dns_failure, timeout, ssl_error, parked_domain, invalid_format)"
    )
    status_code: Optional[int] = Field(
        default=None,
        description="HTTP status code from the final response"
    )
    is_parked: bool = Field(
        default=False,
        description="Whether the domain appears to be parked or for sale"
    )
    domain: Optional[str] = Field(
        default=None,
        description="Extracted domain from the URL"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "valid": True,
                    "canonical_url": "https://example.com/",
                    "redirected": False,
                    "redirect_chain": [],
                    "error": None,
                    "error_type": None,
                    "status_code": 200,
                    "is_parked": False,
                    "domain": "example.com"
                },
                {
                    "valid": False,
                    "canonical_url": None,
                    "redirected": False,
                    "redirect_chain": [],
                    "error": "Domain does not resolve",
                    "error_type": "dns_failure",
                    "status_code": None,
                    "is_parked": False,
                    "domain": "nonexistent-domain-12345.com"
                }
            ]
        }
    }
