"""Feature extraction from raw sensor data.

Transforms raw SensorData readings into structured feature dictionaries that
downstream inference components consume.  Every function uses real numerical
algorithms -- no hard-coded stub values.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List


# ---------------------------------------------------------------------------
# Portable data container -- intentionally free of SQLAlchemy so the signals
# package can be tested and reused without a database dependency.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SensorData:
    """Single sensor reading coming from any source (wearable, phone, etc.)."""

    reading_type: str  # e.g. "heart_rate", "sleep", "steps", "activity"
    value: float
    timestamp: datetime
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Heart-rate features
# ---------------------------------------------------------------------------

def extract_hr_features(readings: List[SensorData]) -> dict:
    """Compute heart-rate features from a sequence of HR readings.

    Parameters
    ----------
    readings:
        ``SensorData`` items whose ``reading_type`` is ``"heart_rate"``
        and ``value`` carries the BPM measurement.

    Returns
    -------
    dict with keys:
        mean_hr, hr_variability_rmssd, resting_hr_estimate, max_hr,
        minutes_above_resting_plus_20, reading_count
    """

    hr_readings = sorted(
        [r for r in readings if r.reading_type == "heart_rate"],
        key=lambda r: r.timestamp,
    )

    if not hr_readings:
        return {
            "mean_hr": 0.0,
            "hr_variability_rmssd": 0.0,
            "resting_hr_estimate": 0.0,
            "max_hr": 0.0,
            "minutes_above_resting_plus_20": 0.0,
            "reading_count": 0,
        }

    values = [r.value for r in hr_readings]

    # --- Mean HR ---
    mean_hr = sum(values) / len(values)

    # --- Max HR ---
    max_hr = max(values)

    # --- Resting HR estimate: lowest 10th-percentile average ---------------
    sorted_vals = sorted(values)
    tenth_pct_count = max(1, len(sorted_vals) // 10)
    resting_hr_estimate = sum(sorted_vals[:tenth_pct_count]) / tenth_pct_count

    # --- HRV (RMSSD approximation) ----------------------------------------
    # RMSSD = root mean square of successive differences between heartbeats.
    # With BPM samples we approximate inter-beat intervals (IBI) in ms and
    # compute successive differences.
    if len(values) >= 2:
        ibis = [60_000.0 / bpm for bpm in values if bpm > 0]
        if len(ibis) >= 2:
            successive_diffs_sq = [
                (ibis[i + 1] - ibis[i]) ** 2 for i in range(len(ibis) - 1)
            ]
            rmssd = math.sqrt(sum(successive_diffs_sq) / len(successive_diffs_sq))
        else:
            rmssd = 0.0
    else:
        rmssd = 0.0

    # --- Time above resting + 20 BPM --------------------------------------
    threshold = resting_hr_estimate + 20.0
    minutes_above = 0.0
    for i in range(len(hr_readings)):
        if hr_readings[i].value > threshold:
            if i + 1 < len(hr_readings):
                delta = (hr_readings[i + 1].timestamp - hr_readings[i].timestamp).total_seconds() / 60.0
                # Cap per-interval contribution to 10 min to avoid giant gaps
                minutes_above += min(delta, 10.0)
            else:
                # Last reading -- assume 1-minute contribution
                minutes_above += 1.0

    return {
        "mean_hr": round(mean_hr, 2),
        "hr_variability_rmssd": round(rmssd, 2),
        "resting_hr_estimate": round(resting_hr_estimate, 2),
        "max_hr": round(max_hr, 2),
        "minutes_above_resting_plus_20": round(minutes_above, 2),
        "reading_count": len(hr_readings),
    }


# ---------------------------------------------------------------------------
# Sleep features
# ---------------------------------------------------------------------------

def extract_sleep_features(readings: List[SensorData]) -> dict:
    """Compute sleep features from sleep-stage readings.

    Each ``SensorData`` with ``reading_type == "sleep"`` represents one
    observed sleep segment.  ``value`` encodes the stage:

    * 0 = awake
    * 1 = light sleep
    * 2 = deep sleep
    * 3 = REM sleep

    ``metadata`` may contain ``{"duration_minutes": <float>}`` for the
    segment length.  If absent the duration is inferred from the gap to
    the next reading (capped at 120 min to tolerate missing data).

    Returns
    -------
    dict with keys:
        total_sleep_minutes, sleep_efficiency, awakenings_count,
        deep_sleep_ratio, sleep_duration_hours, reading_count
    """

    sleep_readings = sorted(
        [r for r in readings if r.reading_type == "sleep"],
        key=lambda r: r.timestamp,
    )

    if not sleep_readings:
        return {
            "total_sleep_minutes": 0.0,
            "sleep_efficiency": 0.0,
            "awakenings_count": 0,
            "deep_sleep_ratio": 0.0,
            "sleep_duration_hours": 0.0,
            "reading_count": 0,
        }

    # Accumulate durations per stage
    stage_minutes: dict[int, float] = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0}

    for i, reading in enumerate(sleep_readings):
        stage = int(reading.value)
        duration = reading.metadata.get("duration_minutes", None)
        if duration is None:
            if i + 1 < len(sleep_readings):
                gap = (sleep_readings[i + 1].timestamp - reading.timestamp).total_seconds() / 60.0
                duration = min(gap, 120.0)
            else:
                duration = 30.0  # default for last segment
        stage_minutes.setdefault(stage, 0.0)
        stage_minutes[stage] = stage_minutes.get(stage, 0.0) + duration

    total_in_bed = sum(stage_minutes.values())
    total_sleep = total_in_bed - stage_minutes.get(0, 0.0)

    sleep_efficiency = (total_sleep / total_in_bed) if total_in_bed > 0 else 0.0

    # Count awakenings: transitions where stage becomes 0 from a non-zero stage
    awakenings = 0
    for i in range(1, len(sleep_readings)):
        prev_stage = int(sleep_readings[i - 1].value)
        curr_stage = int(sleep_readings[i].value)
        if curr_stage == 0 and prev_stage != 0:
            awakenings += 1

    deep_sleep = stage_minutes.get(2, 0.0)
    deep_sleep_ratio = (deep_sleep / total_sleep) if total_sleep > 0 else 0.0

    return {
        "total_sleep_minutes": round(total_sleep, 2),
        "sleep_efficiency": round(sleep_efficiency, 4),
        "awakenings_count": awakenings,
        "deep_sleep_ratio": round(deep_sleep_ratio, 4),
        "sleep_duration_hours": round(total_sleep / 60.0, 2),
        "reading_count": len(sleep_readings),
    }


# ---------------------------------------------------------------------------
# Activity features
# ---------------------------------------------------------------------------

def extract_activity_features(readings: List[SensorData]) -> dict:
    """Compute activity features from step/activity readings.

    Accepted ``reading_type`` values:

    * ``"steps"``: ``value`` is incremental step count for the interval.
    * ``"activity"``: ``value`` encodes level (0 = sedentary, 1 = light,
      2 = moderate, 3 = vigorous).  Duration taken from
      ``metadata["duration_minutes"]`` or inferred from gap to next reading.

    Returns
    -------
    dict with keys:
        step_count, sedentary_minutes, active_minutes, activity_transitions,
        reading_count
    """

    step_readings = sorted(
        [r for r in readings if r.reading_type == "steps"],
        key=lambda r: r.timestamp,
    )
    activity_readings = sorted(
        [r for r in readings if r.reading_type == "activity"],
        key=lambda r: r.timestamp,
    )

    step_count = sum(r.value for r in step_readings)

    sedentary_minutes = 0.0
    active_minutes = 0.0
    transitions = 0

    for i, reading in enumerate(activity_readings):
        level = int(reading.value)
        duration = reading.metadata.get("duration_minutes", None)
        if duration is None:
            if i + 1 < len(activity_readings):
                gap = (activity_readings[i + 1].timestamp - reading.timestamp).total_seconds() / 60.0
                duration = min(gap, 60.0)
            else:
                duration = 5.0
        if level == 0:
            sedentary_minutes += duration
        else:
            active_minutes += duration

        # Count transitions in activity level
        if i > 0:
            prev_level = int(activity_readings[i - 1].value)
            if level != prev_level:
                transitions += 1

    total_count = len(step_readings) + len(activity_readings)

    return {
        "step_count": int(step_count),
        "sedentary_minutes": round(sedentary_minutes, 2),
        "active_minutes": round(active_minutes, 2),
        "activity_transitions": transitions,
        "reading_count": total_count,
    }


# ---------------------------------------------------------------------------
# Context features
# ---------------------------------------------------------------------------

def _time_of_day_bucket(hour: int) -> str:
    """Map an hour (0-23) to a human-readable time-of-day bucket."""
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "night"


def extract_context_features(
    timestamp: datetime,
    cues: List[SensorData] | None = None,
) -> dict:
    """Derive contextual features from the current timestamp and recent cues.

    Parameters
    ----------
    timestamp:
        The point in time for which context is being evaluated.
    cues:
        Recent ``SensorData`` items that represent environmental or
        behavioural cues (e.g. calendar events, location changes).

    Returns
    -------
    dict with keys:
        time_of_day, hour, day_of_week, is_weekend, recent_cue_types,
        cue_count, minutes_since_last_cue
    """

    cues = cues or []

    time_of_day = _time_of_day_bucket(timestamp.hour)
    day_of_week = timestamp.strftime("%A").lower()
    is_weekend = day_of_week in ("saturday", "sunday")

    # Recent cue types (deduplicated, preserving order)
    seen: set[str] = set()
    recent_cue_types: list[str] = []
    for c in sorted(cues, key=lambda c: c.timestamp, reverse=True):
        if c.reading_type not in seen:
            seen.add(c.reading_type)
            recent_cue_types.append(c.reading_type)

    # Minutes since last cue
    if cues:
        latest_cue = max(cues, key=lambda c: c.timestamp)
        minutes_since = (timestamp - latest_cue.timestamp).total_seconds() / 60.0
        minutes_since_last_cue = max(0.0, round(minutes_since, 2))
    else:
        minutes_since_last_cue = -1.0  # sentinel: no cues available

    return {
        "time_of_day": time_of_day,
        "hour": timestamp.hour,
        "day_of_week": day_of_week,
        "is_weekend": is_weekend,
        "recent_cue_types": recent_cue_types,
        "cue_count": len(cues),
        "minutes_since_last_cue": minutes_since_last_cue,
    }
