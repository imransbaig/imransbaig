"""Action selection with cooldown and fatigue logic.

Receives a list of ``TriggeredAction`` candidates from the trigger registry
and selects the single best action (or nothing) after applying cooldown,
fatigue, mode-adjustment, and personalisation filters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ActionDelivery:
    """Record of an action that was actually delivered to the user."""

    action_type: str
    trigger_name: str
    delivered_at: datetime
    dismissed: bool = False
    marked_helpful: bool = False


@dataclass
class SelectedAction:
    """The final action chosen for delivery."""

    action_type: str
    reason_trace: Dict[str, Any]  # populated by ReasonTracer later
    priority: int
    trigger_name: str = ""
    cooldown_minutes: int = 0
    explanation_template: str = ""
    signals_snapshot: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# ActionSelector
# ---------------------------------------------------------------------------

class ActionSelector:
    """Filters triggered actions through cooldown, fatigue, and personalisation layers.

    Parameters
    ----------
    cooldown_multiplier:
        A global multiplier applied to every trigger's cooldown.  The
        ``select`` method also accepts a *mode* parameter that further
        adjusts cooldowns at call time.
    fatigue_dismiss_threshold:
        Number of consecutive dismissals of the same action type before
        the selector stops proposing it for the current session.
    """

    def __init__(
        self,
        cooldown_multiplier: float = 1.0,
        fatigue_dismiss_threshold: int = 2,
    ) -> None:
        self._cooldown_multiplier = cooldown_multiplier
        self._fatigue_threshold = fatigue_dismiss_threshold

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def select(
        self,
        triggered_actions: list,
        user_history: List[ActionDelivery],
        mode: str = "passive",
    ) -> Optional[SelectedAction]:
        """Pick the best action from *triggered_actions* after filtering.

        Parameters
        ----------
        triggered_actions:
            ``TriggeredAction`` instances returned by
            ``TriggerRegistry.evaluate``, already sorted by priority desc.
        user_history:
            Past ``ActionDelivery`` records for the current user.
        mode:
            ``"passive"`` (default) or ``"live"``.  In live mode cooldowns
            are reduced by 50 %.

        Returns
        -------
        SelectedAction | None
            The single best surviving action, or ``None`` if everything
            was filtered out.
        """

        now = datetime.utcnow()
        mode_multiplier = 0.5 if mode == "live" else 1.0
        effective_multiplier = self._cooldown_multiplier * mode_multiplier

        for candidate in triggered_actions:
            action_type: str = candidate.action_type
            trigger_name: str = candidate.trigger_name

            # --- Cooldown check -------------------------------------------
            effective_cooldown = timedelta(
                minutes=candidate.cooldown_minutes * effective_multiplier,
            )
            if self._is_in_cooldown(action_type, user_history, now, effective_cooldown):
                continue

            # --- Fatigue check --------------------------------------------
            if self._is_fatigued(action_type, user_history):
                continue

            # --- Personalisation boost ------------------------------------
            priority = candidate.priority
            priority = self._apply_personalisation(action_type, user_history, priority)

            return SelectedAction(
                action_type=action_type,
                reason_trace={},  # filled in by ReasonTracer
                priority=priority,
                trigger_name=trigger_name,
                cooldown_minutes=candidate.cooldown_minutes,
                explanation_template=candidate.explanation_template,
                signals_snapshot=getattr(candidate, "signals_snapshot", {}),
            )

        return None  # everything was filtered out

    # -----------------------------------------------------------------------
    # Internal filtering layers
    # -----------------------------------------------------------------------

    @staticmethod
    def _is_in_cooldown(
        action_type: str,
        history: List[ActionDelivery],
        now: datetime,
        cooldown: timedelta,
    ) -> bool:
        """Return ``True`` if *action_type* was delivered within *cooldown*."""
        for entry in reversed(history):
            if entry.action_type == action_type:
                if (now - entry.delivered_at) < cooldown:
                    return True
                # Once we find the most recent delivery of this type and it
                # is outside the cooldown, no need to look further.
                return False
        return False

    def _is_fatigued(
        self,
        action_type: str,
        history: List[ActionDelivery],
    ) -> bool:
        """Return ``True`` if the user dismissed the last N deliveries of this type.

        N is ``fatigue_dismiss_threshold`` (default 2).
        """

        # Gather the most recent deliveries of this action type
        recent_same: List[ActionDelivery] = []
        for entry in reversed(history):
            if entry.action_type == action_type:
                recent_same.append(entry)
                if len(recent_same) >= self._fatigue_threshold:
                    break

        if len(recent_same) < self._fatigue_threshold:
            return False

        return all(d.dismissed for d in recent_same)

    @staticmethod
    def _apply_personalisation(
        action_type: str,
        history: List[ActionDelivery],
        base_priority: int,
    ) -> int:
        """Boost priority if the user previously marked this action type helpful.

        For every helpful mark in the last 20 deliveries the priority is
        increased by 1, capped at 10.
        """

        recent_same = [
            e for e in history[-20:] if e.action_type == action_type
        ]
        helpful_count = sum(1 for e in recent_same if e.marked_helpful)
        boosted = base_priority + helpful_count
        return min(boosted, 10)
