"""Tests for the trend detection module."""

import pytest
from datetime import datetime, timedelta
from app.signals.trend_detector import TrendDetector, TrendReport
from app.signals.state_inferrer import InferredStateResult


@pytest.fixture
def detector():
    return TrendDetector()


@pytest.fixture
def mostly_stressed_history():
    """History with mostly stressed states."""
    state_sequence = [
        "stressed", "stressed", "calm", "stressed", "fatigued",
        "stressed", "stressed", "calm", "stressed", "stressed",
        "fatigued", "stressed", "calm", "stressed",
    ]
    return [
        InferredStateResult(
            state=state,
            confidence=0.7 + (i % 3) * 0.1,
            contributing_signals={"source": "test"},
        )
        for i, state in enumerate(state_sequence)
    ]


@pytest.fixture
def improving_history():
    """History transitioning from stressed to calm."""
    state_sequence = [
        "stressed", "stressed", "stressed", "stressed",
        "stressed", "fatigued", "calm", "calm",
        "calm", "calm", "energized", "calm",
        "calm", "energized",
    ]
    return [
        InferredStateResult(
            state=state,
            confidence=0.75,
            contributing_signals={"source": "test"},
        )
        for state in state_sequence
    ]


class TestTrendDetector:
    def test_mostly_stressed_dominant_state(self, detector, mostly_stressed_history):
        report = detector.analyze(mostly_stressed_history, window_days=7)
        assert report.dominant_state == "stressed"

    def test_state_distribution_sums_to_one(self, detector, mostly_stressed_history):
        report = detector.analyze(mostly_stressed_history, window_days=7)
        total = sum(report.state_distribution.values())
        assert abs(total - 1.0) < 0.01

    def test_improving_trend(self, detector, improving_history):
        report = detector.analyze(improving_history, window_days=7)
        assert report.stress_trend in ("improving", "stable")

    def test_stressed_trend_direction(self, detector, mostly_stressed_history):
        report = detector.analyze(mostly_stressed_history, window_days=7)
        assert report.stress_trend in ("worsening", "stable", "improving")

    def test_empty_history(self, detector):
        report = detector.analyze([], window_days=7)
        assert report.dominant_state == "unknown"
        assert report.avg_confidence == 0.0

    def test_single_state(self, detector):
        states = [InferredStateResult(
            state="calm",
            confidence=0.8,
            contributing_signals={},
        )]
        report = detector.analyze(states, window_days=7)
        assert report.dominant_state == "calm"

    def test_report_has_all_fields(self, detector, mostly_stressed_history):
        report = detector.analyze(mostly_stressed_history, window_days=7)
        assert hasattr(report, "dominant_state")
        assert hasattr(report, "state_distribution")
        assert hasattr(report, "stress_trend")
        assert hasattr(report, "sleep_trend")
        assert hasattr(report, "avg_confidence")

    def test_avg_confidence_reasonable(self, detector, mostly_stressed_history):
        report = detector.analyze(mostly_stressed_history, window_days=7)
        assert 0 < report.avg_confidence <= 1.0
