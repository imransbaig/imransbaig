"""Tests for the state inference engine."""

import pytest
from app.signals.state_inferrer import StateInferrer


@pytest.fixture
def inferrer():
    return StateInferrer()


class TestStateInferrer:
    def test_stressed_state_detection(self, inferrer):
        """Elevated HR + low HRV + sedentary + afternoon → stressed."""
        hr_features = {
            "mean_hr": 95,
            "hr_variability_rmssd": 20,
            "resting_hr_estimate": 68,
            "max_hr": 105,
            "minutes_above_resting_plus_20": 45,
        }
        sleep_features = {
            "sleep_duration_hours": 7,
            "sleep_efficiency": 0.85,
            "awakenings_count": 2,
            "deep_sleep_ratio": 0.2,
            "reading_count": 20,
        }
        activity_features = {
            "step_count": 1200,
            "sedentary_minutes": 300,
            "active_minutes": 30,
            "activity_transitions": 3,
        }
        context_features = {
            "time_of_day": "afternoon",
            "day_of_week": "tuesday",
            "recent_cue_types": ["stress"],
            "minutes_since_last_cue": 30,
        }
        result = inferrer.infer(hr_features, sleep_features, activity_features, context_features)
        assert result.state == "stressed"
        assert 0 < result.confidence <= 1.0

    def test_calm_state_detection(self, inferrer):
        """Normal HR + good HRV + moderate activity → calm."""
        hr_features = {
            "mean_hr": 72,
            "hr_variability_rmssd": 55,
            "resting_hr_estimate": 65,
            "max_hr": 80,
            "minutes_above_resting_plus_20": 5,
        }
        sleep_features = {
            "sleep_duration_hours": 6.5,
            "sleep_efficiency": 0.78,
            "awakenings_count": 2,
            "deep_sleep_ratio": 0.18,
            "reading_count": 20,
        }
        activity_features = {
            "step_count": 4000,
            "sedentary_minutes": 120,
            "active_minutes": 50,
            "activity_transitions": 8,
        }
        context_features = {
            "time_of_day": "morning",
            "day_of_week": "friday",
            "recent_cue_types": [],
            "minutes_since_last_cue": -1,
        }
        result = inferrer.infer(hr_features, sleep_features, activity_features, context_features)
        assert result.state == "calm"
        assert result.confidence > 0.2

    def test_sleep_deprived_detection(self, inferrer):
        """Very poor sleep + elevated resting HR + not morning → sleep_deprived."""
        hr_features = {
            "mean_hr": 82,
            "hr_variability_rmssd": 30,
            "resting_hr_estimate": 78,
            "max_hr": 95,
            "minutes_above_resting_plus_20": 20,
        }
        sleep_features = {
            "sleep_duration_hours": 3.0,
            "sleep_efficiency": 0.40,
            "awakenings_count": 8,
            "deep_sleep_ratio": 0.05,
            "reading_count": 15,
        }
        activity_features = {
            "step_count": 6000,
            "sedentary_minutes": 100,
            "active_minutes": 80,
            "activity_transitions": 10,
        }
        context_features = {
            "time_of_day": "afternoon",
            "day_of_week": "monday",
            "recent_cue_types": [],
            "minutes_since_last_cue": -1,
        }
        result = inferrer.infer(hr_features, sleep_features, activity_features, context_features)
        assert result.state in ("sleep_deprived", "calm", "fatigued")

    def test_fatigued_detection(self, inferrer):
        """Poor sleep + low activity in morning → fatigued."""
        hr_features = {
            "mean_hr": 78,
            "hr_variability_rmssd": 35,
            "resting_hr_estimate": 70,
            "max_hr": 88,
            "minutes_above_resting_plus_20": 10,
        }
        sleep_features = {
            "sleep_duration_hours": 5.5,
            "sleep_efficiency": 0.70,
            "awakenings_count": 5,
            "deep_sleep_ratio": 0.12,
            "reading_count": 20,
        }
        activity_features = {
            "step_count": 500,
            "sedentary_minutes": 240,
            "active_minutes": 15,
            "activity_transitions": 2,
        }
        context_features = {
            "time_of_day": "morning",
            "day_of_week": "wednesday",
            "recent_cue_types": [],
            "minutes_since_last_cue": -1,
        }
        result = inferrer.infer(hr_features, sleep_features, activity_features, context_features)
        assert result.state in ("fatigued", "sleep_deprived")

    def test_energized_detection(self, inferrer):
        """Good sleep + very active + normal HR → energized."""
        hr_features = {
            "mean_hr": 70,
            "hr_variability_rmssd": 60,
            "resting_hr_estimate": 62,
            "max_hr": 85,
            "minutes_above_resting_plus_20": 2,
        }
        sleep_features = {
            "sleep_duration_hours": 8.5,
            "sleep_efficiency": 0.95,
            "awakenings_count": 0,
            "deep_sleep_ratio": 0.28,
            "reading_count": 25,
        }
        activity_features = {
            "step_count": 12000,
            "sedentary_minutes": 60,
            "active_minutes": 240,
            "activity_transitions": 20,
        }
        context_features = {
            "time_of_day": "afternoon",
            "day_of_week": "saturday",
            "recent_cue_types": ["mood_high"],
            "minutes_since_last_cue": 60,
        }
        result = inferrer.infer(hr_features, sleep_features, activity_features, context_features)
        assert result.state in ("energized", "calm")

    def test_confidence_bounded(self, inferrer):
        """Confidence should always be between 0 and 1."""
        hr_features = {"mean_hr": 80, "hr_variability_rmssd": 40, "resting_hr_estimate": 68}
        sleep_features = {"sleep_duration_hours": 7, "sleep_efficiency": 0.80, "reading_count": 20}
        activity_features = {"step_count": 5000, "sedentary_minutes": 180, "active_minutes": 90}
        context_features = {"time_of_day": "evening"}
        result = inferrer.infer(hr_features, sleep_features, activity_features, context_features)
        assert 0 < result.confidence <= 1.0

    def test_contributing_signals_populated(self, inferrer):
        """Result should include contributing signals."""
        hr_features = {"mean_hr": 95, "hr_variability_rmssd": 20, "resting_hr_estimate": 68}
        sleep_features = {"sleep_duration_hours": 7, "sleep_efficiency": 0.85, "reading_count": 20}
        activity_features = {"step_count": 1200, "sedentary_minutes": 300, "active_minutes": 30}
        context_features = {"time_of_day": "afternoon"}
        result = inferrer.infer(hr_features, sleep_features, activity_features, context_features)
        assert isinstance(result.contributing_signals, dict)
        assert len(result.contributing_signals) > 0
