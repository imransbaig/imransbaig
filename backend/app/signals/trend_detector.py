"""Trend analysis over a history of inferred states.

Operates on a time-ordered sequence of ``InferredStateResult`` objects and
produces a ``TrendReport`` that summarises dominant patterns and directional
trends (improving / stable / worsening).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from app.signals.state_inferrer import InferredStateResult


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class TrendReport:
    """Summarised trend information over a rolling window."""

    dominant_state: str
    state_distribution: Dict[str, float]  # state -> percentage (0.0 .. 1.0)
    stress_trend: str  # "improving" | "stable" | "worsening"
    sleep_trend: str   # "improving" | "stable" | "worsening"
    avg_confidence: float
    window_days: int = 7
    total_states: int = 0

    def to_dict(self) -> dict:
        return {
            "dominant_state": self.dominant_state,
            "state_distribution": {
                k: round(v, 4) for k, v in self.state_distribution.items()
            },
            "stress_trend": self.stress_trend,
            "sleep_trend": self.sleep_trend,
            "avg_confidence": round(self.avg_confidence, 4),
            "window_days": self.window_days,
            "total_states": self.total_states,
        }


# ---------------------------------------------------------------------------
# Trend Detector
# ---------------------------------------------------------------------------

class TrendDetector:
    """Rolling-window trend analysis over inferred-state history.

    The detector splits the window in half (first-half vs. second-half) and
    compares the proportion of negative states between halves to decide
    whether a particular dimension is *improving*, *stable*, or *worsening*.
    """

    # States considered negative for each dimension
    _STRESS_STATES = frozenset({"stressed"})
    _SLEEP_NEGATIVE_STATES = frozenset({"sleep_deprived", "fatigued"})

    # Threshold for declaring a trend change
    _TREND_THRESHOLD = 0.10  # 10 percentage-point shift

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def analyze(
        self,
        states: List[InferredStateResult],
        window_days: int = 7,
        reference_time: Optional[datetime] = None,
    ) -> TrendReport:
        """Analyse a list of ``InferredStateResult`` over *window_days*.

        Parameters
        ----------
        states:
            Full history of inferred states (need not be sorted).
        window_days:
            Number of trailing days to consider.
        reference_time:
            The "now" anchor; defaults to ``datetime.utcnow()``.
        """

        if reference_time is None:
            reference_time = datetime.utcnow()

        # --- Empty / no-data fallback --------------------------------------
        if not states:
            return TrendReport(
                dominant_state="unknown",
                state_distribution={},
                stress_trend="stable",
                sleep_trend="stable",
                avg_confidence=0.0,
                window_days=window_days,
                total_states=0,
            )

        # --- State distribution --------------------------------------------
        state_counts = Counter(s.state for s in states)
        total = len(states)
        distribution = {state: count / total for state, count in state_counts.items()}
        dominant_state = state_counts.most_common(1)[0][0]

        # --- Average confidence --------------------------------------------
        avg_confidence = sum(s.confidence for s in states) / total

        # --- Directional trends (first half vs second half) ----------------
        midpoint = total // 2
        first_half = states[:midpoint] if midpoint > 0 else states
        second_half = states[midpoint:] if midpoint > 0 else states

        stress_trend = self._compute_trend(
            first_half, second_half, self._STRESS_STATES,
        )
        sleep_trend = self._compute_trend(
            first_half, second_half, self._SLEEP_NEGATIVE_STATES,
        )

        return TrendReport(
            dominant_state=dominant_state,
            state_distribution=distribution,
            stress_trend=stress_trend,
            sleep_trend=sleep_trend,
            avg_confidence=avg_confidence,
            window_days=window_days,
            total_states=total,
        )

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    @classmethod
    def _compute_trend(
        cls,
        first_half: List[InferredStateResult],
        second_half: List[InferredStateResult],
        negative_states: frozenset[str],
    ) -> str:
        """Compare proportion of *negative_states* between two halves.

        Returns ``"improving"`` when the proportion decreased by more than
        ``_TREND_THRESHOLD``, ``"worsening"`` when it increased, and
        ``"stable"`` otherwise.
        """

        def _proportion(segment: List[InferredStateResult]) -> float:
            if not segment:
                return 0.0
            return sum(1 for s in segment if s.state in negative_states) / len(segment)

        first_pct = _proportion(first_half)
        second_pct = _proportion(second_half)
        delta = second_pct - first_pct

        if delta <= -cls._TREND_THRESHOLD:
            return "improving"
        if delta >= cls._TREND_THRESHOLD:
            return "worsening"
        return "stable"
