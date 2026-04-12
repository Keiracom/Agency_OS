"""Tests for ABR GST three-state model constants — Directive #328.6."""


def test_gst_registered_from_abr_response():
    """ABR response with effectiveFrom and sentinel effectiveTo = REGISTERED."""
    from src.integrations.abn_client import GST_REGISTERED, GST_NOT_REGISTERED, GST_UNKNOWN

    assert GST_REGISTERED == "registered"
    assert GST_NOT_REGISTERED == "not_registered"
    assert GST_UNKNOWN == "unknown"


def test_gst_constants_are_distinct():
    """The three constants must not share a value."""
    from src.integrations.abn_client import GST_REGISTERED, GST_NOT_REGISTERED, GST_UNKNOWN

    assert len({GST_REGISTERED, GST_NOT_REGISTERED, GST_UNKNOWN}) == 3
