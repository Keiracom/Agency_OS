"""Tests for Spider HTML ad tag detection — Directive #291."""
from src.pipeline.free_enrichment import FreeEnrichment


def test_aw_tag_detected():
    html = '<script>gtag("config","AW-974027818");</script>'
    r = FreeEnrichment._detect_ad_tags(html)
    assert r["has_google_ads_tag"] is True
    assert r["has_any_ad_tag"] is True


def test_remarketing_detected():
    html = '<script src="https://googleads.g.doubleclick.net/pagead/viewthroughconversion/123/"></script>'
    r = FreeEnrichment._detect_ad_tags(html)
    assert r["has_google_ads_tag"] is True


def test_meta_pixel_detected():
    html = "fbq('init','1234567');"
    r = FreeEnrichment._detect_ad_tags(html)
    assert r["has_meta_pixel"] is True
    assert r["has_any_ad_tag"] is True


def test_meta_pixel_facebook_connect():
    html = '<script src="https://connect.facebook.net/en_US/fbevents.js"></script>'
    r = FreeEnrichment._detect_ad_tags(html)
    assert r["has_meta_pixel"] is True


def test_empty_html_returns_all_false():
    r = FreeEnrichment._detect_ad_tags("")
    assert r == {"has_google_ads_tag": False, "has_meta_pixel": False, "has_any_ad_tag": False}


def test_no_tags_in_clean_html():
    html = "<html><body><p>Hello world</p></body></html>"
    r = FreeEnrichment._detect_ad_tags(html)
    assert r["has_any_ad_tag"] is False
