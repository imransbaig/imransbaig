"""Coach Engine -- the agentic orchestrator.

Implements the full SENSE -> INFER -> PLAN -> ACT -> LEARN loop that powers
the health coach.  This is the single entry-point that API routes call.

Lifecycle
---------
1. **SENSE** -- receive raw ``SensorData`` readings and contextual cues.
2. **INFER** -- extract features and infer the user's physiological state.
3. **PLAN** -- evaluate the trigger registry and select the best action.
4. **ACT** -- return the selected action with a full reason trace.
5. **LEARN** -- accept user feedback to improve future action selection.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.brain.action_selector import ActionDelivery, ActionSelector, SelectedAction
from app.brain.reason_tracer import ReasonTracer
from app.brain.trigger_registry import TriggerRegistry
from app.signals.feature_extractor import (
    SensorData,
    extract_activity_features,
    extract_context_features,
    extract_hr_features,
    extract_sleep_features,
)
from app.signals.state_inferrer import InferredStateResult, StateInferrer
from app.signals.trend_detector import TrendDetector, TrendReport


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class CoachResult:
    """Value object returned by ``CoachEngine.process``."""

    inferred_state: InferredStateResult
    next_action: Optional[SelectedAction] = None
    reason_trace: Optional[Dict[str, Any]] = None
    trend_summary: Optional[TrendReport] = None
    action_id: Optional[str] = None  # for feedback correlation

    def to_dict(self) -> dict:
        result: dict = {
            "inferred_state": self.inferred_state.to_dict(),
            "next_action": None,
            "reason_trace": self.reason_trace,
            "trend_summary": None,
            "action_id": self.action_id,
        }
        if self.next_action is not None:
            result["next_action"] = {
                "action_type": self.next_action.action_type,
                "priority": self.next_action.priority,
                "trigger_name": self.next_action.trigger_name,
            }
        if self.trend_summary is not None:
            result["trend_summary"] = self.trend_summary.to_dict()
        return result


# ---------------------------------------------------------------------------
# Coach Engine
# ---------------------------------------------------------------------------

class CoachEngine:
    """Agentic health-coach orchestrator.

    Instantiate once per application (or per user session) and call
    ``process`` with each new batch of sensor data.

    Parameters
    ----------
    trigger_registry:
        Optional custom ``TriggerRegistry``; defaults to the built-in set.
    action_selector:
        Optional custom ``ActionSelector``; defaults to standard settings.
    trend_window_days:
        Number of days the trend detector considers.
    """

    def __init__(
        self,
        trigger_registry: Optional[TriggerRegistry] = None,
        action_selector: Optional[ActionSelector] = None,
        trend_window_days: int = 7,
    ) -> None:
        self._inferrer = StateInferrer()
        self._trigger_registry = trigger_registry or TriggerRegistry()
        self._action_selector = action_selector or ActionSelector()
        self._trend_detector = TrendDetector()
        self._reason_tracer = ReasonTracer()
        self._trend_window_days = trend_window_days

        # Per-user in-memory stores (keyed by user_id)
        self._state_history: Dict[str, List[InferredStateResult]] = defaultdict(list)
        self._action_history: Dict[str, List[ActionDelivery]] = defaultdict(list)
        # Map action_id -> (user_id, ActionDelivery) for feedback correlation
        self._pending_feedback: Dict[str, tuple[str, ActionDelivery]] = {}

    # -----------------------------------------------------------------------
    # SENSE -> INFER -> PLAN -> ACT
    # -----------------------------------------------------------------------

    def process(
        self,
        user_id: str,
        readings: List[SensorData],
        cues: Optional[List[SensorData]] = None,
        mode: str = "passive",
    ) -> CoachResult:
        """Run one full agentic cycle.

        Parameters
        ----------
        user_id:
            Unique identifier for the user.
        readings:
            Batch of raw ``SensorData`` readings to process.
        cues:
            Optional contextual cues (calendar events, location, etc.).
        mode:
            ``"passive"`` or ``"live"`` -- forwarded to the action selector.

        Returns
        -------
        CoachResult
        """

        now = datetime.now(timezone.utc)
        cues = cues or []

        # ---- SENSE --------------------------------------------------------
        hr_features = extract_hr_features(readings)
        sleep_features = extract_sleep_features(readings)
        activity_features = extract_activity_features(readings)
        context_features = extract_context_features(now, cues)

        features_bundle: Dict[str, dict] = {
            "hr_features": hr_features,
            "sleep_features": sleep_features,
            "activity_features": activity_features,
            "context_features": context_features,
        }

        # ---- INFER --------------------------------------------------------
        inferred = self._inferrer.infer(
            hr_features, sleep_features, activity_features, context_features,
        )

        # Persist to history
        user_states = self._state_history[user_id]
        user_states.append(inferred)

        # ---- PLAN ---------------------------------------------------------
        triggered = self._trigger_registry.evaluate(
            state=inferred,
            features=features_bundle,
            history=user_states,
        )

        selected = self._action_selector.select(
            triggered_actions=triggered,
            user_history=self._action_history[user_id],
            mode=mode,
        )

        # ---- ACT ----------------------------------------------------------
        reason_trace: Optional[Dict[str, Any]] = None
        action_id: Optional[str] = None

        if selected is not None:
            # Build the inference label used in the trace
            inference_label = self._inference_label(inferred)

            reason_trace = self._reason_tracer.generate(
                trigger_name=selected.trigger_name,
                signals=selected.signals_snapshot,
                inference=inference_label,
                action_type=selected.action_type,
                explanation_template=selected.explanation_template,
                confidence=inferred.confidence,
            )
            selected.reason_trace = reason_trace

            # Record delivery
            action_id = str(uuid.uuid4())
            delivery = ActionDelivery(
                action_type=selected.action_type,
                trigger_name=selected.trigger_name,
                delivered_at=datetime.utcnow(),
            )
            self._action_history[user_id].append(delivery)
            self._pending_feedback[action_id] = (user_id, delivery)

        # ---- TREND (periodic) ---------------------------------------------
        trend: Optional[TrendReport] = None
        if len(user_states) >= 3:
            trend = self._trend_detector.analyze(
                user_states,
                window_days=self._trend_window_days,
            )

        return CoachResult(
            inferred_state=inferred,
            next_action=selected,
            reason_trace=reason_trace,
            trend_summary=trend,
            action_id=action_id,
        )

    # -----------------------------------------------------------------------
    # LEARN -- feedback ingestion
    # -----------------------------------------------------------------------

    def record_feedback(
        self,
        action_id: str,
        helpful: bool,
        note: Optional[str] = None,
    ) -> bool:
        """Record user feedback for a previously delivered action.

        Parameters
        ----------
        action_id:
            The ``action_id`` from a prior ``CoachResult``.
        helpful:
            Whether the user found the action helpful.
        note:
            Optional free-text note from the user.

        Returns
        -------
        bool
            ``True`` if the feedback was recorded, ``False`` if the
            ``action_id`` was not found.
        """

        if action_id not in self._pending_feedback:
            return False

        user_id, delivery = self._pending_feedback.pop(action_id)

        delivery.marked_helpful = helpful
        delivery.dismissed = not helpful

        return True

    # -----------------------------------------------------------------------
    # State / history accessors (useful for API routes)
    # -----------------------------------------------------------------------

    def get_state_history(self, user_id: str) -> List[InferredStateResult]:
        """Return the full state history for a user."""
        return list(self._state_history.get(user_id, []))

    def get_action_history(self, user_id: str) -> List[ActionDelivery]:
        """Return the full action delivery history for a user."""
        return list(self._action_history.get(user_id, []))

    def get_trend(
        self,
        user_id: str,
        window_days: int = 7,
    ) -> Optional[TrendReport]:
        """Compute a trend report for *user_id* on demand."""
        states = self._state_history.get(user_id, [])
        if not states:
            return None
        return self._trend_detector.analyze(states, window_days=window_days)

    def clear_history(self, user_id: str) -> None:
        """Remove all in-memory state and action history for a user."""
        self._state_history.pop(user_id, None)
        self._action_history.pop(user_id, None)

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _inference_label(state: InferredStateResult) -> str:
        """Map an inferred state to a short inference label for the trace."""
        _LABELS = {
            "stressed": "stress_likely",
            "fatigued": "fatigue_detected",
            "energized": "energy_high",
            "sleep_deprived": "sleep_deficit",
            "calm": "calm_state",
        }
        return _LABELS.get(state.state, state.state)
