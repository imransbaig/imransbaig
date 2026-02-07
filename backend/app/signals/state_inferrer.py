"""State inference engine.

Consumes feature dictionaries produced by ``feature_extractor`` and scores
candidate physiological/behavioural states using weighted, rule-based logic.
The state with the highest composite score wins.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class InferredStateResult:
    """Outcome of a single inference pass."""

    state: str  # e.g. "stressed", "fatigued", "energized", ...
    confidence: float  # 0.0 .. 1.0
    contributing_signals: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "state": self.state,
            "confidence": round(self.confidence, 4),
            "contributing_signals": {
                k: round(v, 4) for k, v in self.contributing_signals.items()
            },
        }


# ---------------------------------------------------------------------------
# Helper: clamp a value into [0, 1]
# ---------------------------------------------------------------------------

def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


# ---------------------------------------------------------------------------
# State Inferrer
# ---------------------------------------------------------------------------

class StateInferrer:
    """Rule-based state inference over extracted feature dictionaries.

    Each candidate state is scored by a dedicated method that returns a
    ``(score, contributing_signals)`` pair.  The state with the highest
    score is returned together with a confidence value that is the
    normalised score (divided by the sum of all positive scores so the
    result lives in ``[0, 1]``).
    """

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def infer(
        self,
        hr_features: dict,
        sleep_features: dict,
        activity_features: dict,
        context_features: dict,
    ) -> InferredStateResult:
        """Run all state scorers and return the winning state."""

        scorers = {
            "stressed": self._score_stressed,
            "fatigued": self._score_fatigued,
            "energized": self._score_energized,
            "sleep_deprived": self._score_sleep_deprived,
            "calm": self._score_calm,
        }

        results: List[tuple[str, float, dict]] = []
        for state_name, scorer in scorers.items():
            score, signals = scorer(
                hr_features, sleep_features, activity_features, context_features,
            )
            results.append((state_name, score, signals))

        # Pick the state with the highest score
        results.sort(key=lambda t: t[1], reverse=True)
        best_state, best_score, best_signals = results[0]

        # Normalise confidence
        total_positive = sum(max(s, 0.0) for _, s, _ in results)
        confidence = (best_score / total_positive) if total_positive > 0 else 0.0

        return InferredStateResult(
            state=best_state,
            confidence=_clamp01(confidence),
            contributing_signals=best_signals,
        )

    # -----------------------------------------------------------------------
    # Individual state scorers
    # -----------------------------------------------------------------------

    def _score_stressed(
        self, hr: dict, sleep: dict, activity: dict, ctx: dict,
    ) -> tuple[float, dict]:
        """Stressed: elevated HR + low HRV + sedentary + afternoon/evening.

        Weights: HR 0.4, HRV 0.3, activity 0.2, context 0.1.
        """

        resting = hr.get("resting_hr_estimate", 70.0) or 70.0
        mean_hr = hr.get("mean_hr", 0.0)
        rmssd = hr.get("hr_variability_rmssd", 50.0)
        sedentary = activity.get("sedentary_minutes", 0.0)
        active = activity.get("active_minutes", 0.0)
        time_of_day = ctx.get("time_of_day", "")

        # HR sub-score: how far mean HR exceeds resting + 15
        hr_excess = mean_hr - (resting + 15.0)
        hr_score = _clamp01(hr_excess / 25.0) if mean_hr > 0 else 0.0

        # HRV sub-score: low HRV indicates stress (RMSSD < 25 ms is low)
        hrv_score = _clamp01(1.0 - (rmssd / 60.0)) if rmssd > 0 else 0.0

        # Activity sub-score: high sedentary ratio
        total_minutes = sedentary + active
        if total_minutes > 0:
            sedentary_ratio = sedentary / total_minutes
            activity_score = _clamp01(sedentary_ratio)
        else:
            activity_score = 0.5  # neutral when unknown

        # Context sub-score: stress detection weighted higher in afternoon/evening
        context_score = 0.8 if time_of_day in ("afternoon", "evening") else 0.3

        composite = (
            0.4 * hr_score
            + 0.3 * hrv_score
            + 0.2 * activity_score
            + 0.1 * context_score
        )

        signals = {
            "hr_score": hr_score,
            "hrv_score": hrv_score,
            "activity_score": activity_score,
            "context_score": context_score,
            "mean_hr": mean_hr,
            "rmssd": rmssd,
        }

        return composite, signals

    def _score_fatigued(
        self, hr: dict, sleep: dict, activity: dict, ctx: dict,
    ) -> tuple[float, dict]:
        """Fatigued: poor sleep + low steps + morning context.

        Weights: sleep 0.45, activity 0.30, context 0.25.
        """

        efficiency = sleep.get("sleep_efficiency", 1.0)
        duration_h = sleep.get("sleep_duration_hours", 8.0)
        steps = activity.get("step_count", 0)
        time_of_day = ctx.get("time_of_day", "")

        # Sleep sub-score: bad sleep pushes this toward 1
        eff_score = _clamp01(1.0 - (efficiency / 0.75))
        dur_score = _clamp01(1.0 - (duration_h / 6.0))
        sleep_score = max(eff_score, dur_score)

        # Activity sub-score: fewer than 2000 steps is very low
        activity_score = _clamp01(1.0 - (steps / 4000.0))

        # Context sub-score: fatigue most relevant in morning
        context_score = 0.9 if time_of_day == "morning" else 0.3

        composite = (
            0.45 * sleep_score
            + 0.30 * activity_score
            + 0.25 * context_score
        )

        signals = {
            "sleep_score": sleep_score,
            "activity_score": activity_score,
            "context_score": context_score,
            "sleep_efficiency": efficiency,
            "sleep_duration_hours": duration_h,
            "step_count": steps,
        }

        return composite, signals

    def _score_energized(
        self, hr: dict, sleep: dict, activity: dict, ctx: dict,
    ) -> tuple[float, dict]:
        """Energized: good sleep + active + normal HR.

        Weights: sleep 0.35, activity 0.35, HR 0.30.
        """

        efficiency = sleep.get("sleep_efficiency", 0.0)
        duration_h = sleep.get("sleep_duration_hours", 0.0)
        active_min = activity.get("active_minutes", 0.0)
        steps = activity.get("step_count", 0)
        resting = hr.get("resting_hr_estimate", 70.0) or 70.0
        mean_hr = hr.get("mean_hr", 0.0)

        # Sleep sub-score: good sleep is efficiency > 0.8 and > 7 h
        eff_score = _clamp01((efficiency - 0.6) / 0.3)
        dur_score = _clamp01((duration_h - 5.0) / 3.0)
        sleep_score = (eff_score + dur_score) / 2.0

        # Activity sub-score: step count and active minutes
        step_score = _clamp01(steps / 8000.0)
        active_score = _clamp01(active_min / 60.0)
        activity_score = (step_score + active_score) / 2.0

        # HR sub-score: mean HR close to resting is good (not elevated)
        hr_deviation = abs(mean_hr - resting) if mean_hr > 0 else 30.0
        hr_score = _clamp01(1.0 - (hr_deviation / 30.0))

        composite = (
            0.35 * sleep_score
            + 0.35 * activity_score
            + 0.30 * hr_score
        )

        signals = {
            "sleep_score": sleep_score,
            "activity_score": activity_score,
            "hr_score": hr_score,
            "sleep_efficiency": efficiency,
            "step_count": steps,
        }

        return composite, signals

    def _score_sleep_deprived(
        self, hr: dict, sleep: dict, activity: dict, ctx: dict,
    ) -> tuple[float, dict]:
        """Sleep-deprived: very poor sleep + elevated resting HR.

        Weights: sleep 0.65, HR 0.35.
        """

        efficiency = sleep.get("sleep_efficiency", 1.0)
        duration_h = sleep.get("sleep_duration_hours", 8.0)
        resting = hr.get("resting_hr_estimate", 60.0) or 60.0
        reading_count = sleep.get("reading_count", 0)

        # Sleep sub-score: < 5 h or efficiency < 0.6 is critical
        dur_score = _clamp01(1.0 - (duration_h / 5.0))
        eff_score = _clamp01(1.0 - (efficiency / 0.6))
        sleep_score = max(dur_score, eff_score)

        # If we have no sleep readings at all, do not infer sleep deprivation
        if reading_count == 0:
            sleep_score *= 0.2

        # HR sub-score: resting HR elevated above 75 is a sign
        hr_score = _clamp01((resting - 65.0) / 20.0)

        composite = 0.65 * sleep_score + 0.35 * hr_score

        signals = {
            "sleep_score": sleep_score,
            "hr_score": hr_score,
            "sleep_duration_hours": duration_h,
            "sleep_efficiency": efficiency,
            "resting_hr": resting,
        }

        return composite, signals

    def _score_calm(
        self, hr: dict, sleep: dict, activity: dict, ctx: dict,
    ) -> tuple[float, dict]:
        """Calm: normal HR + good HRV + not sedentary for too long.

        Weights: HR 0.30, HRV 0.35, activity 0.20, context 0.15.
        """

        resting = hr.get("resting_hr_estimate", 70.0) or 70.0
        mean_hr = hr.get("mean_hr", 0.0)
        rmssd = hr.get("hr_variability_rmssd", 0.0)
        sedentary = activity.get("sedentary_minutes", 0.0)
        active = activity.get("active_minutes", 0.0)

        # HR sub-score: mean HR close to resting
        hr_deviation = abs(mean_hr - resting) if mean_hr > 0 else 20.0
        hr_score = _clamp01(1.0 - (hr_deviation / 20.0))

        # HRV sub-score: higher is better; RMSSD > 40 ms is good
        hrv_score = _clamp01(rmssd / 60.0)

        # Activity sub-score: not overly sedentary
        total_minutes = sedentary + active
        if total_minutes > 0:
            active_ratio = active / total_minutes
            activity_score = _clamp01(active_ratio / 0.5)
        else:
            activity_score = 0.5

        # Context sub-score: slightly favour morning / evening calm
        time_of_day = ctx.get("time_of_day", "")
        context_score = 0.7 if time_of_day in ("morning", "evening") else 0.5

        composite = (
            0.30 * hr_score
            + 0.35 * hrv_score
            + 0.20 * activity_score
            + 0.15 * context_score
        )

        signals = {
            "hr_score": hr_score,
            "hrv_score": hrv_score,
            "activity_score": activity_score,
            "context_score": context_score,
            "mean_hr": mean_hr,
            "rmssd": rmssd,
        }

        return composite, signals
