"""Reason-trace generator for the Coach Brain.

Produces a structured JSON-serialisable trace that explains *why* a
particular coaching action was recommended.  The output conforms to the
``ReasonTrace`` schema consumed by the API layer and the front-end
explainability panel.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class ReasonTracer:
    """Generates reason traces for delivered coaching actions.

    A reason trace captures the full causal chain:
    trigger -> signals -> inference -> action, together with a human-readable
    explanation rendered from the trigger's template.

    Example output::

        {
            "trace_id": "d4e5f6...",
            "timestamp": "2025-01-15T14:30:00+00:00",
            "trigger": "elevated_hr_sedentary",
            "signals": {"heart_rate_bpm": 92, "activity_level": "sedentary"},
            "inference": "stress_likely",
            "action": "breathing_exercise_2min",
            "explanation": "Your heart rate was 92 bpm ...",
            "confidence": 0.78
        }
    """

    def generate(
        self,
        trigger_name: str,
        signals: Dict[str, Any],
        inference: str,
        action_type: str,
        explanation_template: str,
        confidence: float = 0.0,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build a complete reason trace dictionary.

        Parameters
        ----------
        trigger_name:
            The identifier of the trigger that fired (e.g.
            ``"elevated_hr_sedentary"``).
        signals:
            Flat dictionary of signal values that contributed to the decision.
        inference:
            A short label describing the inferred state or conclusion
            (e.g. ``"stress_likely"``).
        action_type:
            The coaching action being recommended.
        explanation_template:
            A Python format-string whose placeholders correspond to keys
            in *signals*.  Unknown keys are replaced with ``"?"`` so that
            rendering never raises.
        confidence:
            Numeric confidence of the underlying inference (0.0 .. 1.0).
        extra:
            Optional dictionary merged into the final trace for downstream
            consumers that need additional context.

        Returns
        -------
        dict
            A ``ReasonTrace``-conformant dictionary.
        """

        # --- Render the explanation ----------------------------------------
        explanation = self._render_explanation(explanation_template, signals)

        # --- Build the canonical signal payload ----------------------------
        # Keep only JSON-safe, primitive values.
        clean_signals = self._clean_signals(signals)

        trace: Dict[str, Any] = {
            "trace_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trigger": trigger_name,
            "signals": clean_signals,
            "inference": inference,
            "action": action_type,
            "explanation": explanation,
            "confidence": round(confidence, 4),
        }

        if extra:
            trace.update(extra)

        return trace

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _render_explanation(template: str, signals: Dict[str, Any]) -> str:
        """Safely render *template* using *signals* as format kwargs.

        Missing keys are replaced with ``"?"`` so rendering never fails.
        """

        class _SafeDict(dict):
            """dict subclass that returns '?' for missing keys."""

            def __missing__(self, key: str) -> str:
                return "?"

        try:
            return template.format_map(_SafeDict(signals))
        except (KeyError, ValueError, IndexError):
            # Absolute fallback: return the raw template
            return template

    @staticmethod
    def _clean_signals(signals: Dict[str, Any]) -> Dict[str, Any]:
        """Strip non-JSON-serialisable values from *signals*."""
        clean: Dict[str, Any] = {}
        for key, value in signals.items():
            if isinstance(value, (str, int, float, bool, type(None))):
                clean[key] = value
            elif isinstance(value, (list, tuple)):
                clean[key] = list(value)
            elif isinstance(value, dict):
                clean[key] = value
            else:
                clean[key] = str(value)
        return clean
