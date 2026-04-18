"""Tests for src/pipeline/latency_tracker.py."""
from __future__ import annotations

import time

import pytest

from src.pipeline.latency_tracker import LatencyTracker


class TestStartEndStage:
    def test_records_seconds_within_tolerance(self) -> None:
        tracker = LatencyTracker(domain="test.com.au")
        tracker.start_stage("stage3")
        time.sleep(0.05)
        tracker.end_stage("stage3")
        report = tracker.report()
        seconds = report["stages"]["stage3"]["seconds"]
        assert 0.04 <= seconds <= 0.5

    def test_records_start_and_end_utc(self) -> None:
        tracker = LatencyTracker(domain="test.com.au")
        tracker.start_stage("stage3")
        tracker.end_stage("stage3")
        stage = tracker.report()["stages"]["stage3"]
        assert "start_utc" in stage
        assert "end_utc" in stage
        # ISO-8601 with timezone offset
        assert "T" in stage["start_utc"]
        assert "T" in stage["end_utc"]

    def test_end_before_start_is_safe(self) -> None:
        tracker = LatencyTracker(domain="test.com.au")
        tracker.end_stage("ghost_stage")  # never started — must not raise
        report = tracker.report()
        assert "ghost_stage" not in report["stages"]

    def test_internal_start_mono_not_in_report(self) -> None:
        tracker = LatencyTracker(domain="test.com.au")
        tracker.start_stage("stage2")
        tracker.end_stage("stage2")
        stage = tracker.report()["stages"]["stage2"]
        assert "_start_mono" not in stage


class TestReportShape:
    def test_report_keys(self) -> None:
        tracker = LatencyTracker(domain="example.com.au")
        tracker.start_stage("stage2")
        tracker.end_stage("stage2")
        report = tracker.report()
        assert report["domain"] == "example.com.au"
        assert "run_start_utc" in report
        assert "total_seconds" in report
        assert "stages" in report
        assert "stage_count" in report
        assert "p50_stage_seconds" in report
        assert "slowest_stage" in report

    def test_stage_count(self) -> None:
        tracker = LatencyTracker(domain="x.com.au")
        for name in ("stage2", "stage3", "stage4"):
            tracker.start_stage(name)
            tracker.end_stage(name)
        assert tracker.report()["stage_count"] == 3

    def test_empty_tracker_report(self) -> None:
        tracker = LatencyTracker(domain="empty.com.au")
        report = tracker.report()
        assert report["stage_count"] == 0
        assert report["p50_stage_seconds"] == 0.0
        assert report["slowest_stage"] == "none"

    def test_incomplete_stage_excluded(self) -> None:
        """A stage that was started but not ended must not appear in completed stages."""
        tracker = LatencyTracker(domain="partial.com.au")
        tracker.start_stage("stage2")
        tracker.end_stage("stage2")
        tracker.start_stage("stage3")  # never ended
        report = tracker.report()
        assert "stage2" in report["stages"]
        assert "stage3" not in report["stages"]
        assert report["stage_count"] == 1


class TestP50Calculation:
    def test_p50_single_stage(self) -> None:
        tracker = LatencyTracker(domain="p50.com.au")
        tracker.start_stage("stage2")
        time.sleep(0.05)
        tracker.end_stage("stage2")
        report = tracker.report()
        # p50 of a single-element list is that element
        assert report["p50_stage_seconds"] == report["stages"]["stage2"]["seconds"]

    def test_p50_odd_count(self) -> None:
        """p50 of [1, 2, 3] should be the median index element (index 1 = 2)."""
        tracker = LatencyTracker(domain="odd.com.au")
        # Inject times manually via the internal dict to avoid slow sleeps
        tracker._stages = {
            "a": {"start_utc": "x", "end_utc": "y", "seconds": 1.0},
            "b": {"start_utc": "x", "end_utc": "y", "seconds": 3.0},
            "c": {"start_utc": "x", "end_utc": "y", "seconds": 2.0},
        }
        report = tracker.report()
        assert report["p50_stage_seconds"] == 2.0

    def test_p50_even_count(self) -> None:
        """p50 of [1, 2, 3, 4] should be index 2 = 3 (floor division)."""
        tracker = LatencyTracker(domain="even.com.au")
        tracker._stages = {
            "a": {"start_utc": "x", "end_utc": "y", "seconds": 1.0},
            "b": {"start_utc": "x", "end_utc": "y", "seconds": 2.0},
            "c": {"start_utc": "x", "end_utc": "y", "seconds": 3.0},
            "d": {"start_utc": "x", "end_utc": "y", "seconds": 4.0},
        }
        report = tracker.report()
        assert report["p50_stage_seconds"] == 3.0


class TestSlowestStage:
    def test_slowest_stage_identified(self) -> None:
        tracker = LatencyTracker(domain="slow.com.au")
        tracker._stages = {
            "stage2": {"start_utc": "x", "end_utc": "y", "seconds": 0.5},
            "stage7": {"start_utc": "x", "end_utc": "y", "seconds": 9.1},
            "stage3": {"start_utc": "x", "end_utc": "y", "seconds": 1.2},
        }
        assert tracker.report()["slowest_stage"] == "stage7"

    def test_slowest_none_when_empty(self) -> None:
        tracker = LatencyTracker(domain="empty.com.au")
        assert tracker.report()["slowest_stage"] == "none"
