"""Rule engine for the Coach Brain.

A ``Trigger`` encapsulates a boolean condition over the current inferred
state and raw features, together with a recommended action.  The
``TriggerRegistry`` evaluates all registered triggers and returns the ones
that fire, sorted by descending priority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from app.signals.state_inferrer import InferredStateResult


# ---------------------------------------------------------------------------
# Core data structures
# ---------------------------------------------------------------------------

@dataclass
class Trigger:
    """A single coaching rule."""

    name: str
    condition: Callable[[InferredStateResult, dict, List[InferredStateResult]], bool]
    action_type: str
    priority: int  # 1 (low) .. 10 (high)
    cooldown_minutes: int
    explanation_template: str


@dataclass
class TriggeredAction:
    """An action that a fired trigger wants to deliver."""

    trigger_name: str
    action_type: str
    priority: int
    cooldown_minutes: int
    explanation_template: str
    fired_at: datetime = field(default_factory=datetime.utcnow)
    signals_snapshot: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Built-in condition helpers
# ---------------------------------------------------------------------------

def _elevated_hr_sedentary(
    state: InferredStateResult, features: dict, history: List[InferredStateResult],
) -> bool:
    """Heart rate elevated while user is sedentary."""
    hr = features.get("hr_features", {})
    act = features.get("activity_features", {})

    mean_hr = hr.get("mean_hr", 0.0)
    resting = hr.get("resting_hr_estimate", 70.0) or 70.0
    sedentary = act.get("sedentary_minutes", 0.0)
    active = act.get("active_minutes", 0.0)

    hr_elevated = mean_hr > (resting + 15)
    total = sedentary + active
    is_sedentary = (total == 0) or (sedentary / total > 0.7)

    return hr_elevated and is_sedentary


def _prolonged_sedentary(
    state: InferredStateResult, features: dict, history: List[InferredStateResult],
) -> bool:
    """User has been sedentary for more than 45 minutes."""
    act = features.get("activity_features", {})
    return act.get("sedentary_minutes", 0.0) > 45.0


def _stress_accumulating(
    state: InferredStateResult, features: dict, history: List[InferredStateResult],
) -> bool:
    """Three or more stressed states in the last 2 hours of history."""
    if len(history) < 3:
        return False
    # Take the most recent entries (assume roughly evenly spaced)
    # A pragmatic heuristic: look at the last 12 entries (~10 min intervals = 2 h)
    recent = history[-12:]
    stressed_count = sum(1 for s in recent if s.state == "stressed")
    return stressed_count >= 3


def _poor_sleep_morning(
    state: InferredStateResult, features: dict, history: List[InferredStateResult],
) -> bool:
    """User is sleep-deprived and it is morning."""
    ctx = features.get("context_features", {})
    return state.state == "sleep_deprived" and ctx.get("time_of_day") == "morning"


def _evening_wind_down(
    state: InferredStateResult, features: dict, history: List[InferredStateResult],
) -> bool:
    """Stressed or energized after 9 PM."""
    ctx = features.get("context_features", {})
    hour = ctx.get("hour", 0)
    return state.state in ("stressed", "energized") and hour >= 21


def _positive_reinforcement(
    state: InferredStateResult, features: dict, history: List[InferredStateResult],
) -> bool:
    """User is calm and was previously stressed."""
    if state.state != "calm" or len(history) < 2:
        return False
    # Check if any of the last 4 states were "stressed"
    recent = history[-4:]
    return any(s.state == "stressed" for s in recent)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

# Default set of triggers shipped with the coach
_DEFAULT_TRIGGERS: List[Trigger] = [
    Trigger(
        name="elevated_hr_sedentary",
        condition=_elevated_hr_sedentary,
        action_type="breathing_exercise_2min",
        priority=8,
        cooldown_minutes=30,
        explanation_template=(
            "Your heart rate was {mean_hr} bpm (resting ~{resting_hr} bpm) "
            "while you were mostly sedentary; a 2-minute breathing reset "
            "usually helps."
        ),
    ),
    Trigger(
        name="prolonged_sedentary",
        condition=_prolonged_sedentary,
        action_type="movement_break",
        priority=6,
        cooldown_minutes=60,
        explanation_template=(
            "You have been sedentary for {sedentary_minutes} minutes. "
            "A short movement break can boost focus and circulation."
        ),
    ),
    Trigger(
        name="stress_accumulating",
        condition=_stress_accumulating,
        action_type="guided_reset_5min",
        priority=9,
        cooldown_minutes=120,
        explanation_template=(
            "Stress signals have appeared {stressed_count} times recently. "
            "A 5-minute guided reset can interrupt the stress cycle."
        ),
    ),
    Trigger(
        name="poor_sleep_morning",
        condition=_poor_sleep_morning,
        action_type="gentle_morning_routine",
        priority=7,
        cooldown_minutes=480,
        explanation_template=(
            "You slept about {sleep_hours} hours with {sleep_efficiency}% "
            "efficiency. A gentle morning routine will help you ease into the day."
        ),
    ),
    Trigger(
        name="evening_wind_down",
        condition=_evening_wind_down,
        action_type="wind_down_routine",
        priority=8,
        cooldown_minutes=240,
        explanation_template=(
            "It is {hour}:00 and your state is {state}. "
            "Winding down now will improve tonight's sleep quality."
        ),
    ),
    Trigger(
        name="positive_reinforcement",
        condition=_positive_reinforcement,
        action_type="encouragement_nudge",
        priority=3,
        cooldown_minutes=180,
        explanation_template=(
            "You moved from a stressed state to calm -- great job! "
            "Whatever you just did seems to be working."
        ),
    ),
]


class TriggerRegistry:
    """Maintains a list of triggers and evaluates them against the current context.

    Usage::

        registry = TriggerRegistry()
        actions = registry.evaluate(state, features, history)
    """

    def __init__(self, triggers: Optional[List[Trigger]] = None) -> None:
        self._triggers: List[Trigger] = list(triggers or _DEFAULT_TRIGGERS)

    # -----------------------------------------------------------------------
    # Mutation
    # -----------------------------------------------------------------------

    def register(self, trigger: Trigger) -> None:
        """Add a trigger to the registry."""
        self._triggers.append(trigger)

    def unregister(self, name: str) -> None:
        """Remove a trigger by name (no-op if not found)."""
        self._triggers = [t for t in self._triggers if t.name != name]

    @property
    def triggers(self) -> List[Trigger]:
        return list(self._triggers)

    # -----------------------------------------------------------------------
    # Evaluation
    # -----------------------------------------------------------------------

    def evaluate(
        self,
        state: InferredStateResult,
        features: dict,
        history: List[InferredStateResult],
    ) -> List[TriggeredAction]:
        """Evaluate all triggers and return fired actions, sorted by priority (desc)."""

        fired: List[TriggeredAction] = []
        now = datetime.utcnow()

        for trigger in self._triggers:
            try:
                if trigger.condition(state, features, history):
                    # Build a snapshot of the signals referenced by the template
                    snapshot = self._build_snapshot(state, features, history)
                    fired.append(
                        TriggeredAction(
                            trigger_name=trigger.name,
                            action_type=trigger.action_type,
                            priority=trigger.priority,
                            cooldown_minutes=trigger.cooldown_minutes,
                            explanation_template=trigger.explanation_template,
                            fired_at=now,
                            signals_snapshot=snapshot,
                        )
                    )
            except Exception:
                # A failing condition must never crash the entire evaluation
                continue

        # Sort by descending priority
        fired.sort(key=lambda a: a.priority, reverse=True)
        return fired

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _build_snapshot(
        state: InferredStateResult, features: dict, history: List[InferredStateResult],
    ) -> Dict[str, Any]:
        """Collect commonly referenced template values into a flat dict."""

        hr = features.get("hr_features", {})
        sleep = features.get("sleep_features", {})
        act = features.get("activity_features", {})
        ctx = features.get("context_features", {})

        recent_stressed = sum(
            1 for s in (history[-12:] if history else []) if s.state == "stressed"
        )

        return {
            "mean_hr": hr.get("mean_hr", 0.0),
            "resting_hr": hr.get("resting_hr_estimate", 0.0),
            "rmssd": hr.get("hr_variability_rmssd", 0.0),
            "sedentary_minutes": act.get("sedentary_minutes", 0.0),
            "active_minutes": act.get("active_minutes", 0.0),
            "step_count": act.get("step_count", 0),
            "sleep_hours": sleep.get("sleep_duration_hours", 0.0),
            "sleep_efficiency": round(sleep.get("sleep_efficiency", 0.0) * 100, 1),
            "state": state.state,
            "confidence": state.confidence,
            "hour": ctx.get("hour", 0),
            "time_of_day": ctx.get("time_of_day", ""),
            "stressed_count": recent_stressed,
        }
