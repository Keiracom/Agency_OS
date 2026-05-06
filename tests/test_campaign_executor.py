"""Tests for campaign executor — BU → sequence → send → track loop."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from src.engines.campaign_executor import (
    CampaignExecutor,
    ProspectRecord,
)

SAMPLE_STEPS = [
    {
        "step_number": 1,
        "channel": "email",
        "delay_days": 0,
        "subject_template": "Hi {{first_name}} from {{company_name}}",
        "body_template": "Hello {{first_name}}, we noticed {{company_name}}.",
    },
    {
        "step_number": 2,
        "channel": "email",
        "delay_days": 3,
        "subject_template": "Following up, {{first_name}}",
        "body_template": "Just checking in about {{company_name}}.",
    },
]


def _prospect(email="test@dental.com.au", name="Jane Smith", company="Smile Dental"):
    return ProspectRecord(
        id="test-uuid",
        domain="dental.com.au",
        dm_email=email,
        dm_name=name,
        display_name=company,
        gmb_category="dental",
        state="NSW",
        suburb="Pymble",
    )


def test_render_template_replaces_tags():
    executor = CampaignExecutor(sequence_steps=SAMPLE_STEPS, step=1)
    prospect = _prospect()
    result = executor._render_template("Hi {{first_name}} at {{company_name}}", prospect)
    assert result == "Hi Jane at Smile Dental"


def test_render_template_aiden_tags():
    executor = CampaignExecutor(sequence_steps=SAMPLE_STEPS, step=1)
    prospect = _prospect()
    result = executor._render_template(
        "Hi {{dm_name}} at {{display_name}} in {{suburb}}, {{state}}", prospect
    )
    assert result == "Hi Jane at Smile Dental in Pymble, NSW"


def test_render_template_fallbacks_when_name_missing():
    executor = CampaignExecutor(sequence_steps=SAMPLE_STEPS, step=1)
    prospect = _prospect(name=None, company=None)
    # company=None sets display_name=None in _prospect helper
    result = executor._render_template("Hi {{first_name}} at {{company_name}}", prospect)
    assert result == "Hi there at your practice"


@pytest.mark.asyncio
async def test_dry_run_does_not_send():
    executor = CampaignExecutor(
        sequence_steps=SAMPLE_STEPS,
        step=1,
        dry_run=True,
    )
    prospect = _prospect()
    result = await executor._send_one(prospect, executor.steps[0])
    assert result.status == "dry_run"
    assert result.email == "test@dental.com.au"


@pytest.mark.asyncio
async def test_live_send_calls_resend():
    executor = CampaignExecutor(
        sequence_steps=SAMPLE_STEPS,
        step=1,
        dry_run=False,
    )
    prospect = _prospect()
    with patch(
        "src.integrations.resend_client.send_email",
        return_value={"id": "msg_123"},
    ):
        result = await executor._send_one(prospect, executor.steps[0])
    assert result.status == "sent"
    assert result.message_id == "msg_123"


def test_sequence_step_not_found_raises():
    executor = CampaignExecutor(sequence_steps=SAMPLE_STEPS, step=99)
    with pytest.raises(ValueError, match="Step 99 not found"):
        import asyncio

        asyncio.get_event_loop().run_until_complete(executor.run())


def test_summary_empty_before_run():
    executor = CampaignExecutor(sequence_steps=SAMPLE_STEPS, step=1)
    s = executor.summary()
    assert s["total"] == 0
    assert s["sent"] == 0


def test_load_sequence_from_json(tmp_path):
    seq_file = tmp_path / "test_seq.json"
    seq_file.write_text(json.dumps({"steps": SAMPLE_STEPS}))
    executor = CampaignExecutor(sequence_path=str(seq_file), step=1)
    assert len(executor.steps) == 2
    assert executor.steps[0].subject_template == SAMPLE_STEPS[0]["subject_template"]


def test_compat_shim_aiden_schema():
    """Aiden's schema uses 'emails' with 'step'/'subject'/'body_text' keys."""
    aiden_steps = [
        {
            "step": 1,
            "delay_days": 0,
            "subject": "20 mins on AU agency tooling, {{dm_name}}?",
            "body_text": "Hi {{dm_name}}, this is a test.",
            "body_html": "<p>Hi {{dm_name}}</p>",
        },
    ]
    executor = CampaignExecutor(sequence_steps=aiden_steps, step=1)
    assert len(executor.steps) == 1
    assert executor.steps[0].step_number == 1
    assert executor.steps[0].subject_template == "20 mins on AU agency tooling, {{dm_name}}?"
    assert executor.steps[0].body_template == "Hi {{dm_name}}, this is a test."


def test_compat_shim_aiden_json(tmp_path):
    """Load Aiden's 'emails' format from JSON."""
    aiden_seq = {
        "campaign_name": "test",
        "emails": [
            {
                "step": 1,
                "delay_days": 0,
                "subject": "Test subject",
                "body_text": "Test body",
            },
        ],
    }
    seq_file = tmp_path / "aiden_seq.json"
    seq_file.write_text(json.dumps(aiden_seq))
    executor = CampaignExecutor(sequence_path=str(seq_file), step=1)
    assert len(executor.steps) == 1
    assert executor.steps[0].step_number == 1
    assert executor.steps[0].subject_template == "Test subject"
    assert executor.campaign_name == "test"  # extracted from JSON


def test_campaign_name_from_json(tmp_path):
    """campaign_name is extracted from the sequence JSON when not provided."""
    seq = {"campaign_name": "dental_intro_v1", "steps": SAMPLE_STEPS}
    seq_file = tmp_path / "named.json"
    seq_file.write_text(json.dumps(seq))
    executor = CampaignExecutor(sequence_path=str(seq_file), step=1)
    assert executor.campaign_name == "dental_intro_v1"


def test_campaign_name_override(tmp_path):
    """Explicit campaign_name overrides the JSON value."""
    seq = {"campaign_name": "from_json", "steps": SAMPLE_STEPS}
    seq_file = tmp_path / "override.json"
    seq_file.write_text(json.dumps(seq))
    executor = CampaignExecutor(
        sequence_path=str(seq_file), step=1, campaign_name="explicit_override"
    )
    assert executor.campaign_name == "explicit_override"


def test_campaign_name_default():
    """campaign_name defaults to 'default' when not provided."""
    executor = CampaignExecutor(sequence_steps=SAMPLE_STEPS, step=1)
    assert executor.campaign_name == "default"
