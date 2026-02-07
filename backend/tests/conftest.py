"""Shared test fixtures for the Agentic Health Coach backend."""

import pytest
from datetime import datetime, timedelta
from app.signals.feature_extractor import SensorData


@pytest.fixture
def sample_hr_readings():
    """Generate realistic heart rate sensor data over 2 hours."""
    base_time = datetime(2024, 3, 15, 14, 0, 0)
    readings = []
    hr_values = [
        72, 74, 76, 78, 82, 85, 88, 91, 93, 92,
        90, 88, 85, 82, 80, 78, 76, 74, 73, 72,
        75, 80, 86, 90, 94, 96, 93, 89, 84, 78,
    ]
    for i, hr in enumerate(hr_values):
        readings.append(SensorData(
            reading_type="heart_rate",
            value=float(hr),
            timestamp=base_time + timedelta(minutes=i * 4),
            metadata={"source": "fitbit"},
        ))
    return readings


@pytest.fixture
def sample_sleep_readings():
    """Generate realistic sleep sensor data for one night."""
    base_time = datetime(2024, 3, 14, 22, 30, 0)
    readings = []
    stages = [
        0, 1, 1, 2, 2, 2, 3, 3, 1, 1,
        2, 2, 2, 3, 3, 3, 1, 0, 1, 2,
        2, 3, 3, 1, 1, 0, 1, 2, 2, 3,
    ]
    for i, stage in enumerate(stages):
        readings.append(SensorData(
            reading_type="sleep",
            value=float(stage),
            timestamp=base_time + timedelta(minutes=i * 15),
            metadata={"stage_name": ["awake", "light", "deep", "rem"][stage]},
        ))
    return readings


@pytest.fixture
def sample_activity_readings():
    """Generate realistic activity data with both steps and activity levels."""
    base_time = datetime(2024, 3, 15, 8, 0, 0)
    readings = []
    steps_per_hour = [200, 1500, 300, 150, 80, 2000, 400, 100, 50, 1200, 800, 300]
    for i, steps in enumerate(steps_per_hour):
        readings.append(SensorData(
            reading_type="steps",
            value=float(steps),
            timestamp=base_time + timedelta(hours=i),
            metadata={"period": "hourly"},
        ))
    # Add activity level readings (0=sedentary, 1=light, 2=moderate)
    activity_levels = [0, 1, 0, 0, 0, 2, 1, 0, 0, 1, 1, 0]
    for i, level in enumerate(activity_levels):
        readings.append(SensorData(
            reading_type="activity",
            value=float(level),
            timestamp=base_time + timedelta(hours=i),
            metadata={"duration_minutes": 60.0},
        ))
    return readings


@pytest.fixture
def sample_cues():
    """Sample user-reported cues as SensorData objects."""
    base_time = datetime(2024, 3, 15, 14, 0, 0)
    return [
        SensorData(
            reading_type="stress",
            value=1.0,
            timestamp=base_time - timedelta(hours=1),
            metadata={"note": "Difficult meeting"},
        ),
        SensorData(
            reading_type="mood_low",
            value=1.0,
            timestamp=base_time - timedelta(minutes=30),
            metadata={"note": ""},
        ),
    ]


@pytest.fixture
def poor_sleep_readings():
    """Generate poor sleep data (fragmented with many awakenings)."""
    base_time = datetime(2024, 3, 14, 23, 30, 0)
    readings = []
    stages = [
        0, 0, 1, 1, 0, 1, 2, 1, 0, 0,
        1, 1, 2, 1, 0, 1, 1, 0, 0, 0,
    ]
    for i, stage in enumerate(stages):
        readings.append(SensorData(
            reading_type="sleep",
            value=float(stage),
            timestamp=base_time + timedelta(minutes=i * 15),
            metadata={"stage_name": ["awake", "light", "deep", "rem"][stage]},
        ))
    return readings
