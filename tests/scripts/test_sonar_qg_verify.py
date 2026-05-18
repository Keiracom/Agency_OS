"""Tests for scripts/orchestrator/sonar_qg_verify.py (KEI-189).

All network calls are mocked — no live SonarCloud requests.
Covers 11 scenarios including the real-world PR #981 shape.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "orchestrator"))

from sonar_qg_verify import (  # noqa: E402,I001
    SONARCLOUD_BASE,
    SOURCE_DOC_ISSUES,
    SOURCE_DOC_QG,
    SonarVerifyResult,
    format_review_brief_sonar_block,
    verify_pr,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_http(issues_payload: dict, qg_payload: dict) -> MagicMock:
    """Return an http_client mock that returns the given payloads in order."""
    client = MagicMock()
    resp1 = MagicMock()
    resp1.raise_for_status = MagicMock()
    resp1.json.return_value = issues_payload

    resp2 = MagicMock()
    resp2.raise_for_status = MagicMock()
    resp2.json.return_value = qg_payload

    client.get.side_effect = [resp1, resp2]
    return client


def _ok_qg(conditions: list | None = None) -> dict:
    return {"projectStatus": {"status": "OK", "conditions": conditions or []}}


def _error_qg(conditions: list | None = None) -> dict:
    return {
        "projectStatus": {
            "status": "ERROR",
            "conditions": conditions
            or [
                {
                    "status": "ERROR",
                    "metricKey": "new_duplicated_lines_density",
                    "actualValue": "19.3",
                    "errorThreshold": "3",
                }
            ],
        }
    }


def _issues(total: int) -> dict:
    return {"total": total, "issues": []}


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


class TestVerifyPr:
    def test_verify_pr_both_clean(self):
        """issues=0 + QG=OK → passing=True."""
        client = _mock_http(_issues(0), _ok_qg())
        result = verify_pr("Keiracom_Agency_OS", 981, http_client=client)
        assert result.issues_total == 0
        assert result.qg_status == "OK"
        assert result.passing is True

    def test_verify_pr_issues_nonzero(self):
        """issues=5 + QG=OK → passing=False."""
        client = _mock_http(_issues(5), _ok_qg())
        result = verify_pr("Keiracom_Agency_OS", 981, http_client=client)
        assert result.issues_total == 5
        assert result.qg_status == "OK"
        assert result.passing is False

    def test_verify_pr_qg_error(self):
        """issues=0 + QG=ERROR on dup-density → passing=False."""
        client = _mock_http(_issues(0), _error_qg())
        result = verify_pr("Keiracom_Agency_OS", 981, http_client=client)
        assert result.issues_total == 0
        assert result.qg_status == "ERROR"
        assert result.passing is False
        assert any(c["metricKey"] == "new_duplicated_lines_density" for c in result.qg_conditions)

    def test_verify_pr_both_failing(self):
        """issues=3 + QG=ERROR → passing=False, both reasons in result."""
        client = _mock_http(_issues(3), _error_qg())
        result = verify_pr("Keiracom_Agency_OS", 963, http_client=client)
        assert result.issues_total == 3
        assert result.qg_status == "ERROR"
        assert result.passing is False

    def test_verify_pr_handles_qg_none(self):
        """issues=0 + QG status absent → conservative passing=False."""
        client = _mock_http(_issues(0), {"projectStatus": {}})
        result = verify_pr("Keiracom_Agency_OS", 981, http_client=client)
        assert result.qg_status == "NONE"
        assert result.passing is False

    def test_verify_pr_http_error_issues(self):
        """Issues endpoint 5xx → passing=False, error surfaced."""
        client = MagicMock()
        resp = MagicMock()
        resp.raise_for_status.side_effect = Exception("500 Server Error")
        client.get.return_value = resp
        result = verify_pr("Keiracom_Agency_OS", 981, http_client=client)
        assert result.passing is False
        assert result.error_detail != ""

    def test_verify_pr_http_error_qg(self):
        """QG endpoint 5xx → passing=False, error surfaced."""
        client = MagicMock()
        resp_ok = MagicMock()
        resp_ok.raise_for_status = MagicMock()
        resp_ok.json.return_value = _issues(0)

        resp_err = MagicMock()
        resp_err.raise_for_status.side_effect = Exception("503 Service Unavailable")

        client.get.side_effect = [resp_ok, resp_err]
        result = verify_pr("Keiracom_Agency_OS", 981, http_client=client)
        assert result.passing is False
        assert "qualitygates endpoint error" in result.error_detail

    def test_verify_pr_real_world_pr981_shape(self):
        """Synthetic fixture matching PR #981: issues=0, QG=ERROR dup-density 19.3 vs 3."""
        dup_condition = {
            "status": "ERROR",
            "metricKey": "new_duplicated_lines_density",
            "actualValue": "19.3",
            "errorThreshold": "3",
        }
        client = _mock_http(_issues(0), _error_qg([dup_condition]))
        result = verify_pr("Keiracom_Agency_OS", 981, http_client=client)
        assert result.passing is False
        assert result.issues_total == 0
        assert result.qg_status == "ERROR"
        metrics = [c["metricKey"] for c in result.qg_conditions]
        assert "new_duplicated_lines_density" in metrics
        vals = {c["metricKey"]: c["actualValue"] for c in result.qg_conditions}
        assert vals["new_duplicated_lines_density"] == "19.3"


class TestFormatReviewBrief:
    def test_format_review_brief_includes_both_endpoint_urls(self):
        """Output text must reference both /api/issues/search and /api/qualitygates/project_status."""
        result = SonarVerifyResult(issues_total=0, qg_status="OK")
        text = format_review_brief_sonar_block(result)
        assert SOURCE_DOC_ISSUES in text
        assert SOURCE_DOC_QG in text
        assert SONARCLOUD_BASE in text

    def test_format_review_brief_lists_qg_failing_conditions(self):
        """Failing QG conditions must appear explicitly in text."""
        result = SonarVerifyResult(
            issues_total=0,
            qg_status="ERROR",
            qg_conditions=[
                {
                    "status": "ERROR",
                    "metricKey": "new_duplicated_lines_density",
                    "actualValue": "19.3",
                    "errorThreshold": "3",
                }
            ],
        )
        text = format_review_brief_sonar_block(result)
        assert "new_duplicated_lines_density" in text
        assert "19.3" in text
        assert "3" in text

    def test_format_review_brief_passing_state_concise(self):
        """When passing=True the text shows PASS verdict and no failing conditions."""
        result = SonarVerifyResult(
            issues_total=0,
            qg_status="OK",
            qg_conditions=[{"status": "OK", "metricKey": "coverage"}],
        )
        text = format_review_brief_sonar_block(result)
        assert "PASS" in text
        assert "Failing QG conditions" not in text

    def test_format_review_brief_and_rule_stated(self):
        """The AND-rule must be explicit so agents can't miss it."""
        result = SonarVerifyResult(issues_total=0, qg_status="OK")
        text = format_review_brief_sonar_block(result)
        assert "AND-rule" in text
        assert "issues_total==0" in text
        assert "qg_status==" in text
