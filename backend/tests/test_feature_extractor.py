"""Tests for the feature extraction module."""

import pytest
from datetime import datetime, timedelta
from app.signals.feature_extractor import (
    SensorData,
    extract_hr_features,
    extract_sleep_features,
    extract_activity_features,
    extract_context_features,
)


class TestHRFeatures:
    def test_basic_hr_extraction(self, sample_hr_readings):
        features = extract_hr_features(sample_hr_readings)
        assert "mean_hr" in features
        assert "hr_variability_rmssd" in features
        assert "resting_hr_estimate" in features
        assert "max_hr" in features
        assert "minutes_above_resting_plus_20" in features
        assert "reading_count" in features

    def test_mean_hr_reasonable(self, sample_hr_readings):
        features = extract_hr_features(sample_hr_readings)
        assert 60 <= features["mean_hr"] <= 120

    def test_max_hr_is_maximum(self, sample_hr_readings):
        features = extract_hr_features(sample_hr_readings)
        actual_max = max(r.value for r in sample_hr_readings)
        assert features["max_hr"] == actual_max

    def test_resting_hr_below_mean(self, sample_hr_readings):
        features = extract_hr_features(sample_hr_readings)
        assert features["resting_hr_estimate"] <= features["mean_hr"]

    def test_empty_readings_returns_defaults(self):
        features = extract_hr_features([])
        assert features["mean_hr"] == 0.0
        assert features["hr_variability_rmssd"] == 0.0
        assert features["reading_count"] == 0

    def test_single_reading(self):
        reading = SensorData(
            reading_type="heart_rate",
            value=75.0,
            timestamp=datetime.now(),
            metadata={},
        )
        features = extract_hr_features([reading])
        assert features["mean_hr"] == 75.0
        assert features["max_hr"] == 75.0

    def test_hrv_positive_for_variable_hr(self, sample_hr_readings):
        features = extract_hr_features(sample_hr_readings)
        assert features["hr_variability_rmssd"] > 0


class TestSleepFeatures:
    def test_basic_sleep_extraction(self, sample_sleep_readings):
        features = extract_sleep_features(sample_sleep_readings)
        assert "sleep_duration_hours" in features
        assert "sleep_efficiency" in features
        assert "awakenings_count" in features
        assert "deep_sleep_ratio" in features

    def test_sleep_duration_reasonable(self, sample_sleep_readings):
        features = extract_sleep_features(sample_sleep_readings)
        assert 0 < features["sleep_duration_hours"] <= 12

    def test_sleep_efficiency_bounded(self, sample_sleep_readings):
        features = extract_sleep_features(sample_sleep_readings)
        assert 0 <= features["sleep_efficiency"] <= 1.0

    def test_poor_sleep_detection(self, poor_sleep_readings):
        features = extract_sleep_features(poor_sleep_readings)
        assert features["sleep_efficiency"] < 0.75

    def test_empty_sleep_readings(self):
        features = extract_sleep_features([])
        assert features["sleep_duration_hours"] == 0.0
        assert features["reading_count"] == 0


class TestActivityFeatures:
    def test_basic_activity_extraction(self, sample_activity_readings):
        features = extract_activity_features(sample_activity_readings)
        assert "step_count" in features
        assert "sedentary_minutes" in features
        assert "active_minutes" in features
        assert "activity_transitions" in features

    def test_total_steps_positive(self, sample_activity_readings):
        features = extract_activity_features(sample_activity_readings)
        assert features["step_count"] > 0

    def test_sedentary_detection(self, sample_activity_readings):
        features = extract_activity_features(sample_activity_readings)
        assert features["sedentary_minutes"] > 0

    def test_active_minutes_detected(self, sample_activity_readings):
        features = extract_activity_features(sample_activity_readings)
        assert features["active_minutes"] > 0

    def test_empty_activity_readings(self):
        features = extract_activity_features([])
        assert features["step_count"] == 0
        assert features["reading_count"] == 0


class TestContextFeatures:
    def test_morning_context(self):
        morning = datetime(2024, 3, 15, 8, 30, 0)
        features = extract_context_features(morning, [])
        assert features["time_of_day"] == "morning"

    def test_afternoon_context(self):
        afternoon = datetime(2024, 3, 15, 14, 0, 0)
        features = extract_context_features(afternoon, [])
        assert features["time_of_day"] == "afternoon"

    def test_evening_context(self):
        evening = datetime(2024, 3, 15, 20, 0, 0)
        features = extract_context_features(evening, [])
        assert features["time_of_day"] == "evening"

    def test_night_context(self):
        night = datetime(2024, 3, 15, 23, 30, 0)
        features = extract_context_features(night, [])
        assert features["time_of_day"] == "night"

    def test_cue_context(self, sample_cues):
        now = datetime(2024, 3, 15, 14, 30, 0)
        features = extract_context_features(now, sample_cues)
        assert "recent_cue_types" in features
        assert len(features["recent_cue_types"]) > 0

    def test_no_cues_sentinel(self):
        now = datetime(2024, 3, 15, 14, 0, 0)
        features = extract_context_features(now, [])
        assert features["minutes_since_last_cue"] == -1.0

    def test_day_of_week_present(self):
        dt = datetime(2024, 3, 15, 10, 0, 0)  # Friday
        features = extract_context_features(dt, [])
        assert features["day_of_week"] == "friday"
